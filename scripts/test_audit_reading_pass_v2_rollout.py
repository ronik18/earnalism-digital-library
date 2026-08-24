from __future__ import annotations

from scripts import audit_reading_pass_v2_rollout as audit


def test_public_audio_beyond_control_fails_closed(monkeypatch):
    monkeypatch.setattr(
        audit,
        "controlled_truth",
        lambda: ({"reader-only": {"title": "Reader only"}}, {}),
    )

    report, rows = audit.build_parity_report(
        [
            {"slug": "reader-only", "reader_enabled": True, "audio_enabled": False},
            {"slug": "unsafe-audio", "reader_enabled": True, "audio_enabled": True},
        ]
    )

    assert report["reader_parity"] is False
    assert report["public_audio_beyond_control"] == ["unsafe-audio"]
    assert report["result"] == "FAIL"
    assert next(row for row in rows if row["slug"] == "unsafe-audio")["reason_codes"] == (
        "PUBLIC_READER_WITHOUT_CONTROLLED_READER_AUTHORIZATION;"
        "PUBLIC_AUDIO_WITHOUT_CONTROLLED_AUDIO_AUTHORIZATION"
    )


def test_matching_reader_and_audio_sets_pass(monkeypatch):
    monkeypatch.setattr(
        audit,
        "controlled_truth",
        lambda: ({"reader": {"title": "Reader"}}, {"reader": {"title": "Reader"}}),
    )

    report, rows = audit.build_parity_report(
        [{"slug": "reader", "reader_enabled": True, "audio_enabled": True}]
    )

    assert report["result"] == "PASS"
    assert rows == [{
        "slug": "reader",
        "public_reader": True,
        "controlled_reader": True,
        "public_audio": True,
        "controlled_audio": True,
        "classification": "PARITY",
        "reason_codes": "",
    }]
