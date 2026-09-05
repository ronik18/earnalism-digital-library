from scripts.reading_pass_segment_matrix import build_matrix


def test_short_controlled_titles_use_one_deterministic_adaptive_policy():
    report = build_matrix([
        "book-d19e96859f",
        "muchiram-gurer-jibanchorit",
        "the-open-window",
        "the-selfish-giant",
    ])
    rows = {row["slug"]: row for row in report["rows"]}
    assert report["result"] == "PASS"
    assert rows["book-d19e96859f"]["selected_target_characters"] == 2000
    assert rows["muchiram-gurer-jibanchorit"]["selected_target_characters"] == 2000
    assert rows["the-open-window"]["selected_target_characters"] == 2000
    assert rows["the-selfish-giant"]["selected_target_characters"] == 2800
    assert all(row["classification"] == "READY_PROTECTED_ADAPTIVE" for row in rows.values())
