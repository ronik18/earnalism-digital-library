from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
import os
from config.cloudinary import upload_image
from utils.content_processor import process_docx_content
from motor.motor_asyncio import AsyncIOMotorClient
from .auth import get_current_user

router = APIRouter()

# Assume db is available
db = None  # Need to import or get from main

@router.post("/books/{book_id}/cover")
async def upload_cover(book_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Upload to Cloudinary
    file_bytes = await file.read()
    public_id = f"book_covers/{book_id}"
    upload_result = upload_image(file_bytes, public_id=public_id)

    # Update book in DB
    await db.books.update_one(
        {"_id": book_id},
        {"$set": {"cover_url": upload_result['url']}}
    )

    return {"url": upload_result['url']}

@router.post("/books/{book_id}/upload")
async def upload_content(book_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="File must be a .docx file")

    # Save temp file
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Process content
    processed = process_docx_content(temp_path)

    # Update book in DB
    await db.books.update_one(
        {"_id": book_id},
        {"$set": {"content": processed['html'], "images": processed['images']}}
    )

    # Clean up
    os.remove(temp_path)

    return {"message": "Content uploaded successfully"}