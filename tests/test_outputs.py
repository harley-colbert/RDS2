from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.excel import CostingWorkbookWriter
from backend.app.services import export_summary_for_workbook
from backend.app.word import ProposalWriter


@pytest.fixture(scope="module")
def tmp_output(tmp_path_factory):
    return tmp_path_factory.mktemp("outputs")


def test_excel_filename(tmp_output):
    export = export_summary_for_workbook({
        "base_total": 1000.0,
        "J38": 10.0,
        "J39": 20.0,
        "J40": 30.0,
        "J32": 40.0,
        "J33": 50.0,
        "J18": 60.0,
        "J19": 70.0,
        "J20": 80.0,
        "J45": 90.0,
        "J46": 100.0,
        "J47": 110.0,
        "margin": 0.2,
    })
    writer = CostingWorkbookWriter(allow_xlsb=False)
    path = writer.write(export, tmp_output / "01 - Q#123 - Costing")
    assert path.name == "01 - Q#123 - Costing.xlsx"
    assert path.exists()


def test_word_generation(tmp_output, monkeypatch):
    template = tmp_output / "template.docx"
    # create minimal docx template
    from docx import Document

    doc = Document()
    doc.add_paragraph("Proposal [QuoteNum] for [Customer]")
    doc.save(template)

    writer = ProposalWriter(template)
    result = writer.write({"QuoteNum": "Q123", "Customer": "Acme"}, tmp_output / "Alliance Automation Proposal #Q123 - Dismantling System")
    assert result["docx"].name.endswith(".docx")
    assert result["docx"].exists()
