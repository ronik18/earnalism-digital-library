from backend.api import schemas


def test_transport_schemas_live_in_the_api_package():
    assert schemas.Book.__module__ == "backend.api.schemas"
    assert schemas.PublicBookOut.__module__ == "backend.api.schemas"
    assert schemas.ReaderHeartbeatIn.__module__ == "backend.api.schemas"
    assert schemas.PaymentVerifyIn.__module__ == "backend.api.schemas"
    assert schemas.ALLOWED_AUDIO_ASSET_KEYS == {
        "mp3",
        "timestamps",
        "vtt",
        "chapters",
        "meta",
        "manifest",
    }
