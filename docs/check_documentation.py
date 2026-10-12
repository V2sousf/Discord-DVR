"""Check source documentation links without networking or inspecting private inputs."""
from pathlib import Path
import json
import re

root = Path(__file__).resolve().parents[1]
documents = [root / name for name in (
    "README.md", "INSTALLATION.md", "CONTRIBUTING.md", "CHANGELOG.md",
    "SECURITY.md", "THIRD_PARTY_NOTICES.md",
)] + sorted((root / "docs").glob("*.md"))
missing = []
for document in documents:
    text = document.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if target.startswith(("https:", "http:", "#", "mailto:")):
            continue
        path = target.split("#", 1)[0]
        if path and not (document.parent / path).exists():
            missing.append({"file": document.relative_to(root).as_posix(), "target": target})

result = {"passed": not missing, "documents_checked": len(documents), "missing_links": missing}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["passed"] else 1)
