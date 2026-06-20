from __future__ import annotations

from backend import server


def test_controlled_public_book_query_fetches_only_dracula_candidate():
    query = server._controlled_public_book_query()

    assert query["slug"] == {"$in": ["dracula"]}
    assert query["is_published"] is True
    assert "rights_metadata.rights_tier" not in query
    assert "rights_metadata.verification_status" not in query


def test_controlled_public_book_query_preserves_search_or_for_candidate_fetch():
    query = server._controlled_public_book_query({
        "$or": [{"title": {"$regex": "Dracula", "$options": "i"}}],
    })

    assert query["slug"] == {"$in": ["dracula"]}
    assert query["$or"][0]["title"] == {"$regex": "Dracula", "$options": "i"}


def test_only_dracula_is_controlled_public_slug():
    assert server._is_controlled_public_slug("dracula") is True
    assert server._is_controlled_public_slug("frankenstein") is False
    assert server._is_controlled_public_slug("sherlock-holmes") is False
