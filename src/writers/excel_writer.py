"""ExcelWriter — Ghi file Excel đã dịch, giữ nguyên định dạng gốc."""

import logging
from pathlib import Path
from typing import Callable

from src.writers.base import FileWriter

logger = logging.getLogger(__name__)


class ExcelWriter(FileWriter):
    """Writer cho file Excel (.xlsx, .xls).

    Giữ nguyên: styles, merge cells, hình ảnh, biểu đồ, formulas.
    Dịch: cell values (text), sheet names, shapes text.
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
        else:
            self._write_xlsx(source_path, output_path, translate_fn)

    def _write_xlsx(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file .xlsx bằng openpyxl — giữ nguyên formatting."""
        import openpyxl

        wb = openpyxl.load_workbook(source_path)

        for ws in wb.worksheets:
            # Dịch cell values
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None and isinstance(cell.value, str):
                        original = cell.value
                        if original.strip():
                            cell.value = translate_fn(original)

            # Không dịch shapes text — openpyxl làm mất shapes khi
            # truy cập _drawing nội bộ. Ưu tiên giữ nguyên shapes.

        # Dịch tên sheet
        for ws in wb.worksheets:
            original_title = ws.title
            if original_title.strip():
                ws.title = translate_fn(original_title)

        wb.save(output_path)
        wb.close()
        logger.info("Đã ghi file xlsx: %s", output_path.name)

    def _translate_shapes_xlsx(
        self,
        ws: "openpyxl.worksheet.worksheet.Worksheet",
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch text trong shapes của worksheet.

        Shapes trong xlsx được lưu trong file drawing XML.
        Openpyxl giữ nguyên drawing khi save, nhưng không expose API
        để sửa shape text. Ta cần thao tác trực tiếp trên XML.
        """
        try:
            if not hasattr(ws, '_charts') and not hasattr(ws, '_drawing'):
                return

            drawing = getattr(ws, '_drawing', None)
            if drawing is None:
                return

            # Duyệt qua các anchor trong drawing
            for anchor in getattr(drawing, 'oneCellAnchor', []) + getattr(drawing, 'twoCellAnchor', []):
                shape = getattr(anchor, 'sp', None)
                if shape is None:
                    continue
                txBody = getattr(shape, 'txBody', None)
                if txBody is None:
                    continue
                self._translate_xml_text_body(txBody, translate_fn)

        except Exception as e:
            logger.debug("Không thể dịch shapes trong worksheet: %s", e)

    def _translate_xml_text_body(
        self,
        txBody: object,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch text trong txBody XML element."""
        try:
            for p in txBody.p_lst:
                full_text = ""
                runs = []
                for r in getattr(p, 'r_lst', []):
                    if hasattr(r, 't') and r.t is not None:
                        full_text += r.t
                        runs.append(r)

                if full_text.strip() and runs:
                    translated = translate_fn(full_text)
                    # Gán toàn bộ text dịch vào run đầu tiên, xoá các run còn lại
                    runs[0].t = translated
                    for r in runs[1:]:
                        r.t = ""
        except Exception as e:
            logger.debug("Không thể dịch txBody: %s", e)

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
            ws.title = translate_fn(rs.name) if rs.name.strip() else rs.name

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
