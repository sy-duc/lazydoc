"""ExcelWriter — Ghi file Excel đã dịch, giữ nguyên định dạng gốc."""

import logging
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree as ET

from src.writers.base import FileWriter

logger = logging.getLogger(__name__)

# Namespaces dùng trong xlsx XML
_NS = {
    "sst": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


class ExcelWriter(FileWriter):
    """Writer cho file Excel (.xlsx, .xls).

    Chiến lược 2 nhánh:
    - File có shapes/images: thao tác tầng ZIP/XML để giữ nguyên 100%.
    - File đơn giản: dùng openpyxl (nhanh hơn, dễ xử lý formatting).
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".xlsx", ".xls"]

    def write_translated(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file Excel giữ nguyên định dạng.

        Args:
            source_path: Đường dẫn file gốc.
            output_path: Đường dẫn file đầu ra.
            translate_fn: Hàm dịch.
        """
        ext = source_path.suffix.lower()
        if ext == ".xls":
            self._write_xls(source_path, output_path, translate_fn)
        elif self._has_shapes_or_media(source_path):
            self._write_xlsx_zip(source_path, output_path, translate_fn)
        else:
            self._write_xlsx_openpyxl(source_path, output_path, translate_fn)

    # --- Detect ---

    @staticmethod
    def _has_shapes_or_media(source_path: Path) -> bool:
        """Kiểm tra file xlsx có chứa shapes, images, hoặc drawings không."""
        try:
            with zipfile.ZipFile(source_path, "r") as zf:
                for name in zf.namelist():
                    if name.startswith("xl/drawings/") or name.startswith("xl/media/"):
                        return True
        except zipfile.BadZipFile:
            pass
        return False

    # --- Nhánh ZIP/XML (giữ nguyên shapes) ---

    def _write_xlsx_zip(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file .xlsx bằng thao tác ZIP/XML — giữ nguyên shapes/images.

        Chỉ sửa xl/sharedStrings.xml (text cells) và xl/workbook.xml (tên sheet),
        giữ nguyên mọi file khác trong zip.
        """
        shutil.copy2(source_path, output_path)

        with zipfile.ZipFile(source_path, "r") as zf_in:
            # Đọc và dịch sharedStrings
            modified_files: dict[str, bytes] = {}

            if "xl/sharedStrings.xml" in zf_in.namelist():
                sst_xml = zf_in.read("xl/sharedStrings.xml")
                translated_sst = self._translate_shared_strings(sst_xml, translate_fn)
                modified_files["xl/sharedStrings.xml"] = translated_sst

            # Dịch tên sheet trong workbook.xml
            if "xl/workbook.xml" in zf_in.namelist():
                wb_xml = zf_in.read("xl/workbook.xml")
                translated_wb = self._translate_workbook_sheet_names(wb_xml, translate_fn)
                modified_files["xl/workbook.xml"] = translated_wb

            # Dịch inline strings trong từng sheet
            for name in zf_in.namelist():
                if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                    sheet_xml = zf_in.read(name)
                    translated_sheet = self._translate_inline_strings(sheet_xml, translate_fn)
                    if translated_sheet is not None:
                        modified_files[name] = translated_sheet

        # Ghi lại file zip với các file đã sửa
        self._replace_in_zip(output_path, modified_files)
        logger.info("Đã ghi file xlsx (ZIP mode): %s", output_path.name)

    def _translate_shared_strings(
        self, xml_data: bytes, translate_fn: Callable[[str], str]
    ) -> bytes:
        """Dịch text trong xl/sharedStrings.xml."""
        tree = ET.ElementTree(ET.fromstring(xml_data))
        root = tree.getroot()
        ns = _NS["sst"]

        for si in root.findall(f"{{{ns}}}si"):
            # Trường hợp 1: <si><t>text</t></si>
            t_elem = si.find(f"{{{ns}}}t")
            if t_elem is not None and t_elem.text and t_elem.text.strip():
                t_elem.text = translate_fn(t_elem.text)
                continue

            # Trường hợp 2: <si><r><t>text</t></r>...</si> (rich text)
            runs = si.findall(f".//{{{ns}}}r")
            if runs:
                full_text = ""
                t_elements = []
                for r in runs:
                    t = r.find(f"{{{ns}}}t")
                    if t is not None and t.text:
                        full_text += t.text
                        t_elements.append(t)

                if full_text.strip() and t_elements:
                    translated = translate_fn(full_text)
                    t_elements[0].text = translated
                    for t in t_elements[1:]:
                        t.text = ""

        return ET.tostring(root, xml_declaration=True, encoding="UTF-8")

    def _translate_workbook_sheet_names(
        self, xml_data: bytes, translate_fn: Callable[[str], str]
    ) -> bytes:
        """Dịch tên sheet trong xl/workbook.xml."""
        tree = ET.ElementTree(ET.fromstring(xml_data))
        root = tree.getroot()
        ns = _NS["sst"]

        for sheet in root.findall(f".//{{{ns}}}sheet"):
            name = sheet.get("name", "")
            if name.strip():
                translated_name = translate_fn(name)
                # Tên sheet tối đa 31 ký tự, không chứa ký tự đặc biệt
                translated_name = self._sanitize_sheet_name(translated_name)
                sheet.set("name", translated_name)

        return ET.tostring(root, xml_declaration=True, encoding="UTF-8")

    def _translate_inline_strings(
        self, xml_data: bytes, translate_fn: Callable[[str], str]
    ) -> bytes | None:
        """Dịch inline strings trong sheet XML (cell có type='inlineStr')."""
        tree = ET.ElementTree(ET.fromstring(xml_data))
        root = tree.getroot()
        ns = _NS["sst"]

        has_changes = False
        for is_elem in root.findall(f".//{{{ns}}}is"):
            t_elem = is_elem.find(f"{{{ns}}}t")
            if t_elem is not None and t_elem.text and t_elem.text.strip():
                t_elem.text = translate_fn(t_elem.text)
                has_changes = True

        if not has_changes:
            return None

        return ET.tostring(root, xml_declaration=True, encoding="UTF-8")

    @staticmethod
    def _replace_in_zip(zip_path: Path, modified_files: dict[str, bytes]) -> None:
        """Thay thế các file trong zip mà không ảnh hưởng file khác."""
        if not modified_files:
            return

        temp_path = zip_path.with_suffix(".tmp")
        with zipfile.ZipFile(zip_path, "r") as zf_in, \
             zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf_out:
            for item in zf_in.infolist():
                if item.filename in modified_files:
                    zf_out.writestr(item, modified_files[item.filename])
                else:
                    zf_out.writestr(item, zf_in.read(item.filename))

        temp_path.replace(zip_path)

    @staticmethod
    def _sanitize_sheet_name(name: str) -> str:
        """Chuẩn hóa tên sheet theo quy tắc Excel."""
        import re
        # Loại bỏ ký tự không hợp lệ: [ ] * ? / \
        name = re.sub(r'[\[\]*?/\\]', '', name)
        # Tối đa 31 ký tự
        name = name[:31].strip()
        return name if name else "Sheet"

    # --- Nhánh openpyxl (file đơn giản) ---

    def _write_xlsx_openpyxl(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file .xlsx bằng openpyxl — cho file không có shapes."""
        import openpyxl

        wb = openpyxl.load_workbook(source_path)

        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None and isinstance(cell.value, str):
                        original = cell.value
                        if original.strip():
                            cell.value = translate_fn(original)

        # Dịch tên sheet
        for ws in wb.worksheets:
            original_title = ws.title
            if original_title.strip():
                translated_title = self._sanitize_sheet_name(translate_fn(original_title))
                ws.title = translated_title

        wb.save(output_path)
        wb.close()
        logger.info("Đã ghi file xlsx (openpyxl mode): %s", output_path.name)

    # --- Nhánh xls (legacy) ---

    def _write_xls(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file .xls — chuyển sang .xlsx vì xlrd chỉ đọc.

        File .xls được đọc bằng xlrd, ghi ra .xlsx bằng openpyxl.
        Giữ được dữ liệu nhưng có thể mất một số formatting phức tạp.
        """
        import xlrd
        import openpyxl

        rb = xlrd.open_workbook(source_path)
        wb = openpyxl.Workbook()

        for sheet_idx in range(rb.nsheets):
            rs = rb.sheet_by_index(sheet_idx)

            if sheet_idx == 0:
                ws = wb.active
            else:
                ws = wb.create_sheet()

            # Dịch tên sheet
            if rs.name.strip():
                ws.title = self._sanitize_sheet_name(translate_fn(rs.name))
            else:
                ws.title = rs.name

            # Dịch cell values
            for row_idx in range(rs.nrows):
                for col_idx in range(rs.ncols):
                    value = rs.cell_value(row_idx, col_idx)
                    if isinstance(value, str) and value.strip():
                        ws.cell(row=row_idx + 1, column=col_idx + 1, value=translate_fn(value))
                    elif value != "":
                        ws.cell(row=row_idx + 1, column=col_idx + 1, value=value)

        # Đổi extension sang .xlsx
        actual_output = output_path.with_suffix(".xlsx")
        wb.save(actual_output)
        wb.close()
        logger.info("Đã ghi file xls → xlsx: %s", actual_output.name)
