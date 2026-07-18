# Canva Logo Publish Workflow

The live logo is controlled by the authenticated Admin Settings surface. The
header, sign-in, admin, and footer lockups all read the public `brand.logo_url`
setting; when it is empty, the bundled Earnalism lockup is used.

## Operator flow

1. In Canva, export the complete Earnalism logo lockup as a transparent PNG or
   WebP. Keep the artwork at least 32px on each axis and under 4 MB. A wide
   lockup works best in the header; do not export a symbol-only file unless it
   is intended to replace the complete lockup.
2. Sign in to `/admin`, open the **Settings** tab, and choose **Upload logo**.
3. Review the preview, then choose **Save brand**. Uploading stages the asset;
   saving the brand setting is the explicit publish action.
4. Open the public site in a fresh tab and verify the header, mobile header,
   sign-in page, footer, and admin lockup. The backend clears its public
   settings cache when the setting is saved.

The API is authenticated and never exposes Cloudinary credentials to the
browser. The upload endpoint is `POST /api/admin/settings/brand/logo`; the
setting is saved with `PUT /api/admin/settings/brand`.

## Production prerequisite

The Railway backend must have `ENABLE_ADMIN_MEDIA_UPLOADS=true` for the
authenticated upload action, plus the existing three-part Cloudinary
credentials: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and
`CLOUDINARY_API_SECRET`. The API rejects SVG uploads intentionally; raster
PNG/WebP keeps the public brand surface predictable and avoids serving active
markup from a user-managed logo field.
