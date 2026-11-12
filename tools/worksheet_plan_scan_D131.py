"""OCR explicitly declared areas from a bounded synthetic grayscale plan scan."""
from collections import defaultdict
from csv import DictReader
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
import os
from pathlib import Path
from shutil import which
from subprocess import SubprocessError, run

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from miniuw_foundation.scheduled_expense_case import sha
from worksheet_local_sources_D127 import check, object_or_empty, synthetic_id
from worksheet_plan_pdf_D130 import MARKER, SUMMARY_ROW, TABLE_ROW, sheet_area, unavailable_plan


PROFILE = "SYNTHETIC-D131-full-page-grayscale"
DEFAULT_TESSDATA = "/usr/share/tesseract-ocr/5/tessdata"
MAX_SCAN_PIXELS = 4_000_000


def valid_ocr_options(ocr):
    return (set(ocr) == {"engine_version", "image_library_version", "language_sha256", "dpi", "minimum_word_confidence"}
            and type(ocr["dpi"]) is int and 72 <= ocr["dpi"] <= 400
            and type(ocr["minimum_word_confidence"]) is int and 0 < ocr["minimum_word_confidence"] <= 100)


def full_page_image(page, *, allow_text_layer=False):
    contents = page.get_contents()
    if contents is None:
        return None
    operations = contents.operations
    image_ops = operations[:4]
    if [op for _, op in image_ops] != [b"q", b"cm", b"Do", b"Q"]:
        return None
    tail = [op for _, op in operations[4:]]
    if tail and (not allow_text_layer or tail[0] != b"BT" or tail[-1] != b"ET"
                 or any(op not in (b"Tf", b"Tr", b"Tm", b"Tj") for op in tail[1:-1])):
        return None
    matrix, draw = image_ops[1][0], image_ops[2][0]
    extent = (page.mediabox.width, 0, 0, page.mediabox.height, 0, 0)
    if (tuple(matrix) != extent or len(draw) != 1 or tuple(page.mediabox.lower_left) != (0, 0)
            or tuple(page.cropbox) != tuple(page.mediabox)
            or page.rotation != 0):
        return None
    resources = page["/Resources"]["/XObject"].get_object()
    if set(resources) != {draw[0]}:
        return None
    image = resources[draw[0]]
    width, height = image.get("/Width"), image.get("/Height")
    if (image.get("/Subtype") != "/Image" or image.get("/ColorSpace") != "/DeviceGray"
            or image.get("/BitsPerComponent") != 8 or image.get("/Filter") != "/FlateDecode"
            or any(key in image for key in ("/Decode", "/Mask", "/SMask", "/ImageMask"))
            or not isinstance(width, int) or not isinstance(height, int)
            or width <= 0 or height <= 0 or width * height > MAX_SCAN_PIXELS):
        return None
    pixels = image.get_data()
    if len(pixels) != width * height:
        return None
    return f"P5\n{width} {height}\n255\n".encode() + pixels


def runtime(ocr):
    engine = which("tesseract")
    tessdata = Path(os.environ.get("TESSDATA_PREFIX") or DEFAULT_TESSDATA)
    language = tessdata / "eng.traineddata"
    if engine is None or not language.is_file():
        return None, "scan_ocr_runtime_missing"
    env = os.environ | {"LC_ALL": "C", "OMP_THREAD_LIMIT": "1"}
    proc = run([engine, "--version"], capture_output=True, check=False, timeout=5, text=True, env=env)
    versions = proc.stdout.splitlines()
    if (proc.returncode or len(versions) < 2 or versions[0].strip() != ocr["engine_version"]
            or versions[1].strip() != ocr["image_library_version"]
            or sha(language.read_bytes()) != ocr["language_sha256"]):
        return None, "scan_ocr_runtime_mismatch"
    return ([engine, "stdin", "stdout", "--tessdata-dir", str(tessdata), "-l", "eng",
             "--dpi", str(ocr["dpi"]), "--psm", "11", "tsv"], env), None


def recognize(image, command, env):
    proc = run(command, input=image, capture_output=True, check=False, timeout=15, env=env)
    if proc.returncode or len(proc.stdout) > 262144:
        raise ValueError("Invalid OCR result")
    groups = defaultdict(list)
    for row in DictReader(StringIO(proc.stdout.decode("utf-8")), delimiter="\t"):
        word = (row.get("text") or "").strip()
        if row["level"] != "5" or not word:
            continue
        key = tuple(row[field] for field in ("block_num", "par_num", "line_num"))
        confidence = Decimal(row["conf"])
        box = tuple(int(row[field]) for field in ("left", "top", "width", "height"))
        if not confidence.is_finite() or not 0 <= confidence <= 100 or any(v < 0 for v in box):
            raise ValueError("Invalid OCR word confidence or location")
        groups[key].append((word, confidence, box))
    lines = []
    for words in groups.values():
        text = " ".join(word for word, _, _ in words)
        minimum = min(confidence for _, confidence, _ in words)
        boxes = [box for _, _, box in words]
        region = [min(x for x, _, _, _ in boxes), min(y for _, y, _, _ in boxes),
                  max(x + w for x, _, w, _ in boxes), max(y + h for _, y, _, h in boxes)]
        lines.append(dict(text=text, minimum_word_confidence=str(minimum), pixel_region=region))
    return lines


def scan_reading(pages, sheet, label, pattern, digest, plan_ref, threshold):
    text_pages = [(index, [line["text"] for line in lines]) for index, lines in pages]
    row = sheet_area(text_pages, sheet, label, pattern, digest, plan_ref)
    if row["blockers"]:
        return row
    headings = (MARKER, f"PLAN REF {plan_ref}", f"SHEET {sheet}", row["raw_line"])
    lines = [line for index, entries in pages if index == row["page"] for line in entries if line["text"] in headings]
    row["ocr"] = dict(minimum_word_confidence_required=threshold, cited_lines=lines)
    if (len(lines) != len(headings) or any(Decimal(line["minimum_word_confidence"]) < threshold for line in lines)):
        row["ocr"]["observed_value"] = row.pop("value")
        row.update(state="PENDING", blockers=["scan_ocr_confidence_below_declared_minimum_or_ambiguous"])
    return row


def read_scanned_plan(raw, specification):
    spec = object_or_empty(specification)
    if raw is None:
        return unavailable_plan("plan_pdf_missing")
    digest = sha(raw)
    if digest != spec.get("sha256") or not synthetic_id(spec.get("plan_ref")):
        return unavailable_plan("plan_pdf_hash_or_reference_mismatch", digest)
    ocr = object_or_empty(spec.get("ocr"))
    if spec.get("scan_profile") != PROFILE or not valid_ocr_options(ocr):
        return unavailable_plan("scan_ocr_profile_missing_or_invalid", digest)
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or len(reader.pages) != 2:
            return unavailable_plan("scan_image_layout_unsupported", digest)
        images = [full_page_image(page) for page in reader.pages]
        if any(image is None for image in images):
            return unavailable_plan("scan_image_layout_unsupported", digest)
        command, blocker = runtime(ocr)
        if blocker:
            return unavailable_plan(blocker, digest)
        pages = [(index, recognize(image, *command)) for index, image in enumerate(images, 1)]
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, SubprocessError, InvalidOperation, NotImplementedError):
        return unavailable_plan("scan_ocr_or_image_unreadable", digest)
    pages = [(index, lines) for index, lines in pages if any(line["text"] == MARKER for line in lines)]
    if not pages:
        return unavailable_plan("synthetic_scan_plan_not_identified", digest)
    plan_ref, threshold = spec["plan_ref"], ocr["minimum_word_confidence"]
    return dict(document=check(kind="synthetic_scanned_pdf_plan", source_file="Plan.pdf", sha256=digest,
                               plan_ref=plan_ref, ocr=ocr | {"language": "eng"}),
                B05=scan_reading(pages, "A101", "Gross building area", TABLE_ROW, digest, plan_ref, threshold),
                B06=scan_reading(pages, "A601", "Declared GBA", SUMMARY_ROW, digest, plan_ref, threshold))
