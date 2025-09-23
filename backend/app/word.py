from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from docx import Document

try:  # pragma: no cover - optional dependency
    from docx2pdf import convert as docx2pdf_convert
except Exception:  # noqa: BLE001
    docx2pdf_convert = None

logger = logging.getLogger(__name__)


class ProposalWriter:
    def __init__(self, template_path: Path):
        self.template_path = template_path

    def write(self, bookmark_map: Dict[str, str], output_path: Path) -> Dict[str, Path]:
        document = Document(self.template_path)
        for paragraph in document.paragraphs:
            for bookmark, value in bookmark_map.items():
                if bookmark in paragraph.text:
                    paragraph.text = paragraph.text.replace(f"[{bookmark}]", value)
        docx_path = output_path.with_suffix(".docx")
        document.save(docx_path)
        pdf_path = docx_path.with_suffix(".pdf")
        if docx2pdf_convert:
            try:
                docx2pdf_convert(str(docx_path), str(pdf_path))
            except Exception as exc:  # noqa: BLE001
                logger.warning("docx2pdf conversion failed: %s", exc)
                pdf_path = None
        else:
            pdf_path = None
        return {"docx": docx_path, "pdf": pdf_path}
