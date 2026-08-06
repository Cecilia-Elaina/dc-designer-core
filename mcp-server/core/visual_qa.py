"""Office and diagram visual-quality checks for final export gates."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


BANNED_OUTPUT_TOKENS = (
    "candidate", "sufficient", "cognitive_strategy", "authentic_programming_task",
    "teacher_private", "AI_INFERENCE", "AI_SUGGESTION", "TEACHER_INPUT",
    "OFFICIAL_STANDARD", "clause_candidate", "source_hash", "raw dict", "level items note",
)
RAW_DICT_RE = re.compile(r"\{\s*['\"](?:objective_id|source_id|status|level|items)")
EMPTY_BULLET_RE = re.compile(r"(?:^|\n)\s*[-•]\s*[:：]\s*(?:\n|$)")
FONT_SIZE_RE = re.compile(r"w:sz[^>]*w:val=\"(\d+)\"")
DOCX_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}
CHINESE_FONT_HINTS = ("宋体", "SimSun", "Microsoft YaHei", "微软雅黑", "等线", "DengXian", "黑体", "SimHei")


def find_soffice() -> str:
    candidates = [
        os.environ.get("SOFFICE_PATH", ""),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        shutil.which("soffice") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    return ""


def find_pdftoppm() -> str:
    command = shutil.which("pdftoppm") or ""
    if command and Path(command).suffix.lower() == ".cmd":
        wrapper = Path(command).resolve()
        native = wrapper.parents[2] / "native" / "poppler" / "Library" / "bin" / "pdftoppm.exe"
        if native.is_file():
            return str(native)
    return command


def inspect_docx_structure(path: str | Path) -> dict:
    target = Path(path)
    result = {
        "path": str(target),
        "exists": target.is_file(),
        "size": target.stat().st_size if target.is_file() else 0,
        "status": "pass",
        "errors": [],
        "warnings": [],
        "drawings": 0,
        "tables": 0,
        "min_font_half_points": None,
        "banned_tokens": [],
        "sections": [],
        "font_families": [],
        "table_metrics": [],
        "image_assets": [],
        "drawing_extents": [],
        "pagination_risks": [],
    }
    if not target.is_file():
        result["status"] = "fail"
        result["errors"].append("Word 文件不存在")
        return result
    try:
        with zipfile.ZipFile(target) as archive:
            names = set(archive.namelist())
            if "word/document.xml" not in names:
                raise ValueError("不是有效的 Word 文档")
            xml_bytes = archive.read("word/document.xml")
            xml = xml_bytes.decode("utf-8", errors="ignore")
            document_root = ET.fromstring(xml_bytes)
            result["drawings"] = xml.count("w:drawing")
            result["tables"] = xml.count("<w:tbl")
            text = re.sub(r"<[^>]+>", " ", xml)
            text = text.replace("&quot;", '"').replace("&apos;", "'")
            result["banned_tokens"] = [token for token in BANNED_OUTPUT_TOKENS if token.lower() in text.lower()]
            if result["banned_tokens"]:
                result["status"] = "fail"
                result["errors"].append("面向教师的 Word 文本包含内部枚举或原始结构字段")
            if RAW_DICT_RE.search(text) or "{'" in text:
                result["status"] = "fail"
                result["errors"].append("Word 文本包含原始字典输出")
            if EMPTY_BULLET_RE.search(text):
                result["status"] = "fail"
                result["errors"].append("Word 文本包含空 bullet")
            sections = document_root.findall(".//w:sectPr", DOCX_NS)
            w_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            for section in sections:
                page_size = section.find("w:pgSz", DOCX_NS)
                margins = section.find("w:pgMar", DOCX_NS)
                result["sections"].append({
                    "width_twips": int(page_size.get(f"{{{w_ns}}}w", "0")) if page_size is not None else 0,
                    "height_twips": int(page_size.get(f"{{{w_ns}}}h", "0")) if page_size is not None else 0,
                    "orientation": page_size.get(f"{{{w_ns}}}orient", "portrait") if page_size is not None else "portrait",
                    "margins_twips": {
                        key: int(margins.get(f"{{{w_ns}}}{key}", "0"))
                        for key in ("top", "right", "bottom", "left")
                    } if margins is not None else {},
                })
            font_families = set()
            for fonts in document_root.findall(".//w:rFonts", DOCX_NS):
                for key, value in fonts.attrib.items():
                    if key.rsplit("}", 1)[-1] in {"ascii", "hAnsi", "eastAsia", "cs"} and value:
                        font_families.add(value)
            result["font_families"] = sorted(font_families)
            if not any(any(hint.lower() in family.lower() for hint in CHINESE_FONT_HINTS) for family in font_families):
                result["warnings"].append("未检测到明确的中文字体族，需检查 Word 默认字体")
            for table_index, table in enumerate(document_root.findall(".//w:tbl", DOCX_NS), start=1):
                rows = table.findall("./w:tr", DOCX_NS)
                columns = max((len(row.findall("./w:tc", DOCX_NS)) for row in rows), default=0)
                first_row = rows[0] if rows else None
                header_bold = bool(first_row is not None and first_row.findall(".//w:b", DOCX_NS))
                header_repeat = bool(first_row is not None and first_row.findall(".//w:tblHeader", DOCX_NS))
                row_split_protected = sum(1 for row in rows if row.findall("./w:cantSplit", DOCX_NS))
                cell_text_lengths = [
                    sum(len(node.text or "") for node in cell.findall(".//w:t", DOCX_NS))
                    for cell in table.findall(".//w:tc", DOCX_NS)
                ]
                result["table_metrics"].append({
                    "table": table_index,
                    "rows": len(rows),
                    "columns": columns,
                    "header_bold": header_bold,
                    "header_repeat": header_repeat,
                    "row_split_protected": row_split_protected,
                    "max_cell_text_length": max(cell_text_lengths, default=0),
                })
                if len(rows) > 10 and not header_repeat:
                    result["pagination_risks"].append({"table": table_index, "risk": "long_table_without_repeated_header"})
                if columns >= 6 and not any(section.get("orientation") == "landscape" for section in result["sections"]):
                    result["pagination_risks"].append({"table": table_index, "risk": "wide_table_without_landscape_section"})
            for drawing in document_root.findall(".//wp:extent", DOCX_NS):
                result["drawing_extents"].append({"cx": int(drawing.get("cx", "0")), "cy": int(drawing.get("cy", "0"))})
            try:
                from PIL import Image
                for name in sorted(item for item in names if item.startswith("word/media/")):
                    with Image.open(io.BytesIO(archive.read(name))) as image:
                        asset = {"name": name, "width": image.width, "height": image.height, "format": image.format}
                        result["image_assets"].append(asset)
                        if image.width < 800 or image.height < 240:
                            result["warnings"].append(f"嵌入图片 {name} 分辨率偏小，可能导致图中文字不可读")
            except ImportError:
                result["warnings"].append("缺少 Pillow，无法检查嵌入图片分辨率")
            if result["pagination_risks"]:
                result["warnings"].append("发现长表格或宽表格分页风险，需结合逐页 PNG 检查")
            font_values = [int(value) for value in FONT_SIZE_RE.findall(xml)]
            if font_values:
                result["min_font_half_points"] = min(font_values)
                if min(font_values) < 18:
                    result["warnings"].append("发现小于 9 磅的显式字体，需要结合 PDF 页面人工复核")
            else:
                result["warnings"].append("未能从 Word XML 读取显式字号，需结合 PDF 页面复核")
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        result["status"] = "fail"
        result["errors"].append(str(exc))
    return result


def _render_pdf_pages(pdf_path: Path, image_dir: Path) -> dict:
    command = find_pdftoppm()
    result = {"status": "unverified", "renderer": command, "pages": [], "errors": [], "warnings": []}
    if not command:
        result["warnings"].append("未找到 pdftoppm，无法生成逐页 PNG")
        return result
    image_dir.mkdir(parents=True, exist_ok=True)
    prefix = image_dir / "page"
    command_args = [command, "-png", "-r", "150", str(pdf_path), str(prefix)]
    invocation = subprocess.list2cmdline(command_args) if Path(command).suffix.lower() == ".cmd" else command_args
    completed = subprocess.run(
        invocation,
        capture_output=True,
        text=True,
        timeout=120,
        shell=Path(command).suffix.lower() == ".cmd",
    )
    if completed.returncode != 0:
        result["errors"].append((completed.stderr or completed.stdout or "pdftoppm 执行失败").strip())
        result["status"] = "fail"
        return result
    try:
        from PIL import Image, ImageStat
    except ImportError:
        result["warnings"].append("缺少 Pillow，无法计算页面空白度")
        result["status"] = "unverified"
        return result
    page_files = sorted(image_dir.glob("page-*.png"))
    if not page_files:
        result["status"] = "fail"
        result["errors"].append("PDF 未生成页面图片")
        return result
    result["status"] = "pass"
    for page in page_files:
        with Image.open(page) as image:
            gray = image.convert("L")
            mean = ImageStat.Stat(gray).mean[0]
            extrema = gray.getextrema()
            blank = mean > 252 and extrema[0] > 220
            dark = gray.point(lambda value: 255 if value < 245 else 0)
            bbox = dark.getbbox()
            edge_touch = False
            if bbox:
                edge_margin = 8
                edge_touch = min(bbox[0], bbox[1], image.width - bbox[2], image.height - bbox[3]) <= edge_margin
            item = {
                "path": str(page),
                "width": image.width,
                "height": image.height,
                "mean_gray": round(mean, 2),
                "blank": blank,
                "content_bbox": list(bbox) if bbox else None,
                "content_coverage": round((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) / (image.width * image.height), 4) if bbox else 0,
                "content_touches_page_edge": edge_touch,
            }
            result["pages"].append(item)
            if blank:
                result["status"] = "fail"
                result["errors"].append(f"发现疑似空白页: {page.name}")
            elif edge_touch:
                result["warnings"].append(f"页面 {page.name} 的非空内容接近页面边缘，需检查是否存在溢出或裁切")
    return result


def render_docx(path: str | Path, output_dir: str | Path) -> dict:
    target = Path(path)
    output = Path(output_dir)
    structural = inspect_docx_structure(target)
    result = {"structural": structural, "render": {"status": "unverified", "errors": [], "warnings": []}}
    soffice = find_soffice()
    if not soffice:
        result["render"]["warnings"].append("未找到 LibreOffice，无法验证 Word 的真实分页和视觉布局")
        result["status"] = "unverified" if structural["status"] == "pass" else "fail"
        return result
    if not target.is_file():
        result["status"] = "fail"
        return result
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dc-office-") as temp:
        profile = Path(temp) / "profile"
        profile.mkdir(parents=True, exist_ok=True)
        try:
            completed = subprocess.run(
                [soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--convert-to", "pdf", "--outdir", temp, str(target)],
                capture_output=True,
                text=True,
                timeout=90,
            )
        except subprocess.TimeoutExpired as exc:
            result["render"]["status"] = "fail"
            result["render"]["errors"].append(f"LibreOffice 转换超时（90秒）：{target.name}")
            return result
        pdf_path = Path(temp) / f"{target.stem}.pdf"
        if completed.returncode != 0 or not pdf_path.is_file():
            result["render"]["status"] = "fail"
            result["render"]["errors"].append((completed.stderr or completed.stdout or "LibreOffice 转换失败").strip())
        else:
            result["render"] = _render_pdf_pages(pdf_path, output / target.stem)
            saved_pdf = output / f"{target.stem}.pdf"
            saved_pdf.write_bytes(pdf_path.read_bytes())
            result["render"]["pdf"] = str(saved_pdf)
    if structural["status"] == "fail" or result["render"]["status"] == "fail":
        result["status"] = "fail"
    elif result["render"]["status"] == "pass":
        result["status"] = "pass"
    else:
        result["status"] = "unverified"
    return result


def inspect_drawio(path: str | Path, *, minimum_pages: int = 1) -> dict:
    target = Path(path)
    result = {
        "path": str(target),
        "status": "pass",
        "diagrams": 0,
        "cell_count": 0,
        "duplicate_ids": [],
        "errors": [],
        "page_metrics": [],
    }
    if not target.is_file():
        result["status"] = "fail"
        result["errors"].append("Draw.io 文件不存在")
        return result
    try:
        root = ET.fromstring(target.read_text(encoding="utf-8"))
        diagrams = root.findall("diagram")
        result["diagrams"] = len(diagrams)
        duplicate_ids: set[str] = set()
        cell_count = 0
        for diagram in diagrams:
            page_ids: list[str] = []
            for cell in diagram.iter("mxCell"):
                value = cell.attrib.get("id", "")
                if value:
                    page_ids.append(value)
            cell_count += len(page_ids)
            labels = [cell.attrib.get("value", "").strip() for cell in diagram.iter("mxCell") if cell.attrib.get("value", "").strip()]
            result["page_metrics"].append({
                "name": diagram.attrib.get("name", ""),
                "label_count": len(labels),
                "max_label_length": max((len(label) for label in labels), default=0),
            })
            duplicate_ids.update(item for item in set(page_ids) if page_ids.count(item) > 1)
        result["cell_count"] = cell_count
        result["duplicate_ids"] = sorted(duplicate_ids)
        if len(diagrams) < minimum_pages:
            result["status"] = "fail"
            result["errors"].append(f"Draw.io 至少需要 {minimum_pages} 个独立页面")
        if not diagrams:
            result["status"] = "fail"
            result["errors"].append("Draw.io 未包含可编辑页面")
        if result["duplicate_ids"]:
            result["status"] = "fail"
            result["errors"].append("Draw.io 存在重复节点 ID")
    except (OSError, ET.ParseError) as exc:
        result["status"] = "fail"
        result["errors"].append(str(exc))
    return result


def run_visual_qa(files: dict[str, str], output_dir: str | Path) -> dict:
    output = Path(output_dir)
    documents = {}
    for key in ("dc_report", "lesson_plan", "student_worksheet", "ai_process_record"):
        path = files.get(key, "")
        if path:
            documents[key] = render_docx(path, output / "documents")
    drawio = {}
    for key in ("drawio_workbook", "goal_operation_drawio", "skill_hierarchy_drawio"):
        path = files.get(key, "")
        if path:
            minimum_pages = 3 if key == "drawio_workbook" else 1
            drawio[key] = inspect_drawio(path, minimum_pages=minimum_pages)
    all_statuses = [item["status"] for item in documents.values()] + [item["status"] for item in drawio.values()]
    if any(status == "fail" for status in all_statuses):
        status = "fail"
    elif all_statuses and all(status == "pass" for status in all_statuses):
        status = "pass"
    else:
        status = "unverified"
    report = {
        "schema_version": "1.0.0",
        "status": status,
        "documents": documents,
        "drawio": drawio,
        "visual_gate": "pass" if status == "pass" else "fail" if status == "fail" else "unverified",
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    output.mkdir(parents=True, exist_ok=True)
    report["report_path"] = str(output / "visual_qa_report.json")
    (output / "visual_qa_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
