from fastapi import APIRouter, HTTPException, Depends
import httpx
import os
from .auth import create_token

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
MSG91_AUTH_KEY = os.getenv('MSG91_AUTH_KEY')

@router.post("/auth/google")
async def google_auth(token: str):
    # Verify Google token
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}")
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid Google token")
        user_info = resp.json()

    # Create or get user
    # Assume db
    user = await db.users.find_one({"email": user_info['email']})
    if not user:
        user = {
            "_id": str(uuid.uuid4()),
            "email": user_info['email'],
            "name": user_info.get('name'),
            "google_id": user_info['sub']
        }
        await db.users.insert_one(user)

    # Create JWT
    jwt_token = create_token(user)
    return {"token": jwt_token, "user": user}

@router.post("/auth/otp/send")
async def send_otp(phone: str):
    # Send OTP via MSG91
    url = f"https://api.msg91.com/api/v5/otp?authkey={MSG91_AUTH_KEY}&template_id=&mobile={phone}&otp_length=6"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to send OTP")
    return {"message": "OTP sent"}

@router.post("/auth/otp/verify")
async def verify_otp(phone: str, otp: str):
    # Verify OTP
    url = f"https://api.msg91.com/api/v5/otp/verify?authkey={MSG91_AUTH_KEY}&mobile={phone}&otp={otp}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid OTP")

    # Create or get user
    user = await db.users.find_one({"phone": phone})
    if not user:
        user = {
            "_id": str(uuid.uuid4()),
            "phone": phone
        }
        await db.users.insert_one(user)

    jwt_token = create_token(user)
    return {"token": jwt_token, "user": user}