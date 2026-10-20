"""One-shot anonymous alias availability checks; never imports or runs on import."""
import argparse
import datetime as dt
import hashlib
import json
import re
import signal
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, parse_qsl
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOSTS = {"theearnalism.com", "www.theearnalism.com", "earnalism.vercel.app",
         "earnalism-sales-8498s-projects.vercel.app"}
URLS = ["https://www.theearnalism.com/", "https://earnalism.vercel.app/",
        "https://earnalism-sales-8498s-projects.vercel.app/"]


ORIGINAL_CONTRACT = "four-anonymous-v1"
PROPOSED_CONTRACT = "three-public-one-protected-v1"
PROTECTED_URL = "https://earnalism-sales-8498s-projects.vercel.app/"


def validate_protected_redirect(location):
    """Pure validation only. Never follow SSO, authenticate, or retain nonce values."""
    try:
        if (not isinstance(location, str) or len(location) > 2048
                or "#" in location or re.search(r"[\x00-\x20\x7f]", location)):
            raise ValueError("invalid Location syntax")
        p = urlsplit(location)
        pairs = parse_qsl(p.query, keep_blank_values=True, strict_parsing=True,
                          max_num_fields=2)
        values = dict(pairs)
        valid = (p.scheme == "https" and p.netloc == "vercel.com"
                 and p.path == "/sso-api" and not p.fragment
                 and len(pairs) == 2 and set(values) == {"url", "nonce"}
                 and values["url"] == PROTECTED_URL
                 and re.fullmatch(r"[0-9a-f]{64}", values["nonce"]) is not None)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise RuntimeError("protected alias SSO destination contract rejected")
    return {"origin_path": "https://vercel.com/sso-api",
            "return_url": PROTECTED_URL, "nonce_format": "lowercase_hex64",
            "location_sha256": hashlib.sha256(location.encode()).hexdigest(),
            "followed": False}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def allowed(url):
    p = urlsplit(url)
    return (p.scheme == "https" and p.hostname in HOSTS and p.port in (None, 443)
            and not p.username and not p.password and p.path in ("", "/")
            and not p.query and not p.fragment)


@contextmanager
def wall_deadline(seconds):
    """POSIX main-thread timer bounds open, all redirects and body reading together."""
    if seconds <= 0 or not hasattr(signal, "setitimer"):
        raise RuntimeError("Hard wall deadline unavailable/expired; no GET authorized")
    def expired(*_):
        raise TimeoutError("alias hard wall deadline exceeded")
    previous = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def probe(initial, deadline, opener, evidence, clock=time.monotonic,
          contract=ORIGINAL_CONTRACT):
    if contract not in (ORIGINAL_CONTRACT, PROPOSED_CONTRACT):
        raise RuntimeError("unknown acceptance contract; no GET authorized")
    protected_role = contract == PROPOSED_CONTRACT and initial == PROTECTED_URL
    url = initial
    row = {"initial_url": initial, "chain": [], "result": "FAIL"}
    evidence["probes"].append(row)
    for hop in range(3):
        if clock() >= deadline or not allowed(url) or evidence["requests"] >= 9:
            raise RuntimeError("deadline, host or request budget rejected before GET")
        # Debit before sending, including requests which fail or time out.
        evidence["requests"] += 1
        request = Request(url, headers={"User-Agent": "EarnalismAliasCanary/1.0",
                                       "Accept": "text/html"}, method="GET")
        try:
            response = opener.open(request, timeout=min(15, deadline-clock()))
        except HTTPError as error:
            response = error
        with response:
            status = response.code
            step = {"url": url, "status": status}
            row["chain"].append(step)
            if protected_role:
                if status != 302 or hop != 0:
                    raise RuntimeError("protected alias must return direct HTTP302 SSO")
                step["protected_destination"] = validate_protected_redirect(
                    response.headers.get("Location", ""))
                row.update(result="PASS_PROTECTED_ALIAS", anonymously_available=False,
                           role="provider-protected alias; not public application")
                return
            if status in (301, 302, 303, 307, 308):
                try:
                    target = urljoin(url, response.headers.get("Location", ""))
                    parsed_target = urlsplit(target)
                    target_allowed = allowed(target)
                except ValueError:
                    step["redirect_target"] = {"malformed": True}
                    raise RuntimeError("malformed redirect target rejected") from None
                # Preserve rejected-target evidence before fail-closed validation.
                # Never retain arbitrary query, userinfo, fragment or path values.
                step["redirect_target"] = {
                    "scheme": parsed_target.scheme,
                    "hostname": parsed_target.hostname,
                    "root_path": parsed_target.path in ("", "/"),
                    "query_present": bool(parsed_target.query),
                    "fragment_present": bool(parsed_target.fragment),
                    "userinfo_present": bool(parsed_target.username or parsed_target.password),
                    "sha256": hashlib.sha256(target.encode()).hexdigest(),
                }
                if hop == 2 or not response.headers.get("Location") or not target_allowed:
                    raise RuntimeError("redirect limit or approved HTTPS host rejected")
                step["location"] = target
                url = target
                continue
            if status != 200 or "text/html" not in response.headers.get("Content-Type", "").lower():
                raise RuntimeError("root response not readable HTTP200 HTML")
            body = response.read(1024*1024+1)
            if clock() >= deadline or not body or len(body) > 1024*1024:
                raise RuntimeError("body/deadline limit rejected")
            html = body.decode("utf-8", errors="replace")
            if (not re.search(r'id\s*=\s*[\"\']root[\"\']', html, re.I)
                    or not re.search(r'<script\b[^>]*\bsrc\s*=', html, re.I)
                    or "earnalism" not in html.lower()
                    or re.search(r'VERCEL_AUTHENTICATION|DEPLOYMENT_NOT_FOUND|DEPLOYMENT_DISABLED|Authentication Required', html, re.I)):
                raise RuntimeError("application HTML markers missing or provider protection/error")
            row.update(result="PASS", body_bytes=len(body), body_sha256=hashlib.sha256(body).hexdigest())
            return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--ready-at", required=True, help="Verified deployment READY timestamp, aware ISO8601")
    parser.add_argument("--output", required=True)
    parser.add_argument("--contract", choices=(ORIGINAL_CONTRACT, PROPOSED_CONTRACT),
                        default=ORIGINAL_CONTRACT,
                        help="Proposed profile requires separate explicit owner approval")
    args = parser.parse_args()
    if not re.fullmatch(r"dpl_[A-Za-z0-9]+", args.deployment):
        raise SystemExit("Invalid actual deployment identity")
    ready = dt.datetime.fromisoformat(args.ready_at.replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    if ready.tzinfo is None or not 0 <= (now-ready).total_seconds() < 900:
        raise SystemExit("READY timestamp outside fifteen-minute observation window")
    deadline = time.monotonic() + 900-(now-ready).total_seconds()
    path = Path(args.output)
    # A persistent intent prevents a second invocation with the same output path.
    with path.open("x") as handle:
        handle.write(json.dumps({"state": "STARTED_NO_RETRY", "deployment": args.deployment}))
    evidence = {"deployment": args.deployment, "ready_at": args.ready_at,
                "started_at": now.isoformat(), "requests": 0, "probes": [],
                "result": "FAIL", "contract": args.contract,
                "scope": "Public availability and/or protected-alias behavior per explicit contract; exact provider binding verified separately"}
    try:
        opener = build_opener(NoRedirect())
        for url in URLS:
            with wall_deadline(min(15, deadline-time.monotonic())):
                probe(url, deadline, opener, evidence, contract=args.contract)
        evidence["result"] = ("PASS" if args.contract == ORIGINAL_CONTRACT
                              else "PASS_PROPOSED_CONTRACT")
    except Exception as error:
        evidence["error"] = type(error).__name__ + ": " + str(error)
    finally:
        evidence["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        path.write_text(json.dumps(evidence, indent=2)+"\n")
    print(json.dumps({"result": evidence["result"], "requests": evidence["requests"], "output": str(path)}))
    return 0 if evidence["result"] in ("PASS", "PASS_PROPOSED_CONTRACT") else 1


if __name__ == "__main__":
    raise SystemExit(main())
