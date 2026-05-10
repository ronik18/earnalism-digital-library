from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import re
import hmac
import hashlib
import json as _json
import uuid
import logging
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Cookie, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# ---------- Environment / DB ----------
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production").strip().lower()

mongo_url = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URL")
if not mongo_url:
    raise RuntimeError("MONGODB_URL is required")

def _database_name_from_mongo_url(url: str) -> str:
    parsed = urlparse(url)
    db_name = parsed.path.lstrip("/").split("/", 1)[0]
    return db_name or "earnalism"

client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get("DB_NAME") or _database_name_from_mongo_url(mongo_url)]

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is required")
JWT_ALG = "HS256"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@theearnalism.com").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()
SEED_TEST_READER = os.environ.get("SEED_TEST_READER", "false").strip().lower() == "true"
SEED_TEST_READER_EMAIL = os.environ.get("SEED_TEST_READER_EMAIL", "reader@earnalism.com").strip()
SEED_TEST_READER_PASSWORD = os.environ.get("SEED_TEST_READER_PASSWORD", "").strip()

# Cookie config — httpOnly session cookie. SECURE flag is on by default (HTTPS in prod);
# can be disabled via env for plain-HTTP local dev only.
SESSION_COOKIE = "ear_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax")


# ---------- Razorpay test-mode config ----------
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "").strip()
RAZORPAY_MODE = os.environ.get("RAZORPAY_MODE", "test").strip().lower()

# Server-owned pack catalogue. Frontend cannot influence amount/minutes.
# amount is in PAISE (Razorpay's smallest INR unit); minutes is integer minutes.
PACKS: List[dict] = [
    {"id": "30m",  "label": "Afternoon Pause",     "minutes": 30,  "amount_paise": 4900,  "price_inr": 49,  "note": "A single chapter, with breath to spare."},
    {"id": "1h",   "label": "An Evening In",       "minutes": 60,  "amount_paise": 8900,  "price_inr": 89,  "note": "An unhurried hour with a worthy book."},
    {"id": "3h",   "label": "Long Weekend",        "minutes": 180, "amount_paise": 23900, "price_inr": 239, "note": "Three quiet hours; a finished read."},
    {"id": "10h",  "label": "The Reader's Reserve", "minutes": 600, "amount_paise": 69900, "price_inr": 699, "note": "Ten hours, kept until you call them in."},
]
PACKS_BY_ID = {p["id"]: p for p in PACKS}


def razorpay_keys_configured() -> bool:
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


def get_razorpay_client():
    """Lazy-import the SDK so the app boots even if it's not installed."""
    if not razorpay_keys_configured():
        return None
    try:
        import razorpay  # type: ignore
    except ImportError:
        return None
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def _hmac_sha256_hex(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


# ---------- Auth helpers ----------
def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode(), h.encode())

def create_token(sub: str, email: str) -> str:
    payload = {
        "sub": sub,
        "email": email,
        "role": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def create_user_token(sub: str, email: str) -> str:
    payload = {
        "sub": sub,
        "email": email,
        "role": "user",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

bearer = HTTPBearer(auto_error=False)

async def require_admin(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    ear_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict:
    # Accept either an Authorization Bearer header OR the httpOnly session cookie.
    # Cookies are preferred for browsers; Bearer is kept for server-side tests / curl.
    token: Optional[str] = None
    if creds and creds.scheme.lower() == "bearer":
        token = creds.credentials
    elif ear_session:
        token = ear_session
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload


async def require_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> dict:
    """Authenticate a reader user via Bearer token; reject admin tokens."""
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != "user":
        raise HTTPException(status_code=403, detail="User access required")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.get("status") == "blocked":
        raise HTTPException(status_code=403, detail="Account is blocked")
    return user


async def optional_principal(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> Optional[dict]:
    """Return the caller as a dict tagged with role, or None for guests.

    Never raises. Used by endpoints that return different shapes for
    guests / readers / admins (e.g. content-gated chapter fetch).
    """
    if not creds or creds.scheme.lower() != "bearer":
        return None
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    role = payload.get("role")
    if role == "admin":
        return {"role": "admin", "id": payload.get("sub"), "email": payload.get("email")}
    if role == "user":
        u = await db.users.find_one({"id": payload.get("sub")}, {"_id": 0, "password_hash": 0})
        if not u:
            return None
        u["role"] = "user"
        return u
    return None


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


# ---------- Utils ----------
def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text or "").strip().lower()
    return re.sub(r"[\s_-]+", "-", text) or str(uuid.uuid4())[:8]

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Models ----------
class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

class TokenOut(BaseModel):
    token: str
    email: str
    role: str

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    name: str
    description: str = ""
    image_url: str = ""
    order: int = 0

class CategoryIn(BaseModel):
    name: str
    description: str = ""
    image_url: str = ""
    order: int = 0
    slug: Optional[str] = None

class Chapter(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str = ""
    order: int = 0

class ChapterIn(BaseModel):
    title: str
    content: str = ""

class ChapterReorderIn(BaseModel):
    ids: List[str]

class Book(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    title: str
    subtitle: str = ""
    author: str = "The Earnalism"
    category_slug: str
    short_description: str = ""
    description: str = ""
    cover_image_url: str = ""
    estimated_reading_time: str = ""
    price_paperback: str = ""
    price_ebook: str = ""
    buy_url: str = ""
    formats: List[str] = Field(default_factory=lambda: ["Paperback", "Ebook"])
    benefits: List[str] = Field(default_factory=list)
    who_for: List[str] = Field(default_factory=list)
    learnings: List[str] = Field(default_factory=list)
    about_author: str = ""
    chapters: List[Chapter] = Field(default_factory=list)
    is_published: bool = True
    created_at: str = Field(default_factory=now_iso)

class BookIn(BaseModel):
    title: str
    subtitle: str = ""
    author: str = "The Earnalism"
    category_slug: str
    short_description: str = ""
    description: str = ""
    cover_image_url: str = ""
    estimated_reading_time: str = ""
    price_paperback: str = ""
    price_ebook: str = ""
    buy_url: str = ""
    formats: List[str] = Field(default_factory=lambda: ["Paperback", "Ebook"])
    benefits: List[str] = Field(default_factory=list)
    who_for: List[str] = Field(default_factory=list)
    learnings: List[str] = Field(default_factory=list)
    about_author: str = ""
    is_published: bool = True
    slug: Optional[str] = None

class BlogPost(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    title: str
    excerpt: str = ""
    content: str = ""
    category: str = "Reflections"
    cover_image_url: str = ""
    author: str = "The Earnalism"
    pull_quote: str = ""
    is_published: bool = True
    created_at: str = Field(default_factory=now_iso)

class BlogPostIn(BaseModel):
    title: str
    excerpt: str = ""
    content: str = ""
    category: str = "Reflections"
    cover_image_url: str = ""
    author: str = "The Earnalism"
    pull_quote: str = ""
    is_published: bool = True
    slug: Optional[str] = None

class NewsletterIn(BaseModel):
    name: str
    email: EmailStr

class ContactIn(BaseModel):
    name: str
    email: EmailStr
    subject: str = ""
    message: str

class SocialIn(BaseModel):
    instagram: str = ""
    facebook: str = ""
    youtube: str = ""
    linkedin: str = ""
    twitter: str = ""

class BrandIn(BaseModel):
    logo_url: str = ""
    og_image_url: str = ""

class FeaturedIn(BaseModel):
    book_slug: str

class ContactStatusIn(BaseModel):
    status: str  # one of: new, read, responded

VALID_CONTACT_STATUSES = {"new", "read", "responded"}


# ---------- Reader User / Wallet / Session models ----------
class UserSignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str = "user"
    reading_seconds_balance: int = 0
    status: str = "active"
    auth_provider: str = "email"
    created_at: str

class UserAuthOut(BaseModel):
    token: str
    user: UserOut

class GoogleAuthIn(BaseModel):
    credential: str

class OTPRequestIn(BaseModel):
    mobile: str

class OTPVerifyIn(BaseModel):
    mobile: str
    otp: str

class WalletAdjustIn(BaseModel):
    minutes: int  # may be negative; converted to seconds server-side
    reason: str = ""

class WalletTransactionOut(BaseModel):
    id: str
    user_id: str
    type: str  # "credit" | "debit" | "consume"
    seconds: int
    reason: str
    created_at: str
    actor: str = "system"  # "admin" | "system" | "user"

class ReaderSessionStartIn(BaseModel):
    session_id: Optional[str] = None
    book_id: Optional[str] = None
    book_slug: Optional[str] = None
    chapter_id: Optional[str] = None

class ReaderHeartbeatIn(BaseModel):
    session_id: str
    visible: bool = True
    idle: bool = False
    chapter_id: Optional[str] = None

class ReaderSessionEndIn(BaseModel):
    session_id: str

class UserStatusIn(BaseModel):
    status: str  # "active" | "blocked"


# ---------- Payments / Razorpay top-up models ----------
class PackOut(BaseModel):
    id: str
    label: str
    minutes: int
    price_inr: int
    amount_paise: int
    note: str


class TopUpCreateIn(BaseModel):
    pack_id: str


class TopUpCreateOut(BaseModel):
    intent_id: str
    razorpay_order_id: str
    key_id: str
    amount: int  # in paise
    currency: str = "INR"
    name: str
    description: str
    pack: PackOut
    prefill: dict


class PaymentVerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentReconcileIn(BaseModel):
    note: str = ""


def _user_public(doc: dict) -> dict:
    return {
        "id": doc["id"],
        "name": doc.get("name", ""),
        "email": doc["email"],
        "role": "user",
        "reading_seconds_balance": int(doc.get("reading_seconds_balance", 0)),
        "status": doc.get("status", "active"),
        "auth_provider": doc.get("auth_provider", "email"),
        "created_at": doc.get("created_at", now_iso()),
    }


def _is_free_preview_chapter(book: dict, chapter_id: Optional[str]) -> bool:
    """Chapter with order==0 (the first chapter) is always free preview."""
    if not chapter_id:
        return False
    chapters = book.get("chapters") or []
    if not chapters:
        return False
    sorted_ch = sorted(chapters, key=lambda c: c.get("order", 0))
    return sorted_ch[0].get("id") == chapter_id


def _strip_paid_chapter_content(book: dict) -> dict:
    """Return a shallow copy of `book` with non-preview chapter `content`
    blanked. Preview chapter (order==0) keeps its content; everything later
    is metadata-only. Used for PUBLIC `/api/books/*` endpoints so chapter
    bodies are never leaked to guests via the catalog API.
    """
    if not book:
        return book
    chapters = book.get("chapters") or []
    if not chapters:
        return book
    sorted_ch = sorted(chapters, key=lambda c: c.get("order", 0))
    preview_id = sorted_ch[0].get("id") if sorted_ch else None
    masked = []
    for c in chapters:
        c2 = dict(c)
        if c.get("id") != preview_id:
            c2["content"] = ""
        masked.append(c2)
    out = dict(book)
    out["chapters"] = masked
    return out


# ---------- App ----------
async def initialize_database_indexes() -> None:
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", sparse=True)
    await db.users.create_index("mobile", sparse=True)
    await db.users.create_index([("role", 1), ("status", 1), ("created_at", -1)])

    await db.books.create_index("slug", unique=True)
    await db.books.create_index([("is_published", 1), ("created_at", -1)])
    await db.books.create_index([("category_slug", 1), ("is_published", 1), ("created_at", -1)])

    await db.categories.create_index("slug", unique=True)
    await db.categories.create_index([("order", 1), ("slug", 1)])

    await db.blog_posts.create_index("slug", unique=True)
    await db.blog_posts.create_index([("is_published", 1), ("created_at", -1)])

    await db.newsletter.create_index("email", unique=True)
    await db.newsletter.create_index([("created_at", -1)])

    await db.contacts.create_index([("status", 1), ("created_at", -1)])
    await db.contacts.create_index([("created_at", -1)])

    await db.settings.create_index("key", unique=True)

    await db.wallet_transactions.create_index([("user_id", 1), ("created_at", -1)])

    await db.reading_sessions.create_index("id", sparse=True)
    await db.reading_sessions.create_index([("user_id", 1), ("started_at", -1)])
    await db.reading_sessions.create_index([("user_id", 1), ("status", 1), ("started_at", -1)])
    await db.reading_sessions.create_index("status")

    await db.topup_intents.create_index("id", sparse=True)
    await db.topup_intents.create_index(
        "razorpay_order_id",
        unique=True,
        partialFilterExpression={"razorpay_order_id": {"$type": "string"}},
    )
    await db.topup_intents.create_index(
        "razorpay_payment_id",
        unique=True,
        partialFilterExpression={"razorpay_payment_id": {"$type": "string"}},
    )
    await db.topup_intents.create_index([("user_id", 1), ("created_at", -1)])
    await db.topup_intents.create_index([("status", 1), ("created_at", -1)])
    await db.topup_intents.create_index("status")

    await db.payment_webhook_events.create_index("event_id", unique=True, sparse=True)
    await db.payment_webhook_events.create_index([("created_at", -1)])


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # ----- startup -----
    await initialize_database_indexes()

    # admin (seed only if absent; do NOT overwrite password so admin can change it via UI)
    existing = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    if not existing:
        if not ADMIN_PASSWORD:
            raise RuntimeError("ADMIN_PASSWORD is required to seed the initial admin user")
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": ADMIN_EMAIL.lower(),
            "password_hash": hash_password(ADMIN_PASSWORD),
            "name": "Admin",
            "role": "admin",
            "created_at": now_iso(),
        })
        logger.info("Seeded admin user")

    # Optional non-production seed reader (idempotent; disabled unless explicitly enabled).
    test_user_email = SEED_TEST_READER_EMAIL.lower()
    if SEED_TEST_READER and not await db.users.find_one({"email": test_user_email}):
        if not SEED_TEST_READER_PASSWORD:
            raise RuntimeError("SEED_TEST_READER_PASSWORD is required when SEED_TEST_READER=true")
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": test_user_email,
            "password_hash": hash_password(SEED_TEST_READER_PASSWORD),
            "name": "Sample Reader",
            "role": "user",
            "auth_provider": "email",
            "reading_seconds_balance": 0,
            "status": "active",
            "created_at": now_iso(),
        })
        logger.info("Seeded sample reader user")

    # Backfill new fields on legacy user documents (role=user)
    await db.users.update_many(
        {"role": "user", "reading_seconds_balance": {"$exists": False}},
        {"$set": {"reading_seconds_balance": 0}},
    )
    await db.users.update_many(
        {"role": "user", "status": {"$exists": False}},
        {"$set": {"status": "active"}},
    )
    await db.users.update_many(
        {"role": "user", "auth_provider": {"$exists": False}},
        {"$set": {"auth_provider": "email"}},
    )

    # categories
    for c in SEED_CATEGORIES:
        await db.categories.update_one(
            {"slug": c["slug"]},
            {"$setOnInsert": {**c, "id": str(uuid.uuid4())}},
            upsert=True,
        )

    # featured book
    if not await db.books.find_one({"slug": SEED_BOOK["slug"]}):
        b = Book(**SEED_BOOK)
        await db.books.insert_one(b.model_dump())
        logger.info("Seeded featured book")

    # technology sample book (idempotent — only inserted if missing)
    if not await db.books.find_one({"slug": SEED_TECH_BOOK["slug"]}):
        tb = Book(**SEED_TECH_BOOK)
        await db.books.insert_one(tb.model_dump())
        logger.info("Seeded technology sample book")

    # featured setting
    await db.settings.update_one(
        {"key": "featured_book"},
        {"$setOnInsert": {"key": "featured_book", "book_slug": SEED_BOOK["slug"]}},
        upsert=True,
    )

    # blog posts
    for p in SEED_POSTS:
        if not await db.blog_posts.find_one({"slug": p["slug"]}):
            post = BlogPost(**p)
            await db.blog_posts.insert_one(post.model_dump())

    # social settings (seed empty config so GET /api/settings/social always works)
    await db.settings.update_one(
        {"key": "social"},
        {"$setOnInsert": {"key": "social", "instagram": "", "facebook": "", "youtube": "", "linkedin": "", "twitter": ""}},
        upsert=True,
    )

    # brand settings (logo + OG image; seeded empty so the public endpoint always works)
    await db.settings.update_one(
        {"key": "brand"},
        {"$setOnInsert": {"key": "brand", "logo_url": "", "og_image_url": ""}},
        upsert=True,
    )

    # backfill contact.status for older entries that didn't have the field
    await db.contacts.update_many({"status": {"$exists": False}}, {"$set": {"status": "new"}})

    # backfill digital-library fields on any pre-existing books
    await db.books.update_many(
        {"author": {"$exists": False}},
        {"$set": {"author": "The Earnalism"}},
    )
    await db.books.update_many(
        {"estimated_reading_time": {"$exists": False}},
        {"$set": {"estimated_reading_time": ""}},
    )
    await db.books.update_many(
        {"chapters": {"$exists": False}},
        {"$set": {"chapters": []}},
    )
    await db.books.update_many(
        {"is_published": {"$exists": False}},
        {"$set": {"is_published": True}},
    )

    # one-time migration: replace old "publishing brand" wording in the seeded book's about_author
    await db.books.update_one(
        {"slug": SEED_BOOK["slug"], "about_author": re.compile("publishing brand", re.IGNORECASE)},
        {"$set": {"about_author": SEED_BOOK["about_author"]}},
    )
    logger.info("Startup seeding complete")

    yield

    # ----- shutdown -----
    client.close()


app = FastAPI(title="The Earnalism API", lifespan=lifespan)
api = APIRouter(prefix="/api")


# ---------- Auth ----------
@api.post("/auth/login", response_model=TokenOut)
async def login(payload: LoginIn):
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"], user["email"])
    return TokenOut(token=token, email=user["email"], role=user.get("role", "admin"))

@api.get("/auth/me")
async def me(user=Depends(require_admin)):
    return {"email": user["email"], "role": user["role"]}


@api.post("/auth/change-password")
async def change_password(payload: ChangePasswordIn, user=Depends(require_admin)):
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    existing = await db.users.find_one({"email": user["email"]}, {"_id": 0})
    if not existing or not verify_password(payload.current_password, existing["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await db.users.update_one(
        {"email": user["email"]},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
    return {"ok": True, "message": "Password updated. Please sign in again."}


# ---------- Public: Categories ----------
@api.get("/health")
async def health_check():
    """Liveness + DB ping for load balancers and Docker healthchecks."""
    db_ok = True
    try:
        await db.command("ping")
    except Exception:
        db_ok = False
    return {
        "ok": db_ok,
        "service": "the-earnalism-api",
        "mode": RAZORPAY_MODE,
        "razorpay_configured": razorpay_keys_configured(),
        "time": now_iso(),
    }


@app.get("/health")
async def root_health_check():
    return await health_check()


@api.get("/categories", response_model=List[Category])
async def list_categories():
    docs = await db.categories.find({}, {"_id": 0}).sort("order", 1).to_list(200)
    return docs


# ---------- Public: Books ----------
@api.get("/books", response_model=List[Book])
async def list_books(category: Optional[str] = None, q: Optional[str] = None):
    query: dict = {"is_published": True}
    if category and category != "all":
        query["category_slug"] = category
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"subtitle": {"$regex": q, "$options": "i"}},
            {"short_description": {"$regex": q, "$options": "i"}},
            {"category_slug": {"$regex": q, "$options": "i"}},
        ]
    docs = await db.books.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Public list never leaks paid chapter bodies.
    return [_strip_paid_chapter_content(d) for d in docs]

@api.get("/books/{slug}", response_model=Book)
async def get_book(slug: str):
    doc = await db.books.find_one({"slug": slug, "is_published": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")
    # Public detail returns ToC + only the free-preview chapter's body.
    return _strip_paid_chapter_content(doc)


@api.get("/books/{slug}/chapters")
async def get_book_chapters(slug: str):
    doc = await db.books.find_one({"slug": slug, "is_published": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")
    chapters = _strip_paid_chapter_content(doc).get("chapters") or []
    if not chapters:
        return []
    return sorted(chapters, key=lambda c: c.get("order", 0))


@api.get("/books/{slug}/chapters/{chapter_id}")
async def get_book_chapter(slug: str, chapter_id: str):
    doc = await db.books.find_one({"slug": slug, "is_published": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")
    chapters = _strip_paid_chapter_content(doc).get("chapters") or []
    chapter = next((c for c in chapters if c.get("id") == chapter_id), None)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter


# ---------- Public: Blog ----------
@api.get("/blog", response_model=List[BlogPost])
async def list_blog(category: Optional[str] = None):
    query: dict = {"is_published": True}
    if category and category != "all":
        query["category"] = category
    docs = await db.blog_posts.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return docs

@api.get("/blog/{slug}", response_model=BlogPost)
async def get_blog(slug: str):
    doc = await db.blog_posts.find_one({"slug": slug, "is_published": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Article not found")
    return doc


# ---------- Public: Featured ----------
@api.get("/featured")
async def get_featured():
    s = await db.settings.find_one({"key": "featured_book"}, {"_id": 0})
    if not s:
        return {"book": None}
    book = await db.books.find_one({"slug": s.get("book_slug")}, {"_id": 0})
    return {"book": book}


# ---------- Public: Submissions ----------
@api.post("/newsletter")
async def subscribe(payload: NewsletterIn):
    existing = await db.newsletter.find_one({"email": payload.email.lower()}, {"_id": 0})
    if existing:
        return {"ok": True, "message": "You're already part of the Reading Circle."}
    await db.newsletter.insert_one({
        "id": str(uuid.uuid4()),
        "name": payload.name.strip(),
        "email": payload.email.lower().strip(),
        "created_at": now_iso(),
    })
    return {"ok": True, "message": "Welcome to the Earnalism Reading Circle."}

@api.post("/contact")
async def contact(payload: ContactIn):
    await db.contacts.insert_one({
        "id": str(uuid.uuid4()),
        "name": payload.name.strip(),
        "email": payload.email.lower().strip(),
        "subject": payload.subject.strip(),
        "message": payload.message.strip(),
        "status": "new",
        "created_at": now_iso(),
    })
    return {"ok": True, "message": "Thank you. We'll respond with care."}


# ---------- Public: Social settings ----------
@api.get("/settings/social")
async def get_social():
    doc = await db.settings.find_one({"key": "social"}, {"_id": 0}) or {}
    return {
        "instagram": doc.get("instagram", ""),
        "facebook": doc.get("facebook", ""),
        "youtube": doc.get("youtube", ""),
        "linkedin": doc.get("linkedin", ""),
        "twitter": doc.get("twitter", ""),
    }


@api.get("/settings/brand")
async def get_brand():
    """Brand identity: logo URL + social-share OG image. Both optional.
    Empty strings are returned if not configured so the frontend can fall back
    to the existing premium text logo and hero image."""
    doc = await db.settings.find_one({"key": "brand"}, {"_id": 0}) or {}
    return {
        "logo_url": doc.get("logo_url", ""),
        "og_image_url": doc.get("og_image_url", ""),
    }


# ---------- Admin: Books ----------
@api.post("/admin/books", response_model=Book)
async def admin_create_book(payload: BookIn, _=Depends(require_admin)):
    slug = slugify(payload.slug or payload.title)
    if await db.books.find_one({"slug": slug}):
        raise HTTPException(status_code=400, detail="Slug already exists")
    book = Book(slug=slug, **{k: v for k, v in payload.model_dump().items() if k != "slug"})
    await db.books.insert_one(book.model_dump())
    return book

@api.put("/admin/books/{slug}", response_model=Book)
async def admin_update_book(slug: str, payload: BookIn, _=Depends(require_admin)):
    existing = await db.books.find_one({"slug": slug}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Book not found")
    new_slug = slugify(payload.slug or payload.title) if (payload.slug or payload.title != existing["title"]) else slug
    update = payload.model_dump()
    update["slug"] = new_slug
    await db.books.update_one({"slug": slug}, {"$set": update})
    refreshed = await db.books.find_one({"slug": new_slug}, {"_id": 0})
    return refreshed

@api.delete("/admin/books/{slug}")
async def admin_delete_book(slug: str, _=Depends(require_admin)):
    res = await db.books.delete_one({"slug": slug})
    return {"deleted": res.deleted_count}

@api.get("/admin/books", response_model=List[Book])
async def admin_list_books(_=Depends(require_admin)):
    return await db.books.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)


# ---------- Admin: Chapters (manual paste only for Phase 1) ----------
async def _load_book_or_404(slug: str) -> dict:
    doc = await db.books.find_one({"slug": slug}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")
    return doc

@api.post("/admin/books/{slug}/chapters", response_model=Book)
async def admin_add_chapter(slug: str, payload: ChapterIn, _=Depends(require_admin)):
    book = await _load_book_or_404(slug)
    existing = book.get("chapters", []) or []
    next_order = max([c.get("order", 0) for c in existing], default=-1) + 1
    chapter = Chapter(title=payload.title.strip(), content=payload.content, order=next_order).model_dump()
    await db.books.update_one({"slug": slug}, {"$push": {"chapters": chapter}})
    return await _load_book_or_404(slug)

@api.put("/admin/books/{slug}/chapters/{cid}", response_model=Book)
async def admin_update_chapter(slug: str, cid: str, payload: ChapterIn, _=Depends(require_admin)):
    res = await db.books.update_one(
        {"slug": slug, "chapters.id": cid},
        {"$set": {"chapters.$.title": payload.title.strip(), "chapters.$.content": payload.content}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return await _load_book_or_404(slug)

@api.delete("/admin/books/{slug}/chapters/{cid}", response_model=Book)
async def admin_delete_chapter(slug: str, cid: str, _=Depends(require_admin)):
    await _load_book_or_404(slug)
    res = await db.books.update_one({"slug": slug}, {"$pull": {"chapters": {"id": cid}}})
    if res.modified_count == 0:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return await _load_book_or_404(slug)

@api.put("/admin/books/{slug}/chapters/reorder", response_model=Book)
async def admin_reorder_chapters(slug: str, payload: ChapterReorderIn, _=Depends(require_admin)):
    book = await _load_book_or_404(slug)
    existing = {c["id"]: c for c in (book.get("chapters") or [])}
    if set(payload.ids) != set(existing.keys()):
        raise HTTPException(status_code=400, detail="Reorder ids must match existing chapter ids exactly")
    reordered = []
    for i, cid in enumerate(payload.ids):
        c = dict(existing[cid])
        c["order"] = i
        reordered.append(c)
    await db.books.update_one({"slug": slug}, {"$set": {"chapters": reordered}})
    return await _load_book_or_404(slug)


# ---------- Admin: Cloudinary uploads ----------
# Cloudinary setup is lazy — failed imports are surfaced at request time
# rather than blocking app boot when the optional deps aren't installed yet.
_CLOUDINARY_INITIALIZED = False

def _ensure_cloudinary():
    global _CLOUDINARY_INITIALIZED
    if _CLOUDINARY_INITIALIZED:
        return
    try:
        from config.cloudinary import init_cloudinary  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Image pipeline unavailable: {e}")
    init_cloudinary()
    _CLOUDINARY_INITIALIZED = True


_ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_ALLOWED_CHAPTER_EXTS = {"docx", "md", "markdown", "html", "txt"}


@api.post("/admin/books/{slug}/cover")
async def admin_upload_cover(slug: str, file: UploadFile = File(...), _=Depends(require_admin)):
    if file.content_type not in _ALLOWED_COVER_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    body = await file.read()
    if len(body) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Cover must be under 10MB")
    book = await _load_book_or_404(slug)
    _ensure_cloudinary()
    try:
        from utils.content_processor import process_book_cover  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Image pipeline unavailable: {e}")
    result = process_book_cover(body, book.get("id") or slug)
    await db.books.update_one(
        {"slug": slug},
        {"$set": {
            "cover_url": result["cover_url"],
            "cover_image_url": result["cover_url"],
            "thumbnail_url": result["thumbnail_url"],
            "blur_placeholder": result["blur_placeholder"],
            "dominant_color": result["dominant_color"],
        }},
    )
    return {"success": True, **result}


@api.post("/admin/books/{slug}/chapters/{chapter_id}/upload")
async def admin_upload_chapter_file(
    slug: str,
    chapter_id: str,
    file: UploadFile = File(...),
    _=Depends(require_admin),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in _ALLOWED_CHAPTER_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported chapter format")
    body = await file.read()
    if len(body) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Chapter file must be under 50MB")
    book = await _load_book_or_404(slug)
    chapters = book.get("chapters") or []
    target = next((c for c in chapters if c.get("id") == chapter_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Chapter not found")
    _ensure_cloudinary()
    try:
        from utils.content_processor import process_chapter_content  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Content pipeline unavailable: {e}")
    result = process_chapter_content(body, file.filename or "chapter", book.get("id") or slug)
    new_chapters = []
    for c in chapters:
        if c.get("id") == chapter_id:
            c = dict(c)
            c["content"] = result["content_html"]
            c["has_images"] = result["has_images"]
            c["image_count"] = result["image_count"]
            c["word_count"] = result["word_count"]
            c["reading_minutes"] = result["reading_minutes"]
            c["updated_at"] = now_iso()
        new_chapters.append(c)
    await db.books.update_one({"slug": slug}, {"$set": {"chapters": new_chapters}})
    return {
        "success": True,
        "word_count": result["word_count"],
        "reading_minutes": result["reading_minutes"],
        "has_images": result["has_images"],
        "image_count": result["image_count"],
    }


# ---------- Admin: Image upload (generic — for blog editor) ----------
@api.post("/admin/upload/image")
async def admin_upload_image(file: UploadFile = File(...), _=Depends(require_admin)):
    if file.content_type not in _ALLOWED_COVER_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    body = await file.read()
    if len(body) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 10MB")
    _ensure_cloudinary()
    try:
        from config.cloudinary import upload_image  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Image pipeline unavailable: {e}")
    result = upload_image(body, folder="earnalism/journal")
    return {"url": result["url"], "width": result.get("width"), "height": result.get("height")}


# ---------- Admin: Categories ----------
@api.post("/admin/categories", response_model=Category)
async def admin_create_cat(payload: CategoryIn, _=Depends(require_admin)):
    slug = slugify(payload.slug or payload.name)
    if await db.categories.find_one({"slug": slug}):
        raise HTTPException(status_code=400, detail="Slug already exists")
    cat = Category(slug=slug, **{k: v for k, v in payload.model_dump().items() if k != "slug"})
    await db.categories.insert_one(cat.model_dump())
    return cat

@api.put("/admin/categories/{slug}", response_model=Category)
async def admin_update_cat(slug: str, payload: CategoryIn, _=Depends(require_admin)):
    existing = await db.categories.find_one({"slug": slug}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    update = payload.model_dump()
    update["slug"] = slug  # keep slug stable
    await db.categories.update_one({"slug": slug}, {"$set": update})
    return await db.categories.find_one({"slug": slug}, {"_id": 0})

@api.delete("/admin/categories/{slug}")
async def admin_delete_cat(slug: str, _=Depends(require_admin)):
    res = await db.categories.delete_one({"slug": slug})
    return {"deleted": res.deleted_count}


# ---------- Admin: Blog ----------
@api.post("/admin/blog", response_model=BlogPost)
async def admin_create_post(payload: BlogPostIn, _=Depends(require_admin)):
    slug = slugify(payload.slug or payload.title)
    if await db.blog_posts.find_one({"slug": slug}):
        raise HTTPException(status_code=400, detail="Slug already exists")
    post = BlogPost(slug=slug, **{k: v for k, v in payload.model_dump().items() if k != "slug"})
    await db.blog_posts.insert_one(post.model_dump())
    return post

@api.put("/admin/blog/{slug}", response_model=BlogPost)
async def admin_update_post(slug: str, payload: BlogPostIn, _=Depends(require_admin)):
    existing = await db.blog_posts.find_one({"slug": slug}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Post not found")
    update = payload.model_dump()
    update["slug"] = slug
    await db.blog_posts.update_one({"slug": slug}, {"$set": update})
    return await db.blog_posts.find_one({"slug": slug}, {"_id": 0})

@api.delete("/admin/blog/{slug}")
async def admin_delete_post(slug: str, _=Depends(require_admin)):
    res = await db.blog_posts.delete_one({"slug": slug})
    return {"deleted": res.deleted_count}

@api.get("/admin/blog", response_model=List[BlogPost])
async def admin_list_posts(_=Depends(require_admin)):
    return await db.blog_posts.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)


# ---------- Admin: Submissions ----------
@api.get("/admin/newsletter")
async def admin_newsletter(_=Depends(require_admin)):
    return await db.newsletter.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)

@api.get("/admin/contacts")
async def admin_contacts(_=Depends(require_admin)):
    return await db.contacts.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)


@api.patch("/admin/contacts/{cid}/status")
async def admin_set_contact_status(cid: str, payload: ContactStatusIn, _=Depends(require_admin)):
    if payload.status not in VALID_CONTACT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    res = await db.contacts.update_one(
        {"id": cid},
        {"$set": {"status": payload.status, "updated_at": now_iso()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"ok": True, "id": cid, "status": payload.status}


# ---------- Admin: Settings (social) ----------
@api.put("/admin/settings/social")
async def admin_set_social(payload: SocialIn, _=Depends(require_admin)):
    data = payload.model_dump()
    await db.settings.update_one(
        {"key": "social"},
        {"$set": {"key": "social", **data}},
        upsert=True,
    )
    return {"ok": True, **data}


# ---------- Admin: Settings (brand identity) ----------
@api.put("/admin/settings/brand")
async def admin_set_brand(payload: BrandIn, _=Depends(require_admin)):
    data = payload.model_dump()
    await db.settings.update_one(
        {"key": "brand"},
        {"$set": {"key": "brand", **data}},
        upsert=True,
    )
    return {"ok": True, **data}


# ---------- Admin: Featured ----------
@api.put("/admin/featured")
async def admin_set_featured(payload: FeaturedIn, _=Depends(require_admin)):
    book = await db.books.find_one({"slug": payload.book_slug}, {"_id": 0})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    await db.settings.update_one(
        {"key": "featured_book"},
        {"$set": {"key": "featured_book", "book_slug": payload.book_slug}},
        upsert=True,
    )
    return {"ok": True, "book_slug": payload.book_slug}


# ---------- Reader User: Auth ----------
@api.post("/users/signup", response_model=UserAuthOut)
async def user_signup(payload: UserSignupIn):
    name = payload.name.strip()
    email = payload.email.lower().strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "password_hash": hash_password(payload.password),
        "role": "user",
        "auth_provider": "email",
        "reading_seconds_balance": 0,
        "status": "active",
        "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    token = create_user_token(doc["id"], doc["email"])
    return UserAuthOut(token=token, user=UserOut(**_user_public(doc)))


@api.post("/users/login", response_model=UserAuthOut)
async def user_login(payload: UserLoginIn):
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or user.get("role") != "user" or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("status") == "blocked":
        raise HTTPException(status_code=403, detail="Account is blocked. Please contact support.")
    token = create_user_token(user["id"], user["email"])
    return UserAuthOut(token=token, user=UserOut(**_user_public(user)))


@api.post("/users/logout")
async def user_logout(_user=Depends(require_user)):
    return {"ok": True}


# ---------- Social auth: Google + Mobile OTP ----------
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
MSG91_AUTH_KEY = os.environ.get("MSG91_AUTH_KEY", "").strip()
MSG91_TEMPLATE_ID = os.environ.get("MSG91_TEMPLATE_ID", "").strip()


def _phone_email(mobile: str) -> str:
    digits = re.sub(r"\D", "", mobile)
    return f"mobile+{digits}@earnalism.local"


@api.post("/auth/google", response_model=UserAuthOut)
async def auth_google(payload: GoogleAuthIn):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    try:
        from google.oauth2 import id_token  # type: ignore
        from google.auth.transport import requests as google_requests  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Google auth unavailable: {e}")
    try:
        idinfo = id_token.verify_oauth2_token(payload.credential, google_requests.Request(), GOOGLE_CLIENT_ID)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    email = (idinfo.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=401, detail="Google account has no email")
    name = idinfo.get("name") or email.split("@", 1)[0]
    picture = idinfo.get("picture") or ""

    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        doc = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "password_hash": "",
            "role": "user",
            "status": "active",
            "auth_provider": "google",
            "picture": picture,
            "reading_seconds_balance": 0,
            "created_at": now_iso(),
        }
        await db.users.insert_one(doc)
        user = doc
    elif user.get("status") == "blocked":
        raise HTTPException(status_code=403, detail="Account is blocked. Please contact support.")

    token = create_user_token(user["id"], user["email"])
    return UserAuthOut(token=token, user=UserOut(**_user_public(user)))


@api.post("/auth/otp/request")
async def auth_otp_request(payload: OTPRequestIn):
    mobile = payload.mobile.strip()
    if not re.match(r"^\+91[6-9]\d{9}$", mobile):
        raise HTTPException(status_code=400, detail="Invalid mobile number")
    import random
    otp = str(random.randint(100000, 999999))
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.otp_store.update_one(
        {"mobile": mobile},
        {"$set": {"otp": otp, "expires": expires, "attempts": 0}},
        upsert=True,
    )
    if MSG91_AUTH_KEY and MSG91_TEMPLATE_ID:
        try:
            import httpx  # type: ignore
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    "https://api.msg91.com/api/v5/otp",
                    params={
                        "authkey": MSG91_AUTH_KEY,
                        "mobile": mobile.lstrip("+"),
                        "template_id": MSG91_TEMPLATE_ID,
                        "otp": otp,
                    },
                )
        except Exception as e:
            logger.warning(f"MSG91 send failed: {e}")
    return {"success": True, "message": "OTP sent"}


@api.post("/auth/otp/verify", response_model=UserAuthOut)
async def auth_otp_verify(payload: OTPVerifyIn):
    mobile = payload.mobile.strip()
    record = await db.otp_store.find_one({"mobile": mobile})
    if not record:
        raise HTTPException(status_code=400, detail="OTP not requested")
    expires = record.get("expires")
    if isinstance(expires, datetime) and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not expires or expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP expired")
    if int(record.get("attempts", 0)) >= 3:
        raise HTTPException(status_code=429, detail="Too many attempts")
    if record.get("otp") != payload.otp.strip():
        await db.otp_store.update_one({"mobile": mobile}, {"$inc": {"attempts": 1}})
        raise HTTPException(status_code=400, detail="Incorrect OTP")
    await db.otp_store.delete_one({"mobile": mobile})

    synthetic_email = _phone_email(mobile)
    user = await db.users.find_one({"$or": [{"mobile": mobile}, {"email": synthetic_email}]}, {"_id": 0})
    if not user:
        doc = {
            "id": str(uuid.uuid4()),
            "name": mobile,
            "email": synthetic_email,
            "mobile": mobile,
            "password_hash": "",
            "role": "user",
            "status": "active",
            "auth_provider": "mobile_otp",
            "reading_seconds_balance": 0,
            "created_at": now_iso(),
        }
        await db.users.insert_one(doc)
        user = doc
    elif user.get("status") == "blocked":
        raise HTTPException(status_code=403, detail="Account is blocked. Please contact support.")

    token = create_user_token(user["id"], user["email"])
    return UserAuthOut(token=token, user=UserOut(**_user_public(user)))


@api.get("/users/me", response_model=UserOut)
async def user_me(user=Depends(require_user)):
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return UserOut(**_user_public(fresh or user))


@api.get("/users/me/wallet")
async def user_wallet(user=Depends(require_user)):
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0}) or user
    wallet_seconds = int(fresh.get("reading_seconds_balance", fresh.get("wallet_seconds", 0)) or 0)
    return {"wallet_seconds": wallet_seconds}


@api.get("/users/me/transactions", response_model=List[WalletTransactionOut])
async def user_my_transactions(user=Depends(require_user)):
    rows = await db.wallet_transactions.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows


# ---------- Reader: Sessions + Heartbeat ----------
HEARTBEAT_TICK_SECONDS = 30
LOW_BALANCE_THRESHOLD = 300


@api.post("/reader/session/start")
async def reader_session_start(payload: ReaderSessionStartIn, user=Depends(require_user)):
    book_slug = payload.book_slug or payload.book_id
    if not book_slug:
        raise HTTPException(status_code=400, detail="Book id is required")
    book = await db.books.find_one({"slug": book_slug, "is_published": True}, {"_id": 0})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    balance = int((fresh or {}).get("reading_seconds_balance", 0))
    is_preview = _is_free_preview_chapter(book, payload.chapter_id)
    if balance <= 0 and not is_preview:
        raise HTTPException(status_code=402, detail="Insufficient reading time. Top up to continue.")
    sid = str(uuid.uuid4())
    await db.reading_sessions.insert_one({
        "id": sid,
        "user_id": user["id"],
        "book_slug": book_slug,
        "chapter_id": payload.chapter_id,
        "started_at": now_iso(),
        "last_heartbeat_at": now_iso(),
        "seconds_consumed": 0,
        "status": "active",
    })
    return {
        "session_id": sid,
        "remaining_seconds": balance,
        "is_preview": is_preview,
        "tick_seconds": HEARTBEAT_TICK_SECONDS,
    }


@api.post("/reader/heartbeat")
async def reader_heartbeat(payload: ReaderHeartbeatIn, user=Depends(require_user)):
    session = await db.reading_sessions.find_one({"id": payload.session_id, "user_id": user["id"]}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("status") != "active":
        return {"deducted_seconds": 0, "remaining_seconds": 0, "status": session.get("status", "ended"), "is_preview": False}

    book = await db.books.find_one({"slug": session["book_slug"]}, {"_id": 0})
    if not book:
        await db.reading_sessions.update_one({"id": payload.session_id}, {"$set": {"status": "ended"}})
        raise HTTPException(status_code=404, detail="Book not found")

    chapter_id = payload.chapter_id or session.get("chapter_id")
    is_preview = _is_free_preview_chapter(book, chapter_id)

    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    balance = int((fresh or {}).get("reading_seconds_balance", 0))

    deducted = 0
    status = "active"

    if is_preview:
        status = "preview"
    elif not payload.visible or payload.idle:
        status = "paused"
    elif balance <= 0:
        status = "depleted"
    else:
        deducted = min(HEARTBEAT_TICK_SECONDS, balance)
        new_balance = balance - deducted
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"reading_seconds_balance": new_balance}},
        )
        await db.wallet_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "type": "consume",
            "seconds": -deducted,
            "reason": f"Reading {book.get('title','')[:40]}",
            "created_at": now_iso(),
            "actor": "system",
        })
        balance = new_balance
        status = "depleted" if balance <= 0 else "active"

    await db.reading_sessions.update_one(
        {"id": payload.session_id},
        {
            "$set": {"last_heartbeat_at": now_iso(), "chapter_id": chapter_id},
            "$inc": {"seconds_consumed": deducted},
        },
    )

    return {
        "deducted_seconds": deducted,
        "remaining_seconds": balance,
        "status": status,
        "is_preview": is_preview,
    }


@api.post("/reader/session/end")
async def reader_session_end(payload: ReaderSessionEndIn, user=Depends(require_user)):
    res = await db.reading_sessions.update_one(
        {"id": payload.session_id, "user_id": user["id"], "status": "active"},
        {"$set": {"status": "ended", "ended_at": now_iso()}},
    )
    return {"ended": res.modified_count}


# Aliases for /reading/session/ endpoints (frontend compatibility)
@api.post("/reading/session/start")
async def reading_session_start_v2(payload: ReaderSessionStartIn, request: Request, user=Depends(require_user)):
    session_id = payload.session_id or str(uuid.uuid4())
    book_id = payload.book_id or payload.book_slug
    if not book_id:
        raise HTTPException(status_code=400, detail="Book id is required")
    now = datetime.utcnow()
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "active_reading_session": {
                    "session_id": session_id,
                    "book_id": book_id,
                    "chapter_id": payload.chapter_id,
                    "started_at": now,
                    "last_pulse_at": now,
                    "device": request.headers.get("user-agent", "unknown")[:100],
                }
            }
        },
    )
    return {"success": True, "session_id": session_id}


@api.post("/reading/session/end")
async def reading_session_end_v2(payload: ReaderSessionEndIn, principal: Optional[dict] = Depends(optional_principal)):
    if not principal or principal.get("role") != "user":
        return {"success": False, "status": "session_invalid"}
    user = principal
    await db.users.update_one({"id": user["id"]}, {"$unset": {"active_reading_session": ""}})
    return {"success": True}


@api.post("/reading/pulse")
async def reading_pulse(payload: ReaderSessionEndIn, principal: Optional[dict] = Depends(optional_principal)):
    if not principal or principal.get("role") != "user" or principal.get("status") == "blocked":
        return {"success": False, "status": "session_invalid"}
    user = principal
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0}) or user
    active = fresh.get("active_reading_session") or {}
    if active.get("session_id") != payload.session_id:
        return {"success": False, "status": "session_invalid"}

    wallet = int(fresh.get("reading_seconds_balance", fresh.get("wallet_seconds", 0)) or 0)
    if wallet <= 0:
        return {"success": False, "status": "wallet_empty", "wallet_seconds": 0}

    deduct = min(30, wallet)
    remaining = wallet - deduct
    status = "low_balance" if remaining <= LOW_BALANCE_THRESHOLD else "ok"
    now = datetime.utcnow()
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "wallet_seconds": remaining,
                "reading_seconds_balance": remaining,
                "active_reading_session.last_pulse_at": now,
            }
        },
    )
    return {"success": True, "status": status, "wallet_seconds": remaining}


@api.get("/reading/packs")
async def reading_packs():
    return [
        {"id": p["id"], "minutes": p["minutes"], "price": p["price_inr"], "label": p["label"]}
        for p in PACKS
    ]


# ---------- Reader: Gated chapter content ----------
# Returns chapter BODY only when the caller is authorised. Guests, blocked
# users and users with no reading time get a locked metadata-only response.
# Admin tokens always pass (used for the admin reader preview).
@api.get("/reader/chapter/{slug}/{chapter_id}")
async def reader_get_chapter(
    slug: str,
    chapter_id: str,
    principal: Optional[dict] = Depends(optional_principal),
):
    book = await db.books.find_one({"slug": slug, "is_published": True}, {"_id": 0})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    chapters = sorted((book.get("chapters") or []), key=lambda c: c.get("order", 0))
    target = next((c for c in chapters if c.get("id") == chapter_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Chapter not found")

    meta = {
        "id": target["id"],
        "title": target.get("title", ""),
        "order": target.get("order", 0),
    }
    is_preview = chapters[0].get("id") == chapter_id

    # Free preview is open to everyone — no auth, no deduction.
    if is_preview:
        return {
            "locked": False,
            "is_preview": True,
            "chapter": {**meta, "content": target.get("content", "")},
        }

    # Admin always has full access (admin reader preview).
    if principal and principal.get("role") == "admin":
        return {
            "locked": False,
            "is_preview": False,
            "chapter": {**meta, "content": target.get("content", "")},
        }

    # Reader user
    if principal and principal.get("role") == "user":
        if principal.get("status") == "blocked":
            return {
                "locked": True,
                "reason": "BLOCKED",
                "message": "Account is blocked. Please contact support.",
                "chapter": meta,
            }
        if int(principal.get("reading_seconds_balance", 0)) > 0:
            return {
                "locked": False,
                "is_preview": False,
                "chapter": {**meta, "content": target.get("content", "")},
            }
        return {
            "locked": True,
            "reason": "INSUFFICIENT_READING_TIME",
            "message": "Your reading time has ended. Top up to continue reading.",
            "chapter": meta,
        }

    # Guest
    return {
        "locked": True,
        "reason": "AUTH_REQUIRED",
        "message": "Sign in and add reading time to continue.",
        "chapter": meta,
    }


# ---------- Admin: Reader Users + Wallet ----------
@api.get("/admin/users")
async def admin_list_users(_=Depends(require_admin)):
    rows = await db.users.find(
        {"role": "user"},
        {"_id": 0, "password_hash": 0},
    ).sort("created_at", -1).to_list(2000)
    return [_user_public(r) for r in rows]


@api.post("/admin/users/{uid}/wallet/adjust")
async def admin_wallet_adjust(uid: str, payload: WalletAdjustIn, admin=Depends(require_admin)):
    user = await db.users.find_one({"id": uid, "role": "user"}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    seconds_delta = int(payload.minutes) * 60
    current = int(user.get("reading_seconds_balance", 0))
    new_balance = max(0, current + seconds_delta)
    actual_delta = new_balance - current
    await db.users.update_one(
        {"id": uid},
        {"$set": {"reading_seconds_balance": new_balance}},
    )
    await db.wallet_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "type": "credit" if actual_delta >= 0 else "debit",
        "seconds": actual_delta,
        "reason": payload.reason.strip() or ("Admin top-up" if actual_delta >= 0 else "Admin deduction"),
        "created_at": now_iso(),
        "actor": f"admin:{admin.get('email','')}",
    })
    return {
        "ok": True,
        "user_id": uid,
        "applied_seconds": actual_delta,
        "reading_seconds_balance": new_balance,
    }


@api.get("/admin/users/{uid}/transactions", response_model=List[WalletTransactionOut])
async def admin_user_transactions(uid: str, _=Depends(require_admin)):
    rows = await db.wallet_transactions.find(
        {"user_id": uid}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return rows


@api.patch("/admin/users/{uid}/status")
async def admin_user_status(uid: str, payload: UserStatusIn, _=Depends(require_admin)):
    if payload.status not in {"active", "blocked"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    res = await db.users.update_one({"id": uid, "role": "user"}, {"$set": {"status": payload.status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "id": uid, "status": payload.status}


# =====================================================================
# Razorpay test-mode wallet top-up
# =====================================================================

# ---------- Public: Pack catalogue ----------
@api.get("/payments/packs", response_model=List[PackOut])
async def payments_list_packs():
    return [PackOut(**p) for p in PACKS]


@api.get("/payments/config")
async def payments_config():
    """Lightweight config shim used by frontend to know if Razorpay is wired."""
    return {
        "configured": razorpay_keys_configured(),
        "mode": RAZORPAY_MODE,
        "key_id": RAZORPAY_KEY_ID if razorpay_keys_configured() else "",
    }


# ---------- Wallet credit helper (idempotent) ----------
async def _credit_wallet_for_intent(intent: dict, payment_id: Optional[str], source: str) -> dict:
    """Atomically transition a top-up intent to 'credited' and add minutes to
    the user's wallet. Safe against concurrent webhook + verify calls.
    Returns the refreshed intent.
    """
    # Atomic transition: only ONE caller can flip status from a non-credited
    # state to 'credited'. Prevents double-credit when the verify endpoint and
    # the webhook both fire for the same payment.
    set_doc: dict = {
        "status": "credited",
        "credited_at": now_iso(),
        "credited_by": source,  # "verify" | "webhook" | "admin_reconcile"
    }
    if payment_id:
        set_doc["razorpay_payment_id"] = payment_id
    res = await db.topup_intents.update_one(
        {"id": intent["id"], "status": {"$ne": "credited"}},
        {"$set": set_doc},
    )
    if res.modified_count != 1:
        # Already credited by another path — return the existing record.
        return await db.topup_intents.find_one({"id": intent["id"]}, {"_id": 0})

    seconds = int(intent["minutes"]) * 60
    user_id = intent["user_id"]
    # Race-safe credit using $inc.
    await db.users.update_one(
        {"id": user_id, "role": "user"},
        {"$inc": {"reading_seconds_balance": seconds}},
    )
    await db.wallet_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "credit",
        "seconds": seconds,
        "reason": f"Razorpay top-up · {intent.get('pack_id')} · {intent['minutes']} min",
        "created_at": now_iso(),
        "actor": f"razorpay:{source}",
        "topup_intent_id": intent["id"],
    })
    return await db.topup_intents.find_one({"id": intent["id"]}, {"_id": 0})


# ---------- Reader: create a top-up intent + Razorpay order ----------
@api.post("/payments/topup", response_model=TopUpCreateOut)
async def payments_create_topup(payload: TopUpCreateIn, user=Depends(require_user)):
    pack = PACKS_BY_ID.get(payload.pack_id)
    if not pack:
        raise HTTPException(status_code=400, detail="Unknown pack")
    if not razorpay_keys_configured():
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured yet. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to enable payments.",
        )
    client = get_razorpay_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Razorpay SDK is unavailable on this server.")

    intent_id = str(uuid.uuid4())
    receipt = f"earn-{intent_id[:24]}"  # Razorpay receipt must be <= 40 chars

    try:
        order = client.order.create({
            "amount": pack["amount_paise"],
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
            "notes": {
                "intent_id": intent_id,
                "user_id": user["id"],
                "pack_id": pack["id"],
                "minutes": str(pack["minutes"]),
            },
        })
    except Exception as exc:  # razorpay.errors.* — swallow to a clean 502
        logger.exception("Razorpay order.create failed")
        raise HTTPException(status_code=502, detail=f"Could not start payment: {exc}")

    await db.topup_intents.insert_one({
        "id": intent_id,
        "user_id": user["id"],
        "user_email": user.get("email", ""),
        "pack_id": pack["id"],
        "minutes": pack["minutes"],
        "amount_paise": pack["amount_paise"],
        "currency": "INR",
        "razorpay_order_id": order["id"],
        "razorpay_payment_id": None,
        "status": "created",  # created -> paid -> credited (or failed)
        "mode": RAZORPAY_MODE,
        "created_at": now_iso(),
        "credited_at": None,
        "credited_by": None,
    })

    return TopUpCreateOut(
        intent_id=intent_id,
        razorpay_order_id=order["id"],
        key_id=RAZORPAY_KEY_ID,
        amount=pack["amount_paise"],
        currency="INR",
        name="The Earnalism Digital Library",
        description=f'{pack["label"]} · {pack["minutes"]} minutes',
        pack=PackOut(**pack),
        prefill={
            "name": user.get("name", ""),
            "email": user.get("email", ""),
        },
    )


# ---------- Reader: verify Razorpay checkout signature & credit ----------
@api.post("/payments/verify")
async def payments_verify(payload: PaymentVerifyIn, user=Depends(require_user)):
    intent = await db.topup_intents.find_one(
        {"razorpay_order_id": payload.razorpay_order_id, "user_id": user["id"]},
        {"_id": 0},
    )
    if not intent:
        raise HTTPException(status_code=404, detail="Top-up intent not found")
    if not razorpay_keys_configured():
        raise HTTPException(status_code=503, detail="Razorpay is not configured")

    # Verify HMAC-SHA256(order_id|payment_id, KEY_SECRET)
    expected = _hmac_sha256_hex(
        RAZORPAY_KEY_SECRET,
        f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}".encode("utf-8"),
    )
    if not hmac.compare_digest(expected, payload.razorpay_signature):
        await db.topup_intents.update_one({"id": intent["id"]}, {"$set": {"status": "failed", "failed_reason": "bad_signature"}})
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    refreshed = await _credit_wallet_for_intent(intent, payload.razorpay_payment_id, "verify")
    user_doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return {
        "ok": True,
        "intent": refreshed,
        "reading_seconds_balance": int((user_doc or {}).get("reading_seconds_balance", 0)),
    }


# ---------- Razorpay webhook (authoritative) ----------
@api.post("/payments/webhook")
async def payments_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not RAZORPAY_WEBHOOK_SECRET:
        # Refuse to silently accept unsigned events.
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    expected = _hmac_sha256_hex(RAZORPAY_WEBHOOK_SECRET, raw_body)
    if not hmac.compare_digest(expected, signature):
        # Store the rejected event so admins can audit attempts.
        await db.payment_webhook_events.insert_one({
            "id": str(uuid.uuid4()),
            "event_id": None,
            "event": "unknown",
            "status": "rejected_bad_signature",
            "raw": raw_body.decode("utf-8", errors="replace")[:8000],
            "created_at": now_iso(),
        })
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        body = _json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = body.get("event", "")
    event_id = request.headers.get("X-Razorpay-Event-Id") or body.get("id")
    payment = (body.get("payload") or {}).get("payment", {}).get("entity") or {}
    payment_id = payment.get("id")
    order_id = payment.get("order_id")

    # Idempotency: reject duplicate event ids quickly.
    if event_id:
        seen = await db.payment_webhook_events.find_one({"event_id": event_id}, {"_id": 0})
        if seen:
            return {"ok": True, "duplicate": True, "event_id": event_id}

    log_doc = {
        "id": str(uuid.uuid4()),
        "event_id": event_id,
        "event": event,
        "status": "received",
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "raw": raw_body.decode("utf-8", errors="replace")[:8000],
        "created_at": now_iso(),
    }

    intent = None
    if order_id:
        intent = await db.topup_intents.find_one({"razorpay_order_id": order_id}, {"_id": 0})

    if event == "payment.captured" and intent:
        await _credit_wallet_for_intent(intent, payment_id, "webhook")
        log_doc["status"] = "credited"
    elif event == "payment.failed" and intent:
        await db.topup_intents.update_one(
            {"id": intent["id"], "status": "created"},
            {"$set": {"status": "failed", "razorpay_payment_id": payment_id, "failed_reason": payment.get("error_description", "payment_failed")}},
        )
        log_doc["status"] = "marked_failed"
    elif not intent:
        log_doc["status"] = "unmatched_intent"
    else:
        log_doc["status"] = "ignored"

    await db.payment_webhook_events.insert_one(log_doc)
    return {"ok": True, "event": event, "status": log_doc["status"]}


# ---------- Dev-only: simulate a webhook to exercise the credit flow ----------
@api.post("/payments/_simulate_topup")
async def payments_simulate_topup(payload: TopUpCreateIn, user=Depends(require_user)):
    """Dev-only mirror of /payments/topup that does NOT call Razorpay. Creates
    a top-up intent with a synthetic order id so the credit path can be
    exercised end-to-end before real keys are wired up.

    Disabled when RAZORPAY_MODE is not 'test'.
    """
    if RAZORPAY_MODE != "test":
        raise HTTPException(status_code=403, detail="Simulator disabled outside test mode")
    pack = PACKS_BY_ID.get(payload.pack_id)
    if not pack:
        raise HTTPException(status_code=400, detail="Unknown pack")
    intent_id = str(uuid.uuid4())
    fake_order_id = f"order_test_{uuid.uuid4().hex[:18]}"
    await db.topup_intents.insert_one({
        "id": intent_id,
        "user_id": user["id"],
        "user_email": user.get("email", ""),
        "pack_id": pack["id"],
        "minutes": pack["minutes"],
        "amount_paise": pack["amount_paise"],
        "currency": "INR",
        "razorpay_order_id": fake_order_id,
        "razorpay_payment_id": None,
        "status": "created",
        "mode": "test_simulated",
        "created_at": now_iso(),
        "credited_at": None,
        "credited_by": None,
    })
    return {
        "intent_id": intent_id,
        "razorpay_order_id": fake_order_id,
        "amount": pack["amount_paise"],
        "currency": "INR",
        "pack": PackOut(**pack).model_dump(),
        "simulated": True,
    }


@api.post("/payments/_simulate_webhook")
async def payments_simulate_webhook(
    intent_id: str,
    user=Depends(require_user),
):
    """Test helper. Only enabled when RAZORPAY_MODE=='test'. Lets a logged-in
    user (or admin via curl) drive an intent to 'credited' WITHOUT real
    Razorpay — useful when keys are not configured yet.
    """
    if RAZORPAY_MODE != "test":
        raise HTTPException(status_code=403, detail="Simulator disabled outside test mode")
    intent = await db.topup_intents.find_one({"id": intent_id}, {"_id": 0})
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    if intent["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your intent")
    if intent["status"] == "credited":
        return {"ok": True, "duplicate": True, "intent": intent}
    fake_payment_id = f"pay_test_{uuid.uuid4().hex[:20]}"
    refreshed = await _credit_wallet_for_intent(intent, fake_payment_id, "simulate")
    await db.payment_webhook_events.insert_one({
        "id": str(uuid.uuid4()),
        "event_id": f"evt_sim_{uuid.uuid4().hex[:20]}",
        "event": "payment.captured",
        "status": "credited_simulated",
        "razorpay_order_id": intent.get("razorpay_order_id"),
        "razorpay_payment_id": fake_payment_id,
        "raw": "{simulated}",
        "created_at": now_iso(),
    })
    user_doc = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return {
        "ok": True,
        "simulated": True,
        "intent": refreshed,
        "reading_seconds_balance": int((user_doc or {}).get("reading_seconds_balance", 0)),
    }


# ---------- Reader: own top-up history ----------
@api.get("/payments/me/intents")
async def payments_my_intents(user=Depends(require_user)):
    rows = await db.topup_intents.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows


# ---------- Admin: payments dashboard ----------
@api.get("/admin/payments/intents")
async def admin_list_intents(_=Depends(require_admin)):
    rows = await db.topup_intents.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return rows


@api.get("/admin/payments/webhooks")
async def admin_list_webhooks(_=Depends(require_admin)):
    rows = await db.payment_webhook_events.find({}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return rows


@api.post("/admin/payments/intents/{intent_id}/reconcile")
async def admin_reconcile_intent(intent_id: str, payload: PaymentReconcileIn, admin=Depends(require_admin)):
    """Manually mark an intent as credited (e.g. webhook never fired). Idempotent."""
    intent = await db.topup_intents.find_one({"id": intent_id}, {"_id": 0})
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    if intent["status"] == "credited":
        return {"ok": True, "duplicate": True, "intent": intent}
    refreshed = await _credit_wallet_for_intent(
        intent,
        intent.get("razorpay_payment_id"),
        f"admin_reconcile:{admin.get('email','')}:{payload.note[:80]}",
    )
    return {"ok": True, "intent": refreshed}


app.include_router(api)

cors_origins = {
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}
cors_origins.update(
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
)

app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=sorted(cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ---------- Seed ----------
SEED_CATEGORIES = [
    {"slug": "business", "name": "Business & Entrepreneurship", "description": "Disciplined founder reads on building, growing, and sustaining ventures.", "order": 1, "image_url": "https://images.unsplash.com/photo-1769184614794-f6e910de6128?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NDh8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGFyY2hpdGVjdHVyZSUyMGdvbGQlMjB3YXJtfGVufDB8fHx8MTc3NzYxNzE5MHww&ixlib=rb-4.1.0&q=85"},
    {"slug": "self-growth", "name": "Self-Growth", "description": "Quiet, deliberate books for the inner architect.", "order": 2, "image_url": "https://images.unsplash.com/photo-1631737859676-20e3d0a25f01?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2MDV8MHwxfHNlYXJjaHwyfHxjYWxtJTIwc2lsayUyMGZhYnJpYyUyMGZsb3dpbmclMjBpdm9yeXxlbnwwfHx8fDE3Nzc2MTcxOTB8MA&ixlib=rb-4.1.0&q=85"},
    {"slug": "literature", "name": "Literature", "description": "Timeless prose, modern voices, and stories that linger.", "order": 3, "image_url": "https://images.unsplash.com/photo-1604778561734-cdfff7bb3c3b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzB8MHwxfHNlYXJjaHwzfHxhbnRpcXVlJTIwYm9vayUyMHBhZ2VzJTIwbWFjcm8lMjBwaG90b2dyYXBoeXxlbnwwfHx8fDE3Nzc2MTcxNzd8MA&ixlib=rb-4.1.0&q=85"},
    {"slug": "spirituality", "name": "Spirituality", "description": "Reflections that return the reader to themselves.", "order": 4, "image_url": "https://images.unsplash.com/photo-1774485423141-a63a49ae8df7?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2ODh8MHwxfHNlYXJjaHw0fHxjYWxtJTIwbWluaW1hbCUyMGFic3RyYWN0JTIwd2FybSUyMHRleHR1cmV8ZW58MHx8fHwxNzc3NjE3MTc3fDA&ixlib=rb-4.1.0&q=85"},
    {"slug": "bengali-reading", "name": "Bengali Reading", "description": "A devoted shelf for Bengali literature and thought.", "order": 5, "image_url": "https://images.unsplash.com/photo-1644150568283-d2c0b31cd703?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzV8MHwxfHNlYXJjaHwxfHx0ZXJyYWNvdHRhJTIwYXJ0JTIwdGV4dHVyZSUyMG1hY3JvfGVufDB8fHx8MTc3NzYxNzE5MHww&ixlib=rb-4.1.0&q=85"},
    {"slug": "technology", "name": "Technology", "description": "Books on software, AI, data, digital systems, product thinking, and the future of work.", "order": 6, "image_url": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?crop=entropy&cs=srgb&fm=jpg&w=1600&q=85"},
]

SEED_TECH_BOOK = {
    "slug": "the-architecture-of-intelligent-systems",
    "title": "The Architecture of Intelligent Systems",
    "subtitle": "On software, data, and the engineering discipline behind modern digital products.",
    "author": "The Earnalism",
    "category_slug": "technology",
    "short_description": "A thoughtful guide to software architecture, data platforms, AI systems, and the craft of building durable digital products.",
    "description": "The Architecture of Intelligent Systems is written for engineers, founders, and product leaders who want their software to last longer than a quarter. Across patient chapters on services, data platforms, machine intelligence, and the human discipline behind them, it returns again and again to a single idea: technology earns its place through clarity, restraint, and care.",
    "cover_image_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
    "estimated_reading_time": "5 hours",
    "price_paperback": "",
    "price_ebook": "",
    "buy_url": "",
    "formats": ["Ebook"],
    "benefits": [
        "A working vocabulary for modern software architecture",
        "Frameworks for designing data platforms that scale gently",
        "An honest view of AI systems — what they can and cannot promise",
        "A craft-first lens on engineering leadership",
    ],
    "who_for": [
        "Engineers moving from individual contribution to system design",
        "Founders making consequential technology choices",
        "Product leaders responsible for long-lived digital products",
    ],
    "learnings": [
        "How to choose architectures that respect both users and budgets",
        "The discipline of data — quality, lineage, and quiet governance",
        "Where AI belongs in a product, and where it does not",
        "Building engineering teams that compound over years",
    ],
    "about_author": "Curated on the shelves of The Earnalism Digital Library — an independent reading room devoted to thoughtful business, literature, and the craft of modern technology.",
    "chapters": [
        {"id": str(uuid.uuid4()), "order": 0, "title": "The Working Vocabulary",
         "content": "Every technical discipline arrives with two vocabularies — the one used in meetings, and the one that actually ships software.\n\nThe working vocabulary is smaller, sharper, and unglamorous. It names failure modes instead of features. It refuses adjectives that cannot be measured. When a senior engineer says observability, they mean: I can read this system's mind at three in the morning without waking anyone up.\n\nGood architectures begin with this vocabulary. The rest of the system is a long conversation held in its grammar."},
        {"id": str(uuid.uuid4()), "order": 1, "title": "Data Platforms That Scale Gently",
         "content": "A data platform is, at its best, a library. It arranges the facts of the business so that any future question can be asked with dignity.\n\nThe temptation in young companies is to choose tools for the scale they hope to reach. The temptation in older companies is to preserve the tools of a scale they have already passed. Both miss the point. A platform scales gently when each layer does one clear job: ingestion that is honest, storage that is queryable, modelling that is owned, and serving that is fast enough for the question being asked.\n\nComplexity is not an achievement. Clarity is."},
        {"id": str(uuid.uuid4()), "order": 2, "title": "Where AI Belongs — and Where It Does Not",
         "content": "Artificial intelligence is both a capability and a temperament.\n\nAs a capability, it is astonishing: pattern recognition, synthesis, generation, prediction. As a temperament, it is dangerous: quick answers where slow ones are required, confident prose where uncertainty would serve the reader better, a whisper of automation inside decisions that deserve human attention.\n\nThe architect's job is to route each problem to the right temperament. Some belong to machines. Some belong to the person still awake at the end of the quarter."},
    ],
    "is_published": True,
}

SEED_BOOK = {
    "slug": "brownies-to-break-even-and-beyond",
    "title": "Brownies to Break-Even and Beyond",
    "subtitle": "A lyrical business journey for dreamers, founders, and first-time entrepreneurs.",
    "author": "The Earnalism",
    "category_slug": "business",
    "short_description": "A disciplined yet tender memoir-guide for turning passion into a profitable, principled venture.",
    "description": "Part memoir, part operating manual, Brownies to Break-Even and Beyond traces the slow craft of building a small business with care. From the first costing sheet to the first profitable quarter, every chapter pairs lived story with the kind of practical clarity rarely offered to bakers, makers, and quiet entrepreneurs.",
    "cover_image_url": "https://images.unsplash.com/photo-1519764340700-3db40311f21e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxibGFuayUyMG1pbmltYWwlMjBib29rJTIwY292ZXIlMjBmbGF0JTIwbGF5fGVufDB8fHx8MTc3NzYxNzE5MHww&ixlib=rb-4.1.0&q=85",
    "estimated_reading_time": "4 hours",
    "price_paperback": "",
    "price_ebook": "",
    "buy_url": "",
    "formats": ["Ebook"],
    "is_published": True,
    "benefits": [
        "A founder's framework for pricing without guilt",
        "Honest unit economics that respect the craft",
        "A gentle path from side-project to small institution",
        "Marketing that sounds like you, not a template",
    ],
    "who_for": [
        "Bakers, makers, and creative founders building their first venture",
        "Quiet entrepreneurs who prefer depth over hype",
        "Operators ready to move from busy to profitable",
    ],
    "learnings": [
        "How to design a product that pays for itself",
        "The discipline of clean books and honest margins",
        "Building a brand that compounds with each season",
        "Scaling without losing the texture of your work",
    ],
    "about_author": "Curated on the shelves of The Earnalism Digital Library — an independent reading room devoted to thoughtful business, literature, and self-growth.",
    "chapters": [
        {"id": str(uuid.uuid4()), "order": 0, "title": "The First Costing Sheet",
         "content": "Most first ventures begin with a feeling — a warmth, a hunch, a recipe that makes people stop mid-sentence.\n\nBut a business begins the moment that feeling meets a costing sheet.\n\nThe first sheet is uncomfortable. It asks for ingredient weights, packaging cents, the honest price of an afternoon. It resists flourish. And yet, somewhere between the third row and the fifth, the costing sheet becomes something unexpected — a quiet portrait of the work itself. Every line you enter is an act of respect.\n\nBegin there. Before the logo, before the launch, before the pretty camera angle. Sit with the sheet until it holds every real cost. The venture that comes afterward will carry that care in its bones."},
        {"id": str(uuid.uuid4()), "order": 1, "title": "Pricing Without Guilt",
         "content": "Pricing is the first place a founder learns to stand up for their own work.\n\nNumbers carry beliefs. A timid price tells your customer the work is smaller than it is. A reckless one borrows credibility you have not yet earned. The right price is a quiet sentence: this is what it costs to make with care, and this is the margin that lets the making continue.\n\nCharge for your hands. Charge for your judgment. Charge for the years you spent learning the difference between good and almost-good. A business that refuses to price its craft cannot protect it.\n\nThere is no apology in a fair price. Only arithmetic, and kindness to the person writing the cheque six months from now — you."},
        {"id": str(uuid.uuid4()), "order": 2, "title": "From Side-Project to Small Institution",
         "content": "There comes a week — usually quietly — when the project starts to outgrow evenings.\n\nOrders arrive faster than the kitchen empties. Messages accumulate. Someone asks about invoicing, and the honest answer is, I'm figuring it out. This is not a problem. It is the first sign that the work is becoming an institution — a small, dignified one, but an institution nonetheless.\n\nThe transition asks for three slow disciplines: books that close at the end of each week, a calendar that respects weekends, and a customer you would recognise in a crowd. None of it arrives in a single brave day. It arrives in a series of tiny preferences, each one a vote for the business you want to still be running in a decade.\n\nA small institution is not a downgrade from a large one. It is a particular kind of house — one built to last."},
    ],
    "is_published": True,
}

SEED_POSTS = [
    {
        "slug": "why-every-small-business-needs-a-story-before-a-strategy",
        "title": "Why Every Small Business Needs a Story Before a Strategy",
        "excerpt": "Strategy without story is choreography without music. Here's how to find the line that holds your business together.",
        "content": "Most small businesses arrive at strategy too early. They map the funnel before they have found the feeling — the singular line a customer carries home. A story is not a tagline; it is the gravitational center that makes every later decision feel inevitable. When you know the story, pricing becomes posture, marketing becomes memory, and operations become craft.\n\nBegin with the moment you would defend in a quiet room: the reason this venture is worth your unhurried years. Write it down without flourish. Read it aloud. Then build the strategy that protects it.",
        "category": "Business",
        "pull_quote": "Strategy without story is choreography without music.",
        "cover_image_url": "https://images.unsplash.com/photo-1764087957302-ef0756ed8e0a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBmb3VudGFpbiUyMHBlbiUyMHdyaXRpbmclMjBkZXNrfGVufDB8fHx8MTc3NzYxNzE3N3ww&ixlib=rb-4.1.0&q=85",
        "is_published": True,
    },
    {
        "slug": "the-quiet-power-of-a-premium-bookstore-brand",
        "title": "The Quiet Power of a Premium Bookstore Brand",
        "excerpt": "Why restraint, ritual, and refusal are the most underrated assets in running a modern independent bookstore.",
        "content": "A premium brand is not loud — it is precise. It refuses noisy launches, declines easy collaborations, and waits for the right shelf. In bookstores especially, restraint is the most expensive ingredient. The Earnalism is built around the same principle: fewer titles, deeper readings, a longer relationship with each book.\n\nTrust accrues like compound interest. Each careful decision becomes the next reader's reason to return.",
        "category": "Brand",
        "pull_quote": "A premium brand is not loud — it is precise.",
        "cover_image_url": "https://images.unsplash.com/photo-1565357457446-4705a9445e54?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzB8MHwxfHNlYXJjaHwyfHxhbnRpcXVlJTIwYm9vayUyMHBhZ2VzJTIwbWFjcm8lMjBwaG90b2dyYXBoeXxlbnwwfHx8fDE3Nzc2MTcxNzd8MA&ixlib=rb-4.1.0&q=85",
        "is_published": True,
    },
    {
        "slug": "how-reading-shapes-better-founders",
        "title": "How Reading Shapes Better Founders",
        "excerpt": "The founders who endure are not always the loudest readers — they are the most patient ones.",
        "content": "Books slow the founder's mind into the right tempo. They argue with you, comfort you, and rearrange your assumptions while you sleep. Strategy decks fade in a quarter; a great chapter stays for a decade.\n\nReading is not a productivity hack. It is a posture — a way of returning to depth in a culture that rewards velocity. The founders who endure tend to read like they breathe: regularly, unhurriedly, and across worlds.",
        "category": "Self-Growth",
        "pull_quote": "Reading is not a productivity hack. It is a posture.",
        "cover_image_url": "https://images.unsplash.com/photo-1761237771835-1d2914546cea?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2ODh8MHwxfHNlYXJjaHwzfHxjYWxtJTIwbWluaW1hbCUyMGFic3RyYWN0JTIwd2FybSUyMHRleHR1cmV8ZW58MHx8fHwxNzc3NjE3MTc3fDA&ixlib=rb-4.1.0&q=85",
        "is_published": True,
    },
]
