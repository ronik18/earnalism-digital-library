"""Production entrypoint retaining the temporary new-purchase pause.

The underlying application and its historical source contracts stay unchanged.
This outer ASGI boundary never reads a purchase body or invokes a purchase
handler. Existing access, settlement, refunds and lifecycle events pass through.
Reopening requires a reviewed entrypoint change; no environment toggle exists.
"""
from starlette.responses import JSONResponse

try:
    from .commerce_territory import COMMERCE_ORDER_PATH
except ImportError:
    from commerce_territory import COMMERCE_ORDER_PATH


class PurchaseClosedApp:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (scope["type"] == "http" and scope["method"] == "POST"
                and scope["path"].rstrip("/") == COMMERCE_ORDER_PATH):
            response = JSONResponse(
                status_code=503,
                content={"detail": {
                    "code": "PURCHASE_INITIATION_CLOSED",
                    "message": "New Reading Pass purchases are temporarily paused. Existing reading and listening access remains available.",
                }},
                headers={"Cache-Control": "no-store"},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def create_app():
    # Uvicorn calls this factory from the existing /app backend working directory.
    from server import app
    return PurchaseClosedApp(app)
