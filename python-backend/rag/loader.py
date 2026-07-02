"""Document loader: reads markdown files from knowledge_base/ directories."""

from __future__ import annotations

from pathlib import Path

_KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base"


def load_documents(base_dir: Path | None = None) -> list[dict]:
    """Load all .md files from knowledge_base/ subdirectories.

    Returns:
        List of dicts with keys: path (str), content (str), category (str), title (str)
    """
    root = base_dir or _KNOWLEDGE_BASE_DIR
    if not root.is_dir():
        raise FileNotFoundError(f"Knowledge base directory not found: {root}")

    documents: list[dict] = []
    for md_file in sorted(root.rglob("*.md")):
        relative = md_file.relative_to(root)
        category = relative.parts[0] if len(relative.parts) > 1 else "general"
        content = md_file.read_text(encoding="utf-8")
        # Extract title from first markdown heading
        title = md_file.stem
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                title = line.lstrip("# ").strip()
                break

        documents.append({
            "path": str(relative),
            "content": content,
            "category": category,
            "title": title,
        })

    return documents
