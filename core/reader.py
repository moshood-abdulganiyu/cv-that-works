"""Read PDF and DOCX into plain text with clear, student-friendly errors."""
import io
import math
import re
from pathlib import Path

from .rubric import MAX_FILE_BYTES

WORDS_PER_PAGE = 500  # used only for DOCX, where the real page count is not stored in the file


class CVReadError(Exception):
    """Raised with a message that is safe to show to a student."""
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def _tidy(text):
    text = text.replace("\r", "")
    text = re.sub(r"[\uf0b7\uf0a7\uf076\uf0d8\uf0fc]", "•", text)   # bullet glyphs PDF tools often produce
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def read_document(name, data, allow_txt=False):
    """Return {"text", "pages", "pages_estimated"}. Raises CVReadError."""
    ext = Path(name).suffix.lower()
    if len(data) > MAX_FILE_BYTES:
        raise CVReadError("too_large", f"This file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB. Save a smaller PDF or DOCX and try again.")
    if len(data) == 0:
        raise CVReadError("empty_file", "This file is empty. Please upload your CV again.")

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise CVReadError("locked_pdf", "This PDF is password protected. Save an unlocked copy and upload that.")
            pages = len(reader.pages)
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            links = []
            for p in reader.pages:
                for a in (p.get("/Annots") or []):
                    try:
                        uri = a.get_object().get("/A").get_object().get("/URI")
                        if uri:
                            links.append(str(uri))
                    except Exception:
                        pass
        except CVReadError:
            raise
        except Exception:
            raise CVReadError("corrupt", "We could not open this PDF. Try saving it again from Word or Google Docs as PDF.")
        text = _tidy(text)
        if len(text) < 100:
            raise CVReadError("scanned_pdf", "This PDF looks like a scan or photo, so we cannot read the words. "
                              "Export it as a PDF from Word or Google Docs (File, Download, PDF) and upload that.")
        return {"text": text, "pages": pages, "pages_estimated": False, "links": links}

    if ext == ".docx":
        try:
            import docx
            d = docx.Document(io.BytesIO(data))
        except Exception:
            raise CVReadError("corrupt", "We could not open this DOCX. Save it again as .docx (not .doc) and try again.")
        parts = []
        for p in d.paragraphs:
            t = p.text.strip()
            if not t:
                continue
            style = (p.style.name or "") if p.style is not None else ""
            parts.append(("• " + t) if style.lower().startswith("list") else t)
        for tbl in d.tables:
            for row in tbl.rows:
                cells = []
                for c in row.cells:
                    if c.text.strip() and c.text.strip() not in cells:
                        cells.append(c.text.strip())
                if cells:
                    parts.append(" | ".join(cells))
        text = _tidy("\n".join(parts))
        if len(text) < 100:
            raise CVReadError("empty_file", "We found almost no text in this document. Check you uploaded the right file.")
        pages = max(1, math.ceil(len(text.split()) / WORDS_PER_PAGE))
        links = [str(r.target_ref) for r in d.part.rels.values() if r.reltype.endswith("/hyperlink")]
        return {"text": text, "pages": pages, "pages_estimated": True, "links": links}

    if ext == ".txt" and allow_txt:      # for testing only, never offered to students
        text = _tidy(data.decode("utf-8", errors="ignore"))
        return {"text": text, "pages": max(1, math.ceil(len(text.split()) / WORDS_PER_PAGE)), "pages_estimated": True, "links": []}

    raise CVReadError("unsupported_type", "Please upload a PDF or DOCX file. If your CV is a .doc file, open it in Word and save it as .docx.")
