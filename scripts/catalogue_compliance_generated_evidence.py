"""Preserve generated campaign reports outside the publication diff."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile


CANONICAL = "internal/earnalism_intelligence/full_catalogue_processing_20260930"
WORKER = CANONICAL + "_worker"


def preserve_generated_evidence(root: Path) -> Path:
    root = root.resolve()
    sources = []
    for relative in [CANONICAL, WORKER]:
        source = root / relative
        if not source.exists():
            continue
        if source.is_symlink() or not source.is_dir():
            raise ValueError("generated evidence must be a physical directory")
        tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "--", relative], text=True)
        if relative == WORKER and tracked:
            raise ValueError("worker output contains tracked source; preserve it for review")
        for path in source.rglob("*"):
            if path.is_symlink():
                raise ValueError("generated evidence contains a symlink")
            if path.is_file():
                if path.suffix != ".json":
                    raise ValueError("generated evidence contains a non-report file")
                json.loads(path.read_text())
        sources.append((relative, source, bool(tracked)))
    # Retain the exact proposed package diff even when later validation fails.
    proposal = subprocess.check_output(["git", "-C", str(root), "diff", "--binary", "HEAD", "--",
                                       "data/controlled_publications", "backend/data/controlled_publications"])
    archive = Path(tempfile.mkdtemp(prefix="catalogue-generated-evidence-"))
    (archive / "held-title-proposal.diff").write_bytes(proposal)
    for relative, source, tracked in sources:
        shutil.move(str(source), str(archive / source.name))
        if tracked:
            subprocess.run(["git", "-C", str(root), "restore", "--source=HEAD", "--worktree", "--staged", "--", relative], check=True)
    return archive


if __name__ == "__main__":
    print(preserve_generated_evidence(Path.cwd()))
