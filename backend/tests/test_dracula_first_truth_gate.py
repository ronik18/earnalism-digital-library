from __future__ import annotations

from backend import server


def test_controlled_public_book_query_requires_dracula_tier_a_approved():
    query = server._controlled_public_book_query()

    assert query["slug"] == {"$in": ["dracula"]}
    assert query["is_published"] is True
    assert query["rights_metadata.rights_tier"] == "A"
    assert query["rights_metadata.verification_status"] == "approved"
    assert {"rights_metadata.blocked_reason": ""} in query["$or"]


def test_controlled_public_book_query_preserves_search_or_with_rights_blocker():
    query = server._controlled_public_book_query({
        "$or": [{"title": {"$regex": "Dracula", "$options": "i"}}],
    })

    assert "$or" not in query
    assert query["$and"][0]["$or"][0]["rights_metadata.blocked_reason"] == {"$exists": False}
    assert query["$and"][1]["$or"][0]["title"] == {"$regex": "Dracula", "$options": "i"}


def test_only_dracula_is_controlled_public_slug():
    assert server._is_controlled_public_slug("dracula") is True
    assert server._is_controlled_public_slug("frankenstein") is False
    assert server._is_controlled_public_slug("sherlock-holmes") is False
