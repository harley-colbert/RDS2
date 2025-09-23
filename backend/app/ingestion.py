from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict


class WorkbookIngestor:
    def __init__(self, workbook_path: Path):
        self.workbook_path = workbook_path

    def extract(self) -> Dict[str, Any]:
        spec: Dict[str, Any] = {"sheets": {}, "named_ranges": {}}
        with zipfile.ZipFile(self.workbook_path) as zf:
            workbook_xml = ET.fromstring(zf.read("xl/workbook.xml"))
            rels_xml = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
            rel_map = {
                rel.attrib["Id"]: rel.attrib["Target"]
                for rel in rels_xml.findall("rel:Relationship", {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"})
            }
            for sheet in workbook_xml.findall("main:sheets/main:sheet", ns):
                name = sheet.attrib["name"]
                rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                target = rel_map[rel_id]
                sheet_xml = ET.fromstring(zf.read(f"xl/{target}"))
                rows = []
                for row in sheet_xml.findall("main:sheetData/main:row", ns):
                    row_data = []
                    for cell in row.findall("main:c", ns):
                        value = ""
                        if cell.attrib.get("t") == "s":
                            shared_index = int(cell.find("main:v", ns).text)
                            value = self._read_shared_string(zf, shared_index)
                        else:
                            v = cell.find("main:v", ns)
                            if v is not None:
                                value = v.text
                        row_data.append({"ref": cell.attrib.get("r"), "value": value})
                    rows.append(row_data)
                spec["sheets"][name] = {"rows": rows}

            defined_names = workbook_xml.find("main:definedNames", ns)
            if defined_names is not None:
                for defined_name in defined_names.findall("main:definedName", ns):
                    text = defined_name.text or ""
                    spec["named_ranges"][defined_name.attrib.get("name")] = text
        return spec

    def _read_shared_string(self, zf: zipfile.ZipFile, index: int) -> str:
        table = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        items = table.findall("main:si", ns)
        if index < len(items):
            text = items[index].find("main:t", ns)
            if text is not None:
                return text.text or ""
        return ""

    def dump(self, output_path: Path) -> Dict[str, Any]:
        spec = self.extract()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(spec, fh, indent=2)
        return spec
