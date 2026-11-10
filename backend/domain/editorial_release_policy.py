"""Editorial review policy only; this grants no publication or spending authority.

Legacy jobs retain their original review contract. New jobs may explicitly select
automated editorial review without manufacturing owner decisions or human scores.
Rights, complete assets, access, accounting and provider limits are independent.
"""
import re

AUTOMATED_EDITORIAL_POLICY = "automated-editorial-2026-11-11"
AUTOMATED_EDITORIAL_CHECKS = (
    "recording_rights", "voice_model_rights", "music_rights", "protected_access", "accounting",
)


def uses_automated_editorial_policy(value):
    policy = value.get("editorial_release_policy")
    if policy is None:
        return False
    if policy != AUTOMATED_EDITORIAL_POLICY:
        raise ValueError("Unsupported editorial release policy")
    return True


def routine_review_not_applicable():
    return {
        "status": "NOT_APPLICABLE",
        "policy": AUTOMATED_EDITORIAL_POLICY,
        "detail": "Routine human editorial review is not required; not a listening PASS or owner decision.",
    }


def automated_receipt_blockers(receipts, binding):
    """Validate admin QA evidence bindings without reading caller-supplied paths.

    The authenticated release operator supplies retained evidence digests; actual
    storage, rights and candidate verification remain in the server's release path.
    """
    if (not binding.get('slug') or any(not isinstance(binding.get(key), str)
            or not re.fullmatch('[a-f0-9]{64}', binding[key])
            for key in ('audio_sha256', 'manuscript_sha256', 'attempt_fingerprint'))):
        return ['Automated QA requires exact server-selected title/source/audio/attempt bindings.']
    receipts = receipts if isinstance(receipts, dict) else {}
    blockers = []
    for name in AUTOMATED_EDITORIAL_CHECKS:
        receipt = receipts.get(name)
        if (not isinstance(receipt, dict)
                or receipt.get('schema') != 'earnalism.automated_release_check.v1'
                or receipt.get('check') != name or receipt.get('status') != 'PASS'
                or receipt.get('binding') != binding
                or not isinstance(receipt.get('evidence_sha256'), str)
                or not re.fullmatch('[a-f0-9]{64}', receipt['evidence_sha256'])):
            blockers.append(f'Candidate-bound automated acceptance is required: {name}.')
    return blockers
