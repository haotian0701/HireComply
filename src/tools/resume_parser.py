"""Resume Parser Tool.

Extracts text content from PDF and DOCX resume files.
Used as a preprocessing step before the screening node.
"""

from __future__ import annotations

from pathlib import Path


def parse_resume(file_path: str | Path) -> dict:
    """Extract text and metadata from a resume file.

    Supports: .pdf, .docx, .txt

    Returns:
        dict with keys: text, file_name, file_type, page_count
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(path)
    elif suffix == ".docx":
        return _parse_docx(path)
    elif suffix == ".txt":
        return _parse_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use .pdf, .docx, or .txt")


def _parse_pdf(path: Path) -> dict:
    """Extract text from PDF using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]

    return {
        "text": "\n\n".join(pages).strip(),
        "file_name": path.name,
        "file_type": "pdf",
        "page_count": len(reader.pages),
    }


def _parse_docx(path: Path) -> dict:
    """Extract text from DOCX using python-docx."""
    from docx import Document

    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

    return {
        "text": "\n".join(paragraphs).strip(),
        "file_name": path.name,
        "file_type": "docx",
        "page_count": 1,  # DOCX doesn't have a clear page concept
    }


def _parse_txt(path: Path) -> dict:
    """Read plain text file."""
    text = path.read_text(encoding="utf-8")

    return {
        "text": text.strip(),
        "file_name": path.name,
        "file_type": "txt",
        "page_count": 1,
    }


def parse_resumes_from_dir(dir_path: str | Path) -> list[dict]:
    """Parse all resume files in a directory.

    Returns a list of dicts, each with candidate_id, name, text, metadata.
    """
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    resumes = []
    supported = {".pdf", ".docx", ".txt"}

    for i, file_path in enumerate(sorted(dir_path.iterdir())):
        if file_path.suffix.lower() in supported:
            parsed = parse_resume(file_path)
            resumes.append({
                "candidate_id": f"c{i+1:03d}",
                "name": file_path.stem.replace("_", " ").title(),
                "text": parsed["text"],
                "metadata": {
                    "file_name": parsed["file_name"],
                    "file_type": parsed["file_type"],
                    "page_count": parsed["page_count"],
                },
            })

    return resumes
