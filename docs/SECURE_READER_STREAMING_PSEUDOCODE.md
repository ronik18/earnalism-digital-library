# Secure Reader Encrypted Streaming Pseudocode

This is the production design for PDF/EPUB streaming. The current web reader stores normalized chapter HTML, while future file-based readers should use this pattern so original ebook files are never exposed by public URL.

## Backend Flow

```python
from base64 import b64encode
from secrets import token_urlsafe
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

CHUNK_SIZE = 64 * 1024

@api.post("/secure-reader/sessions")
async def start_secure_session(book_slug: str, user=Depends(require_user)):
    # 1. Verify user has reading entitlement and wallet balance.
    # 2. Resolve the private object key from the database, never from user input.
    # 3. Create a short-lived server-side session record.
    # 4. Store only a KMS-wrapped content key, not raw secrets in logs.
    session_id = token_urlsafe(32)
    content_key = get_random_bytes(32)  # AES-256
    await db.secure_reader_sessions.insert_one({
        "id": session_id,
        "user_id": user["id"],
        "book_slug": book_slug,
        "content_key_wrapped": kms_wrap(content_key),
        "expires_at": utc_now_plus(minutes=20),
        "created_at": now_iso(),
    })
    return {"session_id": session_id, "chunk_size": CHUNK_SIZE}


@api.get("/secure-reader/sessions/{session_id}/chunks/{index}")
async def stream_encrypted_chunk(session_id: str, index: int, user=Depends(require_user)):
    # 1. Verify session belongs to user and is unexpired.
    # 2. Read a fixed-size byte range from private storage.
    # 3. Encrypt that range with AES-256-GCM using a fresh nonce per chunk.
    # 4. Return base64 ciphertext only; never return object paths.
    session = await load_valid_session(session_id, user["id"])
    raw = private_storage.read_range(session["object_key"], index * CHUNK_SIZE, CHUNK_SIZE)
    key = kms_unwrap(session["content_key_wrapped"])
    nonce = get_random_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(session_id.encode("utf-8"))
    ciphertext, tag = cipher.encrypt_and_digest(raw)
    return {
        "index": index,
        "nonce": b64encode(nonce).decode(),
        "ciphertext": b64encode(ciphertext).decode(),
        "tag": b64encode(tag).decode(),
        "is_last": len(raw) < CHUNK_SIZE,
    }


@api.delete("/secure-reader/sessions/{session_id}")
async def end_secure_session(session_id: str, user=Depends(require_user)):
    # Destroy server-side session state; browser cleanup clears decrypted buffers.
    await db.secure_reader_sessions.update_one(
        {"id": session_id, "user_id": user["id"]},
        {"$set": {"ended_at": now_iso(), "status": "ended"}},
    )
    return {"ok": True}
```

## Frontend Flow

```javascript
const buffers = new Map();

async function loadChunk(sessionId, index, aesKey) {
  const res = await fetch(`/api/secure-reader/sessions/${sessionId}/chunks/${index}`);
  const chunk = await res.json();
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: base64ToBytes(chunk.nonce), additionalData: new TextEncoder().encode(sessionId) },
    aesKey,
    concat(base64ToBytes(chunk.ciphertext), base64ToBytes(chunk.tag)),
  );
  buffers.set(index, plaintext);
  renderPageFromBuffer(plaintext);
}

window.addEventListener("beforeunload", () => {
  buffers.forEach((buffer) => new Uint8Array(buffer).fill(0));
  buffers.clear();
  navigator.sendBeacon(`/api/secure-reader/sessions/${sessionId}/end`);
});
```

## Compliance Notes

- Log only session IDs and token fingerprints, never bearer tokens or raw ebook bytes.
- Store ebooks in private storage and resolve object keys server-side.
- Use short-lived sessions and rotate chunk nonces.
- Watermark every rendered page with session ID, timestamp, and partial reader identifier.
- This deters casual copying and supports leak tracing, but OS-level screenshots cannot be fully prevented in a browser.
