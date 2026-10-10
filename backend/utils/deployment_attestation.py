"""Safe provider provenance only; never infer a revision from release inputs."""
import os
import re


def deployment_attestation(environ=None):
    source = os.environ if environ is None else environ
    fields = {
        "git_sha": ("RAILWAY_GIT_COMMIT_SHA", r"[0-9a-f]{40}"),
        "deployment_id": ("RAILWAY_DEPLOYMENT_ID", r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"),
        "project_id": ("RAILWAY_PROJECT_ID", r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"),
        "service_id": ("RAILWAY_SERVICE_ID", r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"),
        "environment_id": ("RAILWAY_ENVIRONMENT_ID", r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"),
    }
    result = {}
    for field, (variable, pattern) in fields.items():
        value = source.get(variable)
        result[field] = value if isinstance(value, str) and re.fullmatch(pattern, value) else None
    result["status"] = "AVAILABLE" if all(result.values()) else "UNAVAILABLE"
    return result
