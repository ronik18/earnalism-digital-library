# Production Deployment Guide

This repo is production-ready for a cost-optimized Hostinger VPS deployment:

- React is built once and served as static files by Nginx.
- FastAPI runs behind Caddy with health checks.
- Caddy terminates HTTPS automatically and reverse-proxies `/api/*`.
- MongoDB runs as a private Docker service by default.
- Cloudinary stores uploaded images outside the server filesystem.
- Razorpay, Google OAuth, MSG91, and PostHog are environment-driven.

## Recommended Hostinger Setup

Use a Hostinger VPS, not basic Web/Cloud shared hosting, because this app needs a long-running Python API and MongoDB. Hostinger's own docs say MongoDB is not available on Web/Cloud plans and requires VPS-style hosting.

Start with the smallest VPS that gives at least 2 vCPU and 4 GB RAM if you expect real users. Use the same VPS for frontend, backend, Caddy, and MongoDB at launch. Move MongoDB to Atlas later if backups, point-in-time restore, or multi-region reliability become more important than lowest monthly cost.

## DNS

Point these records to the VPS public IPv4:

```text
A      @      <VPS_IPV4>
A      www    <VPS_IPV4>
```

If you use IPv6:

```text
AAAA   @      <VPS_IPV6>
AAAA   www    <VPS_IPV6>
```

Wait for DNS propagation before expecting HTTPS certificates to issue.

## Production Environment

On the VPS:

```bash
cp deploy/production.env.example deploy/production.env
nano deploy/production.env
```

Set at minimum:

- `SITE_DOMAIN`
- `ACME_EMAIL`
- `MONGO_INITDB_ROOT_PASSWORD`
- `MONGO_URL` with the same Mongo password
- `JWT_SECRET`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `FRONTEND_URL`
- `CORS_ORIGINS`
- Razorpay live keys and webhook secret
- Cloudinary keys
- Google OAuth and MSG91 keys if those login methods are enabled

For same-domain deployment, leave `REACT_APP_BACKEND_URL` and `REACT_APP_API_URL` empty. The frontend will call `/api`, and Caddy will route it to FastAPI.

## Deploy

Install Docker and Docker Compose on the VPS, then from the repo root:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml up -d --build
```

Check health:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml ps
curl -I https://$SITE_DOMAIN
curl https://$SITE_DOMAIN/api/health
```

View logs:

```bash
docker compose --env-file deploy/production.env -f docker-compose.prod.yml logs -f --tail=100
```

Update release:

```bash
git pull
docker compose --env-file deploy/production.env -f docker-compose.prod.yml up -d --build
docker image prune -f
```

## Backups

Run a MongoDB backup:

```bash
sh deploy/backup-mongo.sh
```

Add a daily cron entry on the VPS:

```cron
15 2 * * * cd /path/to/earnalism-digital-library && sh deploy/backup-mongo.sh >> /var/log/earnalism-backup.log 2>&1
```

Download backups off the VPS regularly. A VPS snapshot is useful, but it is not a substitute for database backups.

## Razorpay Webhook

Set the webhook URL in Razorpay:

```text
https://yourdomain.com/api/payments/webhook
```

Use the same value for `RAZORPAY_WEBHOOK_SECRET` in `deploy/production.env`.

## Google OAuth

Authorized JavaScript origin:

```text
https://yourdomain.com
```

Authorized redirect/callback origins depend on the exact Google OAuth flow, but the frontend currently uses the Google Identity popup flow.

## Operational Notes

- Keep ports `80` and `443` open to the public.
- Do not expose MongoDB to the public internet.
- Rotate `JWT_SECRET` only when you are ready to invalidate all active sessions.
- Use `WEB_CONCURRENCY=2` on small VPS plans; raise it after measuring CPU and memory.
- PostHog is disabled unless `REACT_APP_POSTHOG_KEY` is set at build time.
- Uploaded admin images go to Cloudinary, so app containers can be rebuilt safely.

## Access Needed For Direct Deployment

To deploy this from Codex, provide one of:

1. SSH access to the Hostinger VPS: host, username, port, and an SSH key available on this machine.
2. A configured Hostinger MCP/API connector with access to VPS, DNS, and Docker operations.
3. Hostinger Docker Manager access plus the GitHub repo connected to it.

Without one of those, the repo can be made production-ready locally, but I cannot push it into your Hostinger account directly from this session.
