from backend.publication_workflow_schema import (
    SCHEMA_VERSION,
    migrate_book_dry_run,
    normalize_publication_workflow,
    validate_publication_workflow,
)
from backend.publishing_workflow import evaluate_workflow, workflow_signals_from_book
from backend.publication_workflow_adapter import canonical_update, mongo_canonical_update


def legacy_book(**overrides):
    book = {
        "slug": "legacy-book",
        "title": "Legacy Book",
        "rights_metadata": {"rights_tier": "A", "verification_status": "APPROVED"},
        "demand": {"demand_score": 90, "action_status": "READY_FOR_GENERATION"},
        "ingestion_status": "CLEANED",
        "edition_generation_status": "QA_PASSED",
        "visual_status": "QA_PASSED",
        "audio_status": "AUDIO_NOT_REQUIRED",
        "qa": {"qa_status": "QA_PASSED", "warnings": []},
        "cost": {"used": 0, "budget": 10},
    }
    book.update(overrides)
    return book


def test_legacy_only_record_normalizes_and_remains_publishable():
    result = normalize_publication_workflow(legacy_book())
    assert result.workflow["schema_version"] == SCHEMA_VERSION
    assert result.workflow["rights"]["tier"] == "A"
    assert result.workflow["ingestion"]["status"] == "CLEANED"
    assert evaluate_workflow(workflow_signals_from_book(legacy_book())).publish_readiness == "BLOCKED"


def test_canonical_only_record_is_consumed_by_gates():
    book = legacy_book()
    book.pop("rights_metadata")
    book.pop("demand")
    for key in ("ingestion_status", "edition_generation_status", "visual_status", "audio_status", "qa", "cost"):
        book.pop(key, None)
    book["publication_workflow"] = normalize_publication_workflow(legacy_book()).workflow
    assert evaluate_workflow(workflow_signals_from_book(book)).publish_readiness == "READY"


def test_stronger_approved_artifact_wins_and_conflict_is_reported():
    result = normalize_publication_workflow(
        legacy_book(rights_metadata={"rights_tier": "B", "verification_status": "APPROVED"}),
        approved_artifact={"rights": {"tier": "A", "verification_status": "APPROVED"}},
    )
    assert result.workflow["rights"]["tier"] == "A"
    assert any(item["field"] == "rights.tier" for item in result.conflicts)


def test_published_state_does_not_infer_rights_or_audio_approval():
    book = legacy_book(is_published=True, rights_metadata={"rights_tier": "", "verification_status": ""}, audio_status="")
    canonical = normalize_publication_workflow(book).workflow
    canonical["publication"].update({"state": "PUBLISHED", "reader_exposed": True, "audio_exposed": False})
    book["publication_workflow"] = canonical
    signals = workflow_signals_from_book(book)
    assert signals.rights_tier == ""
    assert signals.audio_status == ""
    assert signals.is_published is True


def test_invalid_schema_version_is_rejected():
    workflow = normalize_publication_workflow(legacy_book()).workflow
    workflow["schema_version"] = 999
    assert validate_publication_workflow(workflow) == ["publication_workflow schema_version must be 2"]


def test_dry_run_is_idempotent_for_same_record():
    book = legacy_book()
    first = migrate_book_dry_run(book)
    book["publication_workflow"] = first["publication_workflow"]
    second = migrate_book_dry_run(book)
    assert second["publication_workflow"] == first["publication_workflow"]
    assert second["changed"] is False


def test_canonical_write_adapter_preserves_legacy_fields_and_is_idempotent():
    book = legacy_book()
    workflow = canonical_update(book)
    update = mongo_canonical_update({**book, "publication_workflow": workflow})
    assert update["$set"]["publication_workflow"]["schema_version"] == SCHEMA_VERSION
    assert "rights_metadata" not in update["$set"]
    assert update["$addToSet"]["publication_workflow_audit"]["event_id"]
