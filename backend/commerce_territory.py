"""Purchase admission is separate from literary rights and payment credentials.

International tax/merchant acceptance is not qualified. Fail closed before any
order creation, even if Reader exposure is off or the API is called directly.
Existing payment verification, refunds and webhooks remain available.
"""
try:
    from .release_proxy_auth import ReleaseProxyVerdict, verify_release_proxy_request
except ImportError:
    from release_proxy_auth import ReleaseProxyVerdict, verify_release_proxy_request

COMMERCE_COUNTRIES = frozenset({"IN"})
COMMERCE_ORDER_PATH = "/api/payments/topup"


def commerce_territory_verdict(headers, *, method, path, secret, now=None):
    verdict = verify_release_proxy_request(headers, method=method, path=path, secret=secret, now=now)
    if not verdict.allowed:
        return verdict
    if method.upper() != "POST" or path != COMMERCE_ORDER_PATH:
        return ReleaseProxyVerdict(False, "COMMERCE_SCOPE_INVALID")
    if verdict.country not in COMMERCE_COUNTRIES:
        return ReleaseProxyVerdict(False, "COMMERCE_TERRITORY_DENIED")
    return verdict
