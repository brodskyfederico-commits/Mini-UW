"""Read the labeled text tables of the synthetic PRELIMINAR evidence bundle."""
from io import BytesIO
import re

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.expense_cash_detail import _json


SCHEMA = "miniuw.synthetic-preliminary-pilot.v2"
MARKER = "SYNTHETIC MINI-UW PRELIMINAR"
FILENAME = "Evidence.pdf"
ROLES = ("A101", "A601", "acquisition_and_costs", "rent_and_expenses", "calendar",
         "construction_bank", "permanent_bank", "exit", "florida_property_tax")
BANK_ROLES = ("construction_bank", "permanent_bank")
CLAIM = re.compile(r"C[0-9]{1,2}")
TOKEN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|[0-9]{4}|\[[0-9]{1,2}\]")


def parse_values(value):
    # Only scalar literals are accepted in a table row. Groups are reconstructed
    # from labeled paths, keeping each source line independently citable.
    try:
        parsed = _json(value.encode("utf-8"), 240)
    except ValidationError as error:
        raise ValueError("valor ausente o inválido") from error
    if parsed is not None and type(parsed) not in (str, int, bool):
        raise ValueError("valor fuera del formato de tabla")
    return parsed


def set_value(root, path, value):
    parts = path.split(".")
    if not 1 <= len(parts) <= 7 or any(TOKEN.fullmatch(part) is None for part in parts):
        raise ValueError("campo fuera del formato de tabla")
    node = root
    for part in parts[:-1]:
        node = node.setdefault(part, {})
        if not isinstance(node, dict):
            raise ValueError("campos incompatibles")
    if parts[-1] in node:
        raise ValueError("campo duplicado")
    node[parts[-1]] = value


def restore_lists(group):
    if not isinstance(group, dict):
        return group
    if group and all(key.startswith("[") for key in group):
        positions = sorted(int(key[1:-1]) for key in group)
        if positions != list(range(len(group))) or set(group) != {f"[{position}]" for position in positions}:
            raise ValueError("índices no consecutivos")
        return [restore_lists(group[f"[{position}]"]) for position in positions]
    if any(key.startswith("[") for key in group):
        raise ValueError("campos e índices incompatibles")
    return {key: restore_lists(value) for key, value in group.items()}


def parse_page(lines, deal, scenario):
    if len(lines) < 6 or lines[:2] != [MARKER, f"Expediente | {deal}"] or lines[2] != f"Escenario | {scenario}":
        raise ValueError("identidad del respaldo incompatible")
    role = lines[3].removeprefix("Rol | ")
    if role not in ROLES or lines[3] != f"Rol | {role}" or lines[4] != "Tipo | Campo | Valor":
        raise ValueError("rol o encabezado no reconocido")
    data, cells, locators = {}, {}, {}
    for line_number, text in enumerate(lines[5:], 6):
        pieces = text.split(" | ", 2)
        if len(pieces) != 3:
            raise ValueError(f"línea {line_number} sin campo y valor")
        kind, key, value = pieces
        try:
            if kind == "Inputs" and CLAIM.fullmatch(key):
                if key in cells:
                    raise ValueError("celda duplicada")
                cells[key] = value
            elif kind == "Dato":
                set_value(data, key, parse_values(value))
            else:
                raise ValueError("tipo de fila incompatible")
        except ValueError as error:
            raise ValueError(f"línea {line_number} ({key[:28]}) · {error}") from error
        locators[f"{kind}/{key}"] = line_number
    return role, dict(data=restore_lists(data), cells=cells, locators=locators)


def read_bundle(raw, deal, scenario):
    pages, blockers = {}, []
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= len(ROLES) + 1:
            return {}, ["inventario de páginas incompatible"]
        for page_number, page in enumerate(reader.pages, 1):
            if page.images:
                blockers.append(f"p. {page_number} · se requiere una tabla de texto sintética")
                continue
            text = page.extract_text() or ""
            if len(text) > 12_000:
                blockers.append(f"p. {page_number} · tabla de texto excede el formato")
                continue
            try:
                role, reading = parse_page([line.strip() for line in text.splitlines() if line.strip()], deal, scenario)
            except ValueError as error:
                blockers.append(f"p. {page_number} · {error}")
                continue
            if role in pages:
                blockers.append(f"p. {page_number} · rol duplicado {role}")
            else:
                pages[role] = reading | {"page": page_number}
    except (PyPdfError, OSError, ValueError, TypeError, KeyError, NotImplementedError, RecursionError):
        return {}, ["PDF ilegible"]
    blockers.extend(f"falta página {role}" for role in ROLES if role not in pages)
    return pages, blockers


def merge_financing(pages):
    construction, permanent = (pages[role] for role in BANK_ROLES)
    for key in ("data", "cells"):
        if construction[key].keys() & permanent[key].keys():
            raise ValueError("el crédito de obra y permanente declaran campos duplicados")
    return {key: construction[key] | permanent[key] for key in ("data", "cells")}
