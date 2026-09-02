"""Current bounded synchronous streaming-body iterator."""

from __future__ import annotations


CHUNK_SIZE = 1024 * 1024


def streaming_body_iterator(body):
    try:
        while True:
            chunk = body.read(CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
    finally:
        close = getattr(body, "close", None)
        if callable(close):
            close()
