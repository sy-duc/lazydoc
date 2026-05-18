"""XML Shapes — Trích xuất text và hình ảnh từ shapes trong file Office (ZIP/XML).

File .xlsx, .docx, .pptx đều là file ZIP chứa XML.
Shapes text nằm trong các tag <a:t> bên trong drawing XML.
Module này cung cấp hàm tiện ích chung cho việc parse XML lấy shapes text.
"""

import logging
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from src.core.logging_config import safe_file_label, sanitize_error

logger = logging.getLogger(__name__)

# Namespace XML thường dùng trong file Office
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def extract_text_from_element(element: ET.Element) -> str:
    """Trích xuất tất cả text từ các tag <a:t> bên trong một element.

    Args:
        element: XML element chứa shapes.

    Returns:
        Chuỗi text đã ghép từ các tag <a:t>, mỗi paragraph cách nhau bởi newline.
    """
    paragraphs: list[str] = []
    for para in element.iter(f"{{{NS['a']}}}p"):
        runs: list[str] = []
        for run_text in para.iter(f"{{{NS['a']}}}t"):
            if run_text.text:
                runs.append(run_text.text)
        if runs:
            paragraphs.append("".join(runs))
    return "\n".join(paragraphs)


def extract_shapes_from_xlsx(file_path: Path) -> dict[str, list[str]]:
    """Trích xuất text từ shapes trong file .xlsx bằng cách parse XML trực tiếp.

    Mở file .xlsx (ZIP) → tìm xl/drawings/drawing*.xml → parse <xdr:sp> → lấy <a:t>.

    Args:
        file_path: Đường dẫn file .xlsx.

    Returns:
        Dict mapping tên drawing file → list text từ shapes.
        Key là "drawing1", "drawing2", ... tương ứng với thứ tự sheet.
    """
    shapes_by_drawing: dict[str, list[str]] = {}

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            drawing_files = [
                name for name in zf.namelist()
                if name.startswith("xl/drawings/drawing") and name.endswith(".xml")
            ]

            for drawing_file in sorted(drawing_files):
                shape_texts: list[str] = []
                xml_data = zf.read(drawing_file)
                root = ET.fromstring(xml_data)

                # Tìm tất cả shape elements (<xdr:sp>)
                for sp in root.iter(f"{{{NS['xdr']}}}sp"):
                    text = extract_text_from_element(sp)
                    if text.strip():
                        shape_texts.append(text)

                # Tìm group shapes (<xdr:grpSp>) — đệ quy lấy text
                for grp_sp in root.iter(f"{{{NS['xdr']}}}grpSp"):
                    for sp in grp_sp.iter(f"{{{NS['xdr']}}}sp"):
                        text = extract_text_from_element(sp)
                        if text.strip():
                            shape_texts.append(text)

                if shape_texts:
                    # Lấy tên drawing (drawing1, drawing2, ...)
                    drawing_name = Path(drawing_file).stem
                    shapes_by_drawing[drawing_name] = shape_texts
                    logger.debug(
                        "Tìm thấy %d shapes text trong %s",
                        len(shape_texts), drawing_file,
                    )

    except zipfile.BadZipFile:
        logger.warning("File không phải ZIP hợp lệ: %s", safe_file_label(file_path))
    except Exception as e:
        logger.warning("Lỗi khi parse shapes XML từ %s: %s", safe_file_label(file_path), sanitize_error(e))

    return shapes_by_drawing


def extract_images_from_xlsx(file_path: Path) -> dict[str, bytes]:
    """Trích xuất hình ảnh nhúng trong file .xlsx.

    Hình ảnh nằm trong thư mục xl/media/ bên trong ZIP.

    Args:
        file_path: Đường dẫn file .xlsx.

    Returns:
        Dict mapping tên ảnh → dữ liệu bytes.
    """
    images: dict[str, bytes] = {}

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            for name in zf.namelist():
                if name.startswith("xl/media/"):
                    image_name = Path(name).name
                    images[image_name] = zf.read(name)
    except zipfile.BadZipFile:
        logger.warning("File không phải ZIP hợp lệ: %s", safe_file_label(file_path))
    except Exception as e:
        logger.warning("Lỗi khi extract images từ %s: %s", safe_file_label(file_path), sanitize_error(e))

    return images


def map_drawings_to_sheets(file_path: Path) -> dict[str, str]:
    """Mapping drawing file → sheet name trong file .xlsx.

    Đọc xl/worksheets/_rels/sheet*.xml.rels để tìm drawing tương ứng.

    Args:
        file_path: Đường dẫn file .xlsx.

    Returns:
        Dict mapping tên drawing (drawing1, ...) → tên sheet.
    """
    drawing_to_sheet: dict[str, str] = {}

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            # Đọc workbook.xml để lấy thứ tự sheet
            sheet_names: list[str] = []
            if "xl/workbook.xml" in zf.namelist():
                wb_xml = ET.fromstring(zf.read("xl/workbook.xml"))
                ns_ss = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                for sheet_el in wb_xml.iter(f"{{{ns_ss}}}sheet"):
                    sheet_names.append(sheet_el.get("name", ""))

            # Đọc từng sheet rels file
            for idx, sheet_name in enumerate(sheet_names, 1):
                rels_path = f"xl/worksheets/_rels/sheet{idx}.xml.rels"
                if rels_path not in zf.namelist():
                    continue
                rels_xml = ET.fromstring(zf.read(rels_path))
                for rel in rels_xml:
                    target = rel.get("Target", "")
                    if "drawing" in target.lower():
                        drawing_name = Path(target).stem
                        drawing_to_sheet[drawing_name] = sheet_name

    except Exception as e:
        logger.warning("Lỗi khi mapping drawings -> sheets: %s", sanitize_error(e))

    return drawing_to_sheet


def extract_shapes_from_docx(file_path: Path) -> list[str]:
    """Trích xuất text từ shapes/textbox trong file .docx bằng XML parsing.

    Shapes trong Word nằm trong:
    - <mc:AlternateContent> → <wps:txbx> → <w:txbxContent> → <w:p> → <w:r> → <w:t>
    - <w:drawing> → <a:t> (inline drawing shapes)

    Args:
        file_path: Đường dẫn file .docx.

    Returns:
        List các đoạn text từ shapes/textbox.
    """
    shape_texts: list[str] = []

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            if "word/document.xml" not in zf.namelist():
                return shape_texts

            doc_xml = zf.read("word/document.xml")
            root = ET.fromstring(doc_xml)

            # Tìm text trong textbox shapes (<wps:txbx> → <w:txbxContent>)
            txbx_content_tag = f"{{{NS['w']}}}txbxContent"
            for txbx_content in root.iter(txbx_content_tag):
                paragraphs: list[str] = []
                for para in txbx_content.iter(f"{{{NS['w']}}}p"):
                    runs: list[str] = []
                    for run_text in para.iter(f"{{{NS['w']}}}t"):
                        if run_text.text:
                            runs.append(run_text.text)
                    if runs:
                        paragraphs.append("".join(runs))
                if paragraphs:
                    shape_texts.append("\n".join(paragraphs))

            # Tìm text trong drawing shapes (<a:t> bên trong <w:drawing>)
            for drawing in root.iter(f"{{{NS['w']}}}drawing"):
                text = extract_text_from_element(drawing)
                if text.strip():
                    # Tránh trùng lặp với textbox đã lấy ở trên
                    if text not in shape_texts:
                        shape_texts.append(text)

    except zipfile.BadZipFile:
        logger.warning("File không phải ZIP hợp lệ: %s", safe_file_label(file_path))
    except Exception as e:
        logger.warning("Lỗi khi parse shapes từ docx %s: %s", safe_file_label(file_path), sanitize_error(e))

    return shape_texts
