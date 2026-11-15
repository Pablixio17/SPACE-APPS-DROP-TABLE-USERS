#!/usr/bin/env python3
"""Combine NASA PSI experimental tables without discarding source-specific data."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

# Aliases are matched after trimming whitespace, removing a BOM, and folding case.
ALIASES = {
    "test_id": {"test", "test #", "test#", "same test #", "flex test #", "test number", "as run test #"},
    "fuel": {"fuel", "fuel bottle", "fuel type", "sample (fuel type)"},
    "material": {"fuel sample material", "sample material", "sample type"},
    "test_date": {"test date", "date", "gmt date"},
    "oxygen": {
        "xo2", "xo2 (init)", "oxygen", "oxygen mole fraction", "oxygen conc (percent)",
        "calibrated initial o2 % by vol", "o initial ambient composition; mole fraction",
        "xo2 before test", " xo2 before test",
    },
    "pressure": {"pressure", "ambient pressure (atm)", "ambient pressure; mmhg", "approx p (bar)", "pmean (atm)"},
    "airflow": {"air rate (cm/s)", "air flow (cm/s)", "inlet velocity (cm/s)", "flow velocity (cm/s)"},
}
OXYGEN_UNITS = {
    "oxygen conc (percent)": "%", "calibrated initial o2 % by vol": "%",
}
PRESSURE_UNITS = {
    "ambient pressure (atm)": "atm", "ambient pressure; mmhg": "mmHg",
    "approx p (bar)": "bar", "pmean (atm)": "atm",
}

OUTPUT_FIELDS = [
    "investigation_id", "investigation_name", "experiment_type", "source_file", "source_row",
    "test_id", "test_date", "fuel", "fuel_search", "material", "oxygen", "oxygen_unit",
    "pressure", "pressure_unit", "airflow", "airflow_unit", "source_data_json",
]


def clean_header(value: str) -> str:
    value = value.replace("\ufeff", "").strip()
    value = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", value).casefold()


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def normalize_fuel(value: str) -> str:
    """Make common fuel names searchable in Spanish and English, keeping other labels intact."""
    folded = slug(value).replace("₃", "3").replace("₈", "8")
    folded = folded.replace("c3h8", "propano (c3h8)").replace("propane", "propano")
    folded = folded.replace("c2h4", "etileno (c2h4)").replace("ethylene", "etileno")
    folded = folded.replace("c2h6", "etano (c2h6)").replace("ethane", "etano")
    folded = folded.replace("ch4", "metano (ch4)").replace("methane", "metano")
    return folded.strip()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    # NASA files include UTF-8 BOMs and at least one legacy Windows-1252 file.
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with path.open(encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                headers = [h or "" for h in (reader.fieldnames or [])]
                rows = []
                for row in reader:
                    rows.append({(k or "").replace("\ufeff", "").strip(): text(v) for k, v in row.items() if k is not None})
                return headers, rows
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"No se pudo decodificar {path}")


def value_for(row: dict[str, str], headers: list[str], canonical: str) -> tuple[str, str]:
    aliases = ALIASES.get(canonical, set())
    for header in headers:
        if clean_header(header) in aliases and text(row.get(header)):
            return text(row[header]), header
    return "", ""


def make_row(path: Path, headers: list[str], row: dict[str, str], row_num: int) -> dict[str, str]:
    investigation_id = path.parts[-3]
    fuel, _ = value_for(row, headers, "fuel")
    material, _ = value_for(row, headers, "material")
    oxygen, oxygen_header = value_for(row, headers, "oxygen")
    pressure, pressure_header = value_for(row, headers, "pressure")
    airflow, airflow_header = value_for(row, headers, "airflow")
    test_id, _ = value_for(row, headers, "test_id")
    test_date, _ = value_for(row, headers, "test_date")

    # Preserve exact field names and values so later study-specific work can recover every column.
    source_json = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
    return {
        "investigation_id": investigation_id,
        "investigation_name": path.stem,
        "experiment_type": path.parent.name,
        "source_file": path.relative_to(ROOT).as_posix(),
        "source_row": str(row_num),
        "test_id": test_id,
        "test_date": test_date,
        "fuel": fuel,
        "fuel_search": normalize_fuel(fuel),
        "material": material,
        "oxygen": oxygen,
        "oxygen_unit": OXYGEN_UNITS.get(clean_header(oxygen_header), ""),
        "pressure": pressure,
        "pressure_unit": PRESSURE_UNITS.get(clean_header(pressure_header), ""),
        "airflow": airflow,
        "airflow_unit": "cm/s" if airflow else "",
        "source_data_json": source_json,
    }


def pdf_catalog() -> list[dict[str, str]]:
    return [
        {"investigation_id": next((part for part in path.parts if re.fullmatch(r"PSI-\d+", part)), ""), "file_name": path.name,
         "relative_path": path.relative_to(ROOT).as_posix()}
        for path in sorted(RAW.rglob("*.pdf"), key=lambda p: p.as_posix().casefold())
    ]


def build(fuel_filter: str = "") -> tuple[int, int]:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = sorted((p for p in RAW.rglob("*.csv") if "manifest" not in p.name.casefold()), key=lambda p: p.as_posix().casefold())
    all_rows: list[dict[str, str]] = []
    for path in sources:
        headers, rows = read_csv(path)
        for row_num, row in enumerate(rows, start=2):
            all_rows.append(make_row(path, headers, row, row_num))

    query = slug(fuel_filter)
    chosen = all_rows if not query else [r for r in all_rows if query in r["fuel_search"]]
    target = OUT / ("experiments.csv" if not query else f"experiments_fuel_{re.sub(r'[^a-z0-9]+', '_', query).strip('_')}.csv")
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(chosen)

    (OUT / "pdf_catalog.json").write_text(json.dumps(pdf_catalog(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(sources), len(chosen)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fuel", default="", help="Filtro parcial de combustible (ej.: propano, propane, C3H8)")
    args = parser.parse_args()
    source_count, row_count = build(args.fuel)
    output = "experiments.csv" if not args.fuel else f"experiments_fuel_{re.sub(r'[^a-z0-9]+', '_', slug(args.fuel)).strip('_')}.csv"
    print(f"{source_count} tablas combinadas; {row_count} filas -> data/processed/{output}")
    print(f"Catálogo de PDF (sin procesar): data/processed/pdf_catalog.json")


if __name__ == "__main__":
    main()
