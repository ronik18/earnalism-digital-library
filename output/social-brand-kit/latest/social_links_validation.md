# Social Links Validation

Status: `OPERATOR_REQUIRED`

This validation checks syntax and platform domains only. It does not call social platform APIs and does not publish anything.

| Env var | Platform | Status | Issue |
| --- | --- | --- | --- |
| `REACT_APP_INSTAGRAM_URL` | Instagram | MISSING_OPERATOR_REQUIRED | URL is empty or not configured. |
| `REACT_APP_YOUTUBE_URL` | YouTube | MISSING_OPERATOR_REQUIRED | URL is empty or not configured. |
| `REACT_APP_FACEBOOK_URL` | Facebook | MISSING_OPERATOR_REQUIRED | URL is empty or not configured. |
| `REACT_APP_LINKEDIN_URL` | LinkedIn | MISSING_OPERATOR_REQUIRED | URL is empty or not configured. |
| `REACT_APP_X_URL` | X | MISSING_OPERATOR_REQUIRED | URL is empty or not configured. |
| `REACT_APP_WHATSAPP_CHANNEL_URL` | WhatsApp Channel | MISSING_OPERATOR_REQUIRED | URL is empty or not configured. |
| `REACT_APP_TELEGRAM_CHANNEL_URL` | Telegram | MISSING_OPERATOR_REQUIRED | URL is empty or not configured. |

## Operator Next Step

Create the real social profiles manually, then set only the verified public profile URLs in the matching frontend environment variables. Footer icons must remain hidden until real http/https URLs are configured.
