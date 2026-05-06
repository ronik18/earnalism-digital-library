from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import re
import uuid
import logging
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# ---------- DB ----------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = "HS256"
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@theearnalism.com')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Cookie config — httpOnly session cookie. SECURE flag is on by default (HTTPS in prod);
# can be disabled via env for plain-HTTP local dev only.
SESSION_COOKIE = "ear_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax")


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
    book_slug: str
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
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # ----- startup -----
    # indexes
    await db.users.create_index("email", unique=True)
    await db.books.create_index("slug", unique=True)
    await db.categories.create_index("slug", unique=True)
    await db.blog_posts.create_index("slug", unique=True)
    await db.newsletter.create_index("email", unique=True)
    await db.settings.create_index("key", unique=True)
    await db.wallet_transactions.create_index([("user_id", 1), ("created_at", -1)])
    await db.reading_sessions.create_index([("user_id", 1), ("started_at", -1)])
    await db.reading_sessions.create_index("status")

    # admin (seed only if absent; do NOT overwrite password so admin can change it via UI)
    existing = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": ADMIN_EMAIL.lower(),
            "password_hash": hash_password(ADMIN_PASSWORD),
            "name": "Admin",
            "role": "admin",
            "created_at": now_iso(),
        })
        logger.info("Seeded admin user")

    # test reader user (idempotent — only inserted if absent)
    test_user_email = "reader@earnalism.com"
    if not await db.users.find_one({"email": test_user_email}):
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": test_user_email,
            "password_hash": hash_password("Reader@2026"),
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


@api.get("/users/me", response_model=UserOut)
async def user_me(user=Depends(require_user)):
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return UserOut(**_user_public(fresh or user))


@api.get("/users/me/transactions", response_model=List[WalletTransactionOut])
async def user_my_transactions(user=Depends(require_user)):
    rows = await db.wallet_transactions.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows


# ---------- Reader: Sessions + Heartbeat ----------
HEARTBEAT_TICK_SECONDS = 30


@api.post("/reader/session/start")
async def reader_session_start(payload: ReaderSessionStartIn, user=Depends(require_user)):
    book = await db.books.find_one({"slug": payload.book_slug, "is_published": True}, {"_id": 0})
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
        "book_slug": payload.book_slug,
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


app.include_router(api)

# CORS: Bearer-token auth only (no cookies), so credentials=False is correct.
# A wildcard origin with credentials=True is rejected by browsers.
_cors_env = os.environ.get('CORS_ORIGINS', '*')
_origins = [o.strip() for o in _cors_env.split(',') if o.strip()]
_allow_credentials = not (len(_origins) == 1 and _origins[0] == '*')
app.add_middleware(
    CORSMiddleware,
    allow_credentials=_allow_credentials,
    allow_origins=_origins,
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
