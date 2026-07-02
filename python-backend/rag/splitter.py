"""Text splitter: chunks markdown documents into searchable segments."""

from __future__ import annotations


def split_markdown(content: str, max_chars: int = 800, overlap: int = 80) -> list[str]:
    """Split markdown content into overlapping chunks at paragraph/heading boundaries.

    Args:
        content: Raw markdown text.
        max_chars: Maximum characters per chunk.
        overlap: Overlap characters between chunks.

    Returns:
        List of text chunks.
    """
    # Split on double newlines (paragraph boundaries) first
    sections = _split_on_headings(content)
    chunks: list[str] = []

    for section in sections:
        if len(section) <= max_chars:
            if section.strip():
                chunks.append(section.strip())
        else:
            # Further split long sections on single newlines or sentence boundaries
            sub_chunks = _split_long_section(section, max_chars, overlap)
            chunks.extend(sub_chunks)

    return chunks


def _split_on_headings(content: str) -> list[str]:
    """Split content at markdown heading boundaries (## or #)."""
    lines = content.split("\n")
    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        # Start new section at headings
        if line.strip().startswith("## ") or (line.strip().startswith("# ") and current):
            if current:
                sections.append("\n".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append("\n".join(current))

    return sections


def _split_long_section(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split a long section into overlapping chunks at sentence/paragraph boundaries."""
    chunks: list[str] = []
    paragraphs = text.split("\n")

    current_chunk: list[str] = []
    current_len = 0

    for para in paragraphs:
        para = para.rstrip()
        para_len = len(para) + 1  # +1 for newline

        if current_len + para_len > max_chars and current_chunk:
            chunks.append("\n".join(current_chunk).strip())
            # Overlap: keep the last paragraph
            if overlap > 0 and len(current_chunk) >= 1:
                last = current_chunk[-1]
                current_chunk = [last] if len(last) < overlap else []
                current_len = len(last) if current_chunk else 0
            else:
                current_chunk = []
                current_len = 0

        if para.strip():
            current_chunk.append(para)
            current_len += para_len

    if current_chunk:
        chunks.append("\n".join(current_chunk).strip())

    return [c for c in chunks if c]
