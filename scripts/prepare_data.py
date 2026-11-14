#!/usr/bin/env python3
"""Normalize NASA PSI experimental CSVs into a filterable master table.

Source CSVs are treated as immutable. Each output row points back to its
source file and logical CSV record so original values can be recovered without
duplicating them in a JSON column.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw"
PROCESSED_ROOT = ROOT / "data" / "processed"
HISTORY_ROOT = ROOT / "docs" / "historial_datos"
MASTER_PATH = PROCESSED_ROOT / "experiments.csv"
PDF_CATALOG_PATH = PROCESSED_ROOT / "pdf_catalog.json"
MISSING_VALUES = {"", "n/a", "na", "nan", "null", "none", "-999", "-9999"}


def clean_header(value: object) -> str:
    """Fold a header for matching while preserving its original in source CSV."""
    text = unicodedata.normalize("NFKD", str(value).replace("\ufeff", ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def read_source_csv(path: Path) -> tuple[pd.DataFrame, dict[str, str], int, str]:
    """Read a CSV with encoding/delimiter detection and locate its real header.

    Returns the data frame, key/value metadata found before the header, the
    zero-based header record index, and the successful encoding.
    """
    raw = path.read_bytes()
    decoded = None
    used_encoding = ""
    for encoding in ("utf-8-sig",):
        try:
            decoded = raw.decode(encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    if decoded is None:
        # Latin-1 accepts every byte; choose Windows-1252 for files containing
        # its printable punctuation range, and Latin-1 otherwise.
        probable_cp1252 = any(0x80 <= byte <= 0x9F for byte in raw)
        used_encoding = "cp1252" if probable_cp1252 else "latin-1"
        decoded = raw.decode(used_encoding)
    if decoded is None:
        decoded = raw.decode("utf-8", errors="replace")
        used_encoding = "utf-8-replacement"

    try:
        delimiter = csv.Sniffer().sniff(decoded[:8192], delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = ","

    parsed = pd.read_csv(
        path,
        sep=delimiter,
        header=None,
        dtype=str,
        keep_default_na=False,
        encoding=used_encoding if used_encoding != "utf-8-replacement" else "utf-8",
        encoding_errors="replace",
        engine="python",
    )
    if parsed.empty:
        return pd.DataFrame(), {}, 0, used_encoding

    # Prefer the first row with the widest non-empty shape. In these PSI
    # exports this identifies the tabular header while allowing key/value
    # metadata rows before it.
    widths = parsed.apply(lambda row: sum(bool(str(v).strip()) for v in row), axis=1)
    max_width = int(widths.max())
    candidates = [i for i, width in enumerate(widths.tolist()) if width == max_width and width >= 2]
    header_index = candidates[0] if candidates else 0
    headers = [str(value).strip().replace("\ufeff", "") for value in parsed.iloc[header_index].tolist()]
    headers = [value if value else f"unnamed_{i + 1}" for i, value in enumerate(headers)]

    metadata: dict[str, str] = {}
    for _, row in parsed.iloc[:header_index].iterrows():
        cells = [str(v).strip() for v in row.tolist() if str(v).strip()]
        if len(cells) >= 2:
            key = cells[0].rstrip(":=").strip()
            value = cells[1].lstrip(":= ").strip()
            if key and value:
                metadata[key] = value

    data = parsed.iloc[header_index + 1 :].copy()
    data.columns = headers
    data["__source_row"] = data.index + 1
    data = data.loc[data.apply(lambda row: any(str(v).strip() for v in row), axis=1)]
    return data, metadata, header_index, used_encoding


def _find_column(columns: Iterable[str], aliases: Iterable[str]) -> str | None:
    normalized = {clean_header(column): column for column in columns}
    for alias in aliases:
        found = normalized.get(clean_header(alias))
        if found is not None:
            return found
    return None


def _metadata_value(metadata: dict[str, str], aliases: Iterable[str]) -> str:
    normalized = {clean_header(key): value for key, value in metadata.items()}
    for alias in aliases:
        value = normalized.get(clean_header(alias), "")
        if str(value).strip():
            return str(value).strip()
    return ""


def _value(row: pd.Series, columns: Iterable[str], aliases: Iterable[str]) -> str:
    col = _find_column(columns, aliases)
    if col is None:
        return ""
    value = str(row.get(col, "")).strip()
    return "" if value.lower() in MISSING_VALUES else value


def _number(value: str) -> float | None:
    """Read the first numeric value in a cell, excluding sensor sentinels."""
    text = str(value).strip()
    if not text or text.lower() in MISSING_VALUES or text.lower() == "no ignition":
        return None
    match = re.search(r"[-+]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", text)
    if not match:
        return None
    try:
        number = float(match.group(0).replace(",", ""))
    except ValueError:
        return None
    if not math.isfinite(number) or number in {-999.0, -9999.0}:
        return None
    return number


def _unit_from(value: str, header: str) -> str:
    text = f"{value} {header}".lower()
    for unit in ("mmhg", "kpa", "psi", "bar", "atm"):
        if unit in text:
            return unit
    return ""


def _pressure_kpa(row: pd.Series, columns: list[str]) -> float | None:
    aliases = (
        "pmean (atm)", "mean pressure (atm)", "ambient pressure (atm)",
        "pressure", "approx p (bar)", "ambient pressure; mmHg",
        "pressure (kpa)", "pressure (psi)", "pressure (bar)",
    )
    col = _find_column(columns, aliases)
    if not col:
        col = next((c for c in columns if "pressure" in clean_header(c) or clean_header(c).startswith("approx p")), None)
    if col is None:
        return None
    value = str(row.get(col, "")).strip()
    number = _number(value)
    if number is None:
        return None
    unit = _unit_from(value, col)
    if unit == "atm": return number * 101.325
    if unit == "bar": return number * 100.0
    if unit == "mmhg": return number * 0.133322368
    if unit == "psi": return number * 6.894757293
    if unit == "kpa": return number
    # Unitless PSI pressure fields are retained as unknown rather than guessed.
    return None


FUEL_ALIASES = {
    "c3h8": "propane", "propane": "propane", "propano": "propane",
    "ch4": "methane", "methane": "methane", "metano": "methane",
    "c2h4": "ethylene", "ethylene": "ethylene", "etileno": "ethylene",
    "c2h6": "ethane", "ethane": "ethane",
    "methanol": "methanol", "iso-octane": "iso-octane", "isooctane": "iso-octane",
    "n-octane": "n-octane", "heptane": "heptane", "c12h26": "n-dodecane",
}


def normalize_fuel(value: str) -> str:
    text = str(value).strip().lower()
    if not text:
        return ""
    # Match a known chemical token inside values such as "100% C2H4".
    for alias, canonical in sorted(FUEL_ALIASES.items(), key=lambda item: -len(item[0])):
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text):
            return canonical
    return text


def _fuel(row: pd.Series, columns: list[str], metadata: dict[str, str], filename: str) -> tuple[str, str]:
    raw = _value(row, columns, ("Fuel", "Fuel Bottle", "Fuel Type", "Sample (Fuel Type)"))
    if not raw:
        raw = _metadata_value(metadata, ("Fuel", "Fuel Bottle", "Fuel Type"))
    if not raw:
        # A filename/context may identify the fuel. Do not infer from material
        # fields such as "Fuel Sample Material".
        context = " ".join([filename, *metadata.values()])
        raw = next((token for token in ("propane", "propano", "c3h8", "methane", "ch4", "ethylene", "c2h4")
                    if re.search(rf"(?<![a-z0-9]){token}(?![a-z0-9])", context, re.I)), "")
    return raw, normalize_fuel(raw)


def _oxygen_fraction(row: pd.Series, columns: list[str]) -> float | None:
    # Prefer initial or mean oxygen conditions; a final value is a fallback.
    ordered = (
        "Oxygen Mole Fraction", "XO2", "X_O2", "O2_conc", "Oxygen (%)",
        "Oxygen Conc (percent)", "Calibrated initial O2 % by vol",
        "O initial ambient composition; mole fraction", "Oxygen",
        "XO2 before test", "XO2 (init)", "XO2  after test", "XO2 (final)",
    )
    for alias in ordered:
        col = _find_column(columns, (alias,))
        if col is None:
            continue
        value = str(row.get(col, "")).strip()
        number = _number(value)
        if number is None:
            continue
        header = clean_header(col)
        if "%" in col or "percent" in header or " vol" in header:
            return number / 100.0
        if 0 <= number <= 1:
            return number
        if 1 < number <= 100 and "oxygen" in header:
            return number / 100.0
    return None


def _context_number(metadata: dict[str, str], filename: str, kind: str) -> float | None:
    """Read a contextual oxygen/pressure value when no row field is present."""
    if kind == "oxygen":
        for key, value in metadata.items():
            header = clean_header(key)
            if "oxygen" not in header and "o2" not in header and "xo2" not in header:
                continue
            number = _number(value)
            if number is not None:
                return number / 100 if ("%" in key or "percent" in header) else number
        match = re.search(r"(?<![a-z0-9])(\d+(?:\.\d+)?)\s*o2\b", filename, re.I)
        if match:
            number = float(match.group(1))
            return number / 100 if number > 1 else number
    if kind == "pressure":
        for key, value in metadata.items():
            header = clean_header(key)
            if "pressure" in header or "press" in header:
                number = _number(value)
                unit = _unit_from(value, key)
                if number is not None:
                    factors = {"atm": 101.325, "bar": 100.0, "mmhg": 0.133322368,
                               "psi": 6.894757293, "kpa": 1.0}
                    return number * factors[unit] if unit in factors else None
    return None


def _ignition_success(row: pd.Series, columns: list[str]) -> bool | None:
    col = _find_column(columns, ("Hot ignition", "Ignition success", "Ignited"))
    if col is None:
        return None
    value = str(row.get(col, "")).strip().lower()
    if value in {"yes", "true", "1", "success", "successful", "ignited"}: return True
    if value in {"no", "false", "0", "failed", "no ignition", "not ignited"}: return False
    return None


def _pdf_catalog() -> dict[str, list[str]]:
    catalog: dict[str, list[str]] = {}
    for path in sorted(RAW_ROOT.rglob("*.pdf")):
        match = re.search(r"PSI-\d+", path.as_posix(), re.I)
        if match:
            investigation_id = match.group(0).upper()
            catalog.setdefault(investigation_id, []).append(path.relative_to(ROOT).as_posix())
    return catalog


def _history_path(investigation_id: str) -> str:
    return (Path("docs") / "historial_datos" / f"{investigation_id}.md").as_posix()


def _build_history_docs(investigations: dict[str, list[dict]]) -> None:
    """Create study-level documentation once; never overwrite user edits."""
    HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
    for investigation_id, records in investigations.items():
        target = HISTORY_ROOT / f"{investigation_id}.md"
        if target.exists():
            continue
        source_files = sorted({r["source_file"] for r in records})
        lines = [
            f"# Historial de datos — {investigation_id}", "",
            "Documento de referencia de las normalizaciones aplicadas por el pipeline. "
            "Los CSV originales permanecen intactos en `data/raw/`.", "",
            "## Fuentes", "",
        ]
        lines.extend(f"- `{p}`" for p in source_files)
        lines += ["", "## Reglas aplicadas", "",
                  "- Se asociaron las filas con `investigation_id`, `source_file` y `source_row` para permitir la recuperación de sus valores originales.",
                  "- Se limpiaron nombres de cabecera para reconocer alias; los nombres originales se conservan en los CSV fuente.",
                  "- Se normalizaron combustibles reconocidos (por ejemplo, `C3H8` → `propane`, `CH4` → `methane`, `C2H4` → `ethylene`).",
                  "- El oxígeno se expresa como fracción molar cuando la columna o su unidad permiten identificarlo; porcentajes se dividen entre 100.",
                  "- La presión se expresa en kPa solo cuando se reconoce la unidad (atm, bar, mmHg, psi o kPa).",
                  "- Valores centinela (`-999`, `-9999`, `N/A`) y celdas sin valor numérico se convierten en nulos en las columnas numéricas normalizadas.",
                  "- Las reglas de contexto documentadas se marcan como inferencias en `inference_notes`; los valores explícitos del CSV tienen prioridad.", "",
                  "## Granularidad y excepciones", "",
                  "Cada fila maestra representa una fila de datos de origen. No se agregaron series temporales ni se mezclaron resúmenes con ensayos individuales.",
                  "Las tablas con naturaleza descriptiva conservan sus registros; los campos que no aplican permanecen vacíos.", "",
                  "## Cabeceras de origen y campos normalizados", "",
                  "Esta tabla relaciona cabeceras observadas con los campos canónicos. Las cabeceras sin equivalencia segura permanecen solo en el CSV original.", "",
                  "| Archivo | Cabecera de origen | Campo normalizado | Regla |", "|---|---|---|---|"]
        mappings = [
            (("Test", "Test#", "Test #", "SAME Test #", "Flex Test #", "Flex Number", "As Run Test #"), "test_id", "limpieza de espacios"),
            (("Test Date", "Date"), "test_date", "se conserva la fecha declarada"),
            (("Fuel", "Fuel Bottle", "Fuel Type", "Sample (Fuel Type)"), "fuel", "normalización de alias categórico"),
            (("Oxygen Mole Fraction", "XO2", "X_O2", "O2_conc", "Oxygen (%)", "Oxygen Conc (percent)", "Calibrated initial O2 % by vol", "O initial ambient composition; mole fraction", "Oxygen", "XO2 before test", "XO2 (init)", "XO2  after test", "XO2 (final)"), "oxygen_fraction", "porcentaje a fracción cuando la cabecera indica %"),
            (("pmean (atm)", "mean pressure (atm)", "ambient pressure (atm)", "pressure", "approx p (bar)", "ambient pressure; mmHg", "pressure (kpa)", "pressure (psi)", "pressure (bar)"), "pressure_kpa", "conversión a kPa cuando se reconoce la unidad"),
            (("Fuel Sample Material", "Sample Material", "Material", "Sample Type"), "material", "se conserva la categoría"),
        ]
        for relative in source_files:
            source_path = ROOT / relative
            source_df, _, _, _ = read_source_csv(source_path)
            source_headers = list(source_df.columns)
            for aliases, target_col, rule in mappings:
                source_col = _find_column(source_headers, aliases)
                if source_col:
                    lines.append(f"| `{relative}` | `{source_col}` | `{target_col}` | {rule} |")
        if investigation_id == "PSI-108":
            lines += ["", "PSI-108 tenía dos exportaciones coincidentes; se conserva la primera y se omite la copia `_1_` para no duplicar observaciones."]
        lines += ["", "## PDFs relacionados", "",
                  "El índice se encuentra en `data/processed/pdf_catalog.json`; el contenido de los PDF no se procesa.", ""]
        target.write_text("\n".join(lines), encoding="utf-8")


def build_master() -> pd.DataFrame:
    PROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    pdfs = _pdf_catalog()
    output: list[dict] = []
    source_files = sorted(RAW_ROOT.rglob("*.csv"))
    for path in source_files:
        if path.name.lower() in {"psi_download_manifest.csv", "manifest.csv"}:
            continue
        if "processed" in path.parts:
            continue
        data, metadata, header_index, _encoding = read_source_csv(path)
        if data.empty:
            continue
        investigation_match = re.search(r"PSI-\d+", path.as_posix(), re.I)
        investigation_id = investigation_match.group(0).upper() if investigation_match else ""
        columns = [column for column in data.columns if column != "__source_row"]
        relative_file = path.relative_to(ROOT).as_posix()
        file_stem = path.stem
        # Detect duplicate PSI-108 download copies. Keep the preferred first
        # copy and list the duplicate in its history document rather than
        # doubling the 38 repeated records.
        if investigation_id == "PSI-108" and "_1_" in path.stem:
            continue

        for _, row in data.iterrows():
            source_row = int(row["__source_row"])  # logical CSV record; header is record 1
            test_id = _value(row, columns, (
                "Test", "Test#", "Test #", "SAME Test #", "Flex Test #",
                "Flex Number", "As Run Test #",
            ))
            if not test_id:
                test_match = re.search(r"(?:^|[^a-z0-9])test[-_ ]?([a-z0-9]+)\b", path.stem, re.I)
                test_id = test_match.group(1) if test_match else ""
            if not test_id:
                test_id = _metadata_value(metadata, ("Test", "Test ID", "Run ID"))
            _, fuel = _fuel(row, columns, metadata, path.name)
            oxygen = _oxygen_fraction(row, columns)
            if oxygen is None:
                oxygen = _context_number(metadata, path.stem, "oxygen")
            pressure = _pressure_kpa(row, columns)
            if pressure is None:
                pressure = _context_number(metadata, path.stem, "pressure")
            date = _value(row, columns, ("Test Date", "Date"))
            if not date:
                date = _metadata_value(metadata, ("Test Date", "Date"))
            material = _value(row, columns, (
                "Material", "Sample Material", "Sample Type", "Fuel Sample Material",
            ))
            if not material:
                material = _metadata_value(metadata, ("Material", "Sample Material"))
            flame_type = _value(row, columns, ("Flame Type",))
            source_name = " ".join([path.name, path.parent.name]).lower()
            if "experimental table" in path.parent.name.lower():
                experiment_type = "experimental_table"
            else:
                experiment_type = path.parent.name.lower().replace(" ", "_")
            grain = "test_row" if test_id else "summary_or_descriptive_row"
            hardware = _value(row, columns, ("Hardware", "Hardware Description"))
            if not hardware:
                hardware = _metadata_value(metadata, ("Hardware", "Hardware Description"))
            inference_notes: list[str] = []
            # Apply the provided broad program rules only where they do not
            # overwrite source values or invent a more specific fuel.
            program = path.name.lower()
            if any(key in program for key in ("acme", "bre", "cfi-g", "e-field", "s-flame", "cld flame")):
                if not hardware:
                    hardware = "CIR"
                    inference_notes.append("hardware=CIR (regla de dominio ACME)")
            elif any(key in program for key in ("flex", "cfi")):
                if not hardware:
                    hardware = "MDCA (en CIR)"
                    inference_notes.append("hardware=MDCA (en CIR) (regla de dominio FLEX/CFI)")
            elif any(key in program for key in ("bass", "spice", "slice")):
                if not hardware:
                    hardware = "MSG (SPICE flow duct)"
                    inference_notes.append("hardware=MSG (regla de dominio BASS/SPICE/SLICE)")
            focus = ""
            if "saffire" in source_name:
                focus = "Solid materials flammability (gran escala)"
            elif "same" in source_name:
                focus = "Smoke and aerosol detection"
            elif "daft" in source_name:
                focus = "Dust detection (instrumentos SAME)"
            elif "acme" in source_name or "cfi-g" in source_name:
                focus = "Combustión gaseosa"
            if not fuel and any(key in program for key in ("acme", "bre", "cfi-g", "e-field", "s-flame", "cld flame")):
                fuel = "gaseous"
                inference_notes.append("fuel=gaseous (regla de dominio ACME)")

            fuel_class = ""
            if fuel in {"methane", "propane", "ethylene", "ethane", "n-dodecane", "gaseous"}:
                fuel_class = "gaseous"
            elif "flex" in program or re.search(r"\bcfi\b", program):
                fuel_class = "liquid droplet"
            elif material and any(word in material.lower() for word in ("pmma", "film", "sibal", "solid")):
                fuel_class = "solid"

            # Keep common direct measurements in explicit, unit-labelled fields.
            fuel_rate = _number(_value(row, columns, ("Fuel Rate (mg/s)", "HC Fuel Rate (mg/s)", "mFuel (mg/s)", "mHC (mg/s)")))
            air_rate = _number(_value(row, columns, ("Air Rate (cm/s)", "Air Flow (cm/s)", "Flow Velocity (cm/s)")))
            burn_time = _number(_value(row, columns, ("Burn time (sec)", "Burn time; s", "Burn time (s)")))
            duration = _number(_value(row, columns, ("Duration (sec)", "Duration (seconds)", "Test duration (sec)")))
            diameter = _number(_value(row, columns, ("Initial Droplet Diameter (mm)", "Droplet initial diameter; mm")))
            reference_paths = pdfs.get(investigation_id, [])
            output.append({
                "record_id": f"{investigation_id}:{path.stem}:{source_row}",
                "investigation_id": investigation_id,
                "investigation_name": file_stem,
                "experiment_type": experiment_type,
                "grain_type": grain,
                "source_file": relative_file,
                "source_row": source_row,
                "test_id": test_id,
                "test_date": date,
                "flame_type": flame_type,
                "fuel": fuel,
                "fuel_class": fuel_class,
                "material": material,
                "hardware": hardware,
                "focus": focus,
                "oxygen_fraction": oxygen,
                "pressure_kpa": pressure,
                "fuel_flow_mg_s": fuel_rate,
                "airflow_cm_s": air_rate,
                "droplet_initial_diameter_mm": diameter,
                "burn_time_s": burn_time,
                "duration_s": duration,
                "ignition_success": _ignition_success(row, columns),
                "inference_notes": "; ".join(inference_notes),
                "data_history_path": _history_path(investigation_id),
                "reference_pdf_path": ";".join(reference_paths),
            })

    frame = pd.DataFrame(output)
    if frame.empty:
        frame = pd.DataFrame(columns=[
            "record_id", "investigation_id", "investigation_name", "experiment_type", "grain_type",
            "source_file", "source_row", "test_id", "test_date", "flame_type", "fuel", "fuel_class",
            "material", "hardware", "focus", "oxygen_fraction",
            "pressure_kpa", "fuel_flow_mg_s", "airflow_cm_s",
            "droplet_initial_diameter_mm", "burn_time_s", "duration_s", "ignition_success",
            "inference_notes", "data_history_path", "reference_pdf_path",
        ])
    frame.to_csv(MASTER_PATH, index=False, encoding="utf-8")
    PDF_CATALOG_PATH.write_text(json.dumps(pdfs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    grouped: dict[str, list[dict]] = {}
    for record in output:
        grouped.setdefault(record["investigation_id"], []).append(record)
    _build_history_docs(grouped)
    return frame


def _matches(series: pd.Series, wanted: object, column: str) -> pd.Series:
    values = series.fillna("").astype(str)
    if isinstance(wanted, (list, tuple, set)):
        mask = pd.Series(False, index=series.index)
        for item in wanted:
            mask |= _matches(series, item, column)
        return mask
    target = str(wanted).strip()
    if column == "fuel":
        target = normalize_fuel(target)
        return values.map(normalize_fuel).eq(target)
    return values.str.casefold().eq(target.casefold())


def filter_for_dashboard(df: pd.DataFrame, **filters: object) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Filter the master and return (rows, chart columns, unique PDF paths).

    Filters are exact and case-insensitive except fuel, which recognizes
    aliases such as propane/C3H8/propano. Example: fuel="propane".
    """
    filtered = df.copy()
    aliases = {"fuel": "fuel", "investigation": "investigation_id", "study": "investigation_id"}
    for key, wanted in filters.items():
        column = aliases.get(key, key)
        if column not in filtered.columns:
            continue
        filtered = filtered.loc[_matches(filtered[column], wanted, column)]

    numeric_columns = [
        column for column in filtered.select_dtypes(include="number").columns
        if column not in {"source_row"} and filtered[column].notna().any()
    ]
    if len(filtered):
        completeness = filtered[numeric_columns].notna().mean().sort_values(ascending=False)
        recommended = completeness.index.tolist()
    else:
        recommended = []

    pdf_paths: set[str] = set()
    if "reference_pdf_path" in filtered.columns:
        for cell in filtered["reference_pdf_path"].dropna().astype(str):
            pdf_paths.update(path for path in cell.split(";") if path)
    return filtered.reset_index(drop=True), recommended, sorted(pdf_paths)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fuel", help="Guardar además una vista filtrada por combustible")
    args = parser.parse_args()
    master = build_master()
    if args.fuel:
        filtered, _, _ = filter_for_dashboard(master, fuel=args.fuel)
        target = PROCESSED_ROOT / f"experiments_fuel_{normalize_fuel(args.fuel).replace(' ', '_')}.csv"
        filtered.to_csv(target, index=False, encoding="utf-8")
        print(f"{len(filtered)} filas: {target.relative_to(ROOT)}")
    else:
        print(f"{len(master)} filas: {MASTER_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
