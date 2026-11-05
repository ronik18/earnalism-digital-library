"""Pure quality-finding classification, separate from mandatory acceptance."""
import re
from typing import Any, Mapping

SHA = re.compile(r"^[a-f0-9]{64}$")


def classify_quality_findings(value: Mapping[str, Any]) -> dict:
    """Retain unconfirmed warnings without inventing a defect or another review.

    Accepted adjudications annotate warnings only. They never erase confirmed
    defects, fill missing mandatory acceptance, alter scores or become approval.
    Existing evidence may be reused; this helper requests no new evidence/run.
    """
    warnings, blockers = [], []
    findings = value.get('quality_findings', [])
    if not isinstance(findings, list):
        return {'warnings': [{'classification': 'UNCERTAINTY_WARNING', 'detail': 'unclassified findings metadata; no defect conclusion'}], 'blockers': []}
    audio = value.get('audio') if isinstance(value.get('audio'), Mapping) else {}
    manuscript = value.get('manuscript') if isinstance(value.get('manuscript'), Mapping) else {}
    binding = {'audio_sha256': audio.get('sha256') or value.get('audio_sha256'),
               'manuscript_sha256': manuscript.get('sha256') or value.get('manuscript_sha256') or value.get('source_sha256')}
    for finding in findings:
        if not isinstance(finding, dict) or not finding.get('id'):
            warnings.append({'classification': 'UNCERTAINTY_WARNING', 'detail': 'unclassified signal; no confirmed defect'})
            continue
        kind = finding.get('classification')
        if kind == 'UNCERTAINTY_WARNING':
            row = dict(finding)
            row['resolution'] = 'UNCONFIRMED_WARNING_NOT_A_DEFECT'
            adjudications = value.get('accepted_adjudications')
            for adjudication in adjudications if isinstance(adjudications, list) else []:
                if (isinstance(adjudication, dict)
                        and adjudication.get('status') == 'ACCEPTED'
                        and adjudication.get('finding_id') == finding['id']
                        and all(isinstance(binding[k], str) and SHA.fullmatch(binding[k])
                                for k in ('audio_sha256', 'manuscript_sha256'))
                        and adjudication.get('audio_sha256') == binding['audio_sha256']
                        and adjudication.get('manuscript_sha256') == binding['manuscript_sha256']
                        and finding.get('span') is not None
                        and adjudication.get('span') == finding['span']
                        and isinstance(adjudication.get('evidence_sha256'), str)
                        and SHA.fullmatch(adjudication['evidence_sha256'])):
                    row['resolution'] = 'EXISTING_SOURCE_BOUND_ADJUDICATION_REFERENCE'
                    row['acceptance_rechecked_by_classifier'] = False
            warnings.append(row)
        elif kind in {'CONFIRMED_MATERIAL_DEFECT', 'MISSING_MANDATORY_ACCEPTANCE'}:
            blockers.append(f"{kind}: {finding['id']}")
        else:
            warnings.append({**finding, 'resolution': 'UNCLASSIFIED_SIGNAL_NOT_CONFIRMED_DEFECT'})
    return {'warnings': warnings, 'blockers': blockers}
