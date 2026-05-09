# Production Deployment Guide for Earnalism Digital Library

## Required environment variables

### Backend (`backend/.env`)
- `MONGO_URL` — MongoDB connection string (use MongoDB Atlas in production)
- `DB_NAME` — database name; example: `earnalism`
- `JWT_SECRET` — long random secret for signing JWTs
- `ADMIN_EMAIL` — admin login email
- `ADMIN_PASSWORD` — admin login password
- `COOKIE_SECURE` — `true` for HTTPS production
- `COOKIE_SAMESITE` — `lax` recommended
- `FRONTEND_URL` — production frontend URL, e.g. `https://yourdomain.com`
- `CORS_ORIGINS` — comma-separated allowed origins, e.g. `https://yourdomain.com`

### Payments
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`
- `RAZORPAY_MODE=live`

### Images
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

### Authentication
- `GOOGLE_CLIENT_ID`
- `MSG91_AUTH_KEY`
- `MSG91_TEMPLATE_ID`

## Frontend
Use production env values in `frontend/.env.production` or your deployment provider's environment manager.

Example `frontend/.env.production`:
```env
REACT_APP_BACKEND_URL=https://api.yourdomain.com
REACT_APP_API_URL=https://api.yourdomain.com
REACT_APP_GOOGLE_CLIENT_ID=your-google-client-id
```

## Deployment checklist
1. Set backend env variables securely in your hosting environment.
2. Configure `CORS_ORIGINS` or `FRONTEND_URL` to your live frontend domain.
3. Provision MongoDB Atlas for production.
4. Provision Cloudinary and Razorpay accounts.
5. Create a Google OAuth client and set the client ID in both frontend and backend.
6. Ensure `REACT_APP_BACKEND_URL` and `REACT_APP_API_URL` point to the same production API.
7. Build the frontend with `npm run build` and deploy the static assets.
8. Run the backend with `uvicorn server:app --host 0.0.0.0 --port 8000` or your platform's equivalent.

## Notes
- `frontend/src/pages/Reader.jsx` now uses `REACT_APP_BACKEND_URL` first for consistency.
- `frontend/src/lib/api.js` falls back to `REACT_APP_API_URL` and `http://localhost:8000` for local development.
- Keep secrets out of source control and use deployment provider environment management.
