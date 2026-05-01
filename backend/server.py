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

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
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

bearer = HTTPBearer(auto_error=False)

async def require_admin(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload


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

class Book(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    title: str
    subtitle: str = ""
    category_slug: str
    short_description: str = ""
    description: str = ""
    cover_image_url: str = ""
    price_paperback: str = ""
    price_ebook: str = ""
    buy_url: str = ""
    formats: List[str] = Field(default_factory=lambda: ["Paperback", "Ebook"])
    benefits: List[str] = Field(default_factory=list)
    who_for: List[str] = Field(default_factory=list)
    learnings: List[str] = Field(default_factory=list)
    about_author: str = ""
    is_published: bool = True
    created_at: str = Field(default_factory=now_iso)

class BookIn(BaseModel):
    title: str
    subtitle: str = ""
    category_slug: str
    short_description: str = ""
    description: str = ""
    cover_image_url: str = ""
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
    return docs

@api.get("/books/{slug}", response_model=Book)
async def get_book(slug: str):
    doc = await db.books.find_one({"slug": slug, "is_published": True}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")
    return doc


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
    "category_slug": "technology",
    "short_description": "A thoughtful guide to software architecture, data platforms, AI systems, and the craft of building durable digital products.",
    "description": "The Architecture of Intelligent Systems is written for engineers, founders, and product leaders who want their software to last longer than a quarter. Across patient chapters on services, data platforms, machine intelligence, and the human discipline behind them, it returns again and again to a single idea: technology earns its place through clarity, restraint, and care.",
    "cover_image_url": "https://images.unsplash.com/photo-1532012197267-da84d127e765?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
    "price_paperback": "",
    "price_ebook": "",
    "buy_url": "",
    "formats": ["Paperback", "Ebook"],
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
    "about_author": "Curated on the shelves of The Earnalism — an independent bookstore devoted to thoughtful business, literature, and the craft of modern technology.",
    "is_published": True,
}

SEED_BOOK = {
    "slug": "brownies-to-break-even-and-beyond",
    "title": "Brownies to Break-Even and Beyond",
    "subtitle": "A lyrical business journey for dreamers, founders, and first-time entrepreneurs.",
    "category_slug": "business",
    "short_description": "A disciplined yet tender memoir-guide for turning passion into a profitable, principled venture.",
    "description": "Part memoir, part operating manual, Brownies to Break-Even and Beyond traces the slow craft of building a small business with care. From the first costing sheet to the first profitable quarter, every chapter pairs lived story with the kind of practical clarity rarely offered to bakers, makers, and quiet entrepreneurs.",
    "cover_image_url": "https://images.unsplash.com/photo-1519764340700-3db40311f21e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwxfHxibGFuayUyMG1pbmltYWwlMjBib29rJTIwY292ZXIlMjBmbGF0JTIwbGF5fGVufDB8fHx8MTc3NzYxNzE5MHww&ixlib=rb-4.1.0&q=85",
    "price_paperback": "",
    "price_ebook": "",
    "buy_url": "",
    "formats": ["Paperback", "Ebook"],
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
    "about_author": "Curated on the shelves of The Earnalism — an independent bookstore devoted to thoughtful business, literature, and self-growth.",
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
