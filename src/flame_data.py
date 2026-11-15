"""Read-only data and evidence layer for Flame in Freefall.

Curated strings are retained for exact exports. Typed analysis never fills
missing measurements from study bounds, archive records or document text.
"""

from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unicodedata
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CSV_PATH = DATA / "processed" / "experiments.csv"
PACKAGE_PATH = DATA / "processed" / "PROJECT_MASTER_PACKAGE.zip"

METRICS = {
    "oxygen_pct": "Oxygen · %",
    "pressure_psi": "Absolute pressure · psia",
    "pressure_kpa": "Absolute pressure · kPa",
    "ppo2_psi": "O₂ partial pressure · psi",
    "fuel_flow_mg_s": "Fuel flow rate · mg/s",
    "airflow_cm_s": "Airflow velocity · cm/s",
    "droplet_initial_diameter_mm": "Initial diameter · mm",
    "burn_time_s": "Burn time · s",
    "duration_s": "Duration · s",
    "irl_score": "Legacy IRL · points",
}
LABELS = {
    **METRICS,
    "record_id": "Record ID",
    "investigation_id": "Investigation",
    "investigation_name": "Source name",
    "experiment_type": "Experiment type",
    "grain_type": "Granularity",
    "source_file": "Source file",
    "source_row": "Source row",
    "test_id": "Test ID",
    "test_date": "Test date",
    "flame_type": "Flame type",
    "fuel": "Fuel",
    "fuel_class": "Fuel class",
    "material": "Material / specimen",
    "hardware": "Hardware",
    "focus": "Study focus",
    "oxygen_fraction": "Oxygen fraction",
    "ignition_success": "Ignition outcome",
    "inference_notes": "Inference notes",
    "data_history_path": "Data history",
    "reference_pdf_path": "Reference PDF",
    "source_encoding": "Source encoding",
    "source_values_json": "Original values",
    "source_files": "Source files",
    "merge_status": "Integration status",
    "merge_conflicts_json": "Integration conflicts",
    "record_scope": "Record scope",
    "test_uid": "Composite test identifier",
    "duplicate_of_record_id": "Duplicate of",
    "pressure_atm": "Pressure · atm",
    "oxygen_fraction_min": "Minimum O₂ fraction",
    "oxygen_fraction_max": "Maximum O₂ fraction",
    "pressure_kpa_min": "Minimum pressure · kPa",
    "pressure_kpa_max": "Maximum pressure · kPa",
    "droplet_initial_diameter_mm_min": "Minimum diameter · mm",
    "droplet_initial_diameter_mm_max": "Maximum diameter · mm",
    "airflow_cm_s_min": "Minimum airflow · cm/s",
    "airflow_cm_s_max": "Maximum airflow · cm/s",
    "is_lunar_atmosphere": "Source lunar indicator",
    "is_combustion_core": "Combustion core",
    "exclusion_reason": "Exclusion reason",
    "study_environment": "Environment",
    "gravity_regime": "Gravity regime",
    "partial_gravity_emulation": "Partial gravity emulation",
    "gravity_interpolation_index": "Interpolation index",
    "gravity_interpolation_status": "Interpolation status",
    "safety_pillar": "Research pillar",
    "material_category": "Material family",
    "flow_regime": "Flow regime",
    "visual_phenomena": "Visual phenomenon",
    "linked_investigation_ids": "Related studies",
    "available_linked_investigation_ids": "Available links",
    "missing_linked_investigation_ids": "Pending links",
    "doi": "Reference / DOI",
    "pdf_reference_count": "PDF references",
    "s_atm": "IRL atmospheric component",
    "s_seg": "IRL safety component",
    "s_grav": "IRL gravity component",
    "s_mat": "IRL material component",
    "irl_status": "IRL status",
    "irl_component_coverage": "IRL coverage",
    "include_in_safety_ranking": "Source ranking inclusion",
    "scoring_basis_json": "IRL criteria",
    "study_pressure_min_atm": "Study minimum pressure · atm",
    "study_pressure_max_atm": "Study maximum pressure · atm",
    "study_oxygen_min_pct": "Study minimum O₂ · %",
    "study_oxygen_max_pct": "Study maximum O₂ · %",
    "data_quality_flags": "Quality flags",
    "numeric_details_json": "Normalization details",
    "field_provenance_json": "Field provenance",
    "rules_version": "Rules version",
    "acronym": "Program",
    "traffic_light": "Legacy traffic light",
    "safety_pillar_detail": "Detailed pillar",
    "doi_status": "Reference status",
    "earth_spin_off": "Source Earth spin-off",
    "study_pressure_min_psi": "Study minimum pressure · psi",
    "study_pressure_max_psi": "Study maximum pressure · psi",
    "study_covers_lunar_envelope": "Declared lunar coverage",
    "safety_alert_banner": "Source alert",
    "scope_label": "Record scope",
    "ignition_label": "Ignition",
    "quality_label": "Recorded quality",
    "study_label": "Study",
    "count": "Records",
    "pillar_label": "Research pillar",
}
VALUES = {
    "test": "Test",
    "test_observation": "Observation",
    "study_summary": "Study summary",
    "microgravity_context": "Microgravity",
    "ground_context": "Ground reference",
    "gas": "Gas",
    "solid": "Solid",
    "liquid": "Liquid",
    "spaceflight": "Spaceflight",
    "ground": "Ground",
    "prevention": "Prevention",
    "suppression": "Suppression",
    "detection": "Detection",
    "soot_and_flame_design": "Soot and flame design",
    "cfd_modeling_validation": "CFD validation",
    "fundamental_cfd_calibration": "CFD calibration",
    "partial_gravity_proxy": "Electric forcing / proxy",
    "cool_flame_chemistry": "Cool flame chemistry",
    "forced": "Forced flow",
    "quiescent": "Quiescent",
    "polymer": "Polymer",
    "textile": "Textile",
    "foam": "Foam",
    "wax": "Wax",
    "GREEN": "Green · source classification",
    "AMBER": "Amber · source classification",
    "document_report": "Documentary synthesis",
    "dataset_assessment": "Dataset assessment",
    "related_document_context": "Related documentary context",
}
INSIGHTS = {
    "PSI-10": (
        "The report describes radiative extinction and stability under specific"
        " ethylene conditions. It compares normal and inverse flames without"
        " turning overall study bounds into individual test conditions."
    ),
    "PSI-20": (
        "The report describes sustained combustion without imposed flow under"
        " elevated oxygen. Records are summaries of a burner emulating condensed"
        " fuels; they do not certify materials."
    ),
    "PSI-21": (
        "These are study summaries. Some chemical formulas are flagged as"
        " unrecognized; verify labels before comparing fuels. No direct PDF"
        " is included in this package."
    ),
    "PSI-22": (
        "The electric field modifies transport and voltage-current curves."
        " The report does not establish a calibrated equivalence with 0.16 g"
        " lunar gravity."
    ),
    "PSI-23": (
        "The report describes radiative extinction and leaves certain low-flow"
        " mechanisms unresolved: chemical kinetics or heat loss to the burner."
    ),
    "PSI-25": (
        "Allows comparing specimens, geometries, and ventilation. It contains"
        " neither ignition outcomes nor a direct PDF to infer an overall"
        " safety classification."
    ),
    "PSI-26": (
        "For thin fuels on the cited page, flame spread depends on flow"
        " direction. Keep tests, observations, and study summaries separate."
    ),
    "PSI-39": (
        "The report investigates droplets, extinction, and radiation across"
        " multiple fuels. The curated subset only lists n-dodecane and does not"
        " represent the full coverage of the report."
    ),
    "PSI-47": (
        "DAFT provides context on aerosol instrumentation feasibility. Its"
        " historical records do not belong to the curated combustion CSV."
    ),
    "PSI-68": (
        "Its summaries contain ranges and sets. Do not combine extreme bounds"
        " to fabricate a tested condition or a scalar extinction metric."
    ),
    "PSI-69": (
        "Heptane and methanol records organize droplet conditions. Without"
        " ignition outcomes or a direct PDF, they cannot establish a general"
        " suppression threshold."
    ),
    "PSI-101": (
        "Organizes smoke studies for Kapton, Lampwick, Pyrell, silicone, and"
        " Teflon. Observations are not additional tests and do not prove"
        " detector performance."
    ),
    "PSI-102": (
        "SAME summaries provide indirect context for PSI-115 models. Those"
        " simulations are not measurements of the eight rows in the study."
    ),
    "PSI-106": (
        "Summaries delimit SLICE coverage. There is no direct PDF supporting a"
        " numerical threshold for flame stability or lift-off."
    ),
    "PSI-107": (
        "SPICE contains multiple observations per test and timing alerts."
        " Resolve quality flags before interpreting durations; row count does"
        " not equal independent experiments."
    ),
    "PSI-108": (
        "Historical fluid physics context, excluded from the combustion core"
        " and absent from the curated CSV. Not included in experimental plots."
    ),
    "PSI-115": (
        "The report models larger smoke particles in microgravity for the"
        " compared configurations. Results depend on material and geometry;"
        " there are no curated experimental rows."
    ),
    "PSI-142": (
        "Ground reference for FLEX comparisons. Paired observations and a"
        " gravity model are missing; its links cannot predict lunar outcomes."
    ),
    "PSI-159": (
        "The report documents cool flames in a restricted n-butane"
        " configuration. CSV ignition success alone does not identify a cool"
        " flame."
    ),
}


def label(value: str) -> str:
    return LABELS.get(value, VALUES.get(value, value.replace("_", " ")))


def signature(path: Path) -> tuple:
    return (
        (str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size)
        if path.exists()
        else (str(path), None, None)
    )


def prepare_database(
    package: Path = PACKAGE_PATH, cache_dir: Path | None = None
) -> Path:
    """Extract only the named database atomically; never execute packaged scripts."""
    cache_dir = cache_dir or ROOT / ".cache" / "flame"
    cache_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read("PROJECT_MASTER/MANIFEST.json"))
        entry = next(
            x
            for x in manifest["files"]
            if x["name"] == "PROJECT_MASTER.sqlite"
        )
        target = cache_dir / (entry["sha256"] + ".sqlite")
        if target.exists() and target.stat().st_size == entry["size_bytes"]:
            return target
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=cache_dir, suffix=".tmp", delete=False
            ) as out:
                temporary = Path(out.name)
                digest = hashlib.sha256()
                with archive.open(
                    "PROJECT_MASTER/PROJECT_MASTER.sqlite"
                ) as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                        out.write(chunk)
            if digest.hexdigest() != entry["sha256"]:
                raise ValueError(
                    "The documentary database does not match its SHA-256 manifest."
                )
            temporary.replace(target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return target


def connect(database: Path):
    connection = sqlite3.connect(
        database.resolve().as_uri() + "?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    return connection


def load_metadata(database: Path) -> tuple[list[dict], list[dict]]:
    with closing(connect(database)) as db:
        projects = [
            json.loads(r[0])
            for r in db.execute("SELECT summary_json FROM project_summaries")
        ]
        fields = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM field_dictionary ORDER BY position"
            )
        ]
    return (
        sorted(
            projects, key=lambda p: int(p["investigation_id"].split("-")[1])
        ),
        fields,
    )


def load_records(
    path: Path = CSV_PATH, fields: list[dict] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(
        path, dtype=str, keep_default_na=False, encoding="utf-8-sig"
    )
    required = {
        "record_id",
        "investigation_id",
        "record_scope",
        "oxygen_pct",
        "pressure_psi",
        "data_quality_flags",
    }
    if not required.issubset(raw.columns):
        raise ValueError(
            "The CSV is missing required fields: "
            + ", ".join(sorted(required - set(raw.columns)))
        )
    if raw.record_id.duplicated().any():
        raise ValueError(
            "The CSV contains duplicate record_id values. Check the source"
            " before analyzing."
        )
    df = raw.copy()
    for field in fields or []:
        name = field["field"]
        if name not in df:
            continue
        if field["type"] == "number":
            df[name] = pd.to_numeric(df[name], errors="coerce")
        elif field["type"] == "boolean":
            df[name] = (
                df[name]
                .str.lower()
                .map({"true": True, "false": False})
                .astype("boolean")
            )
    # Also works without the optional documentary package.
    for name in METRICS:
        df[name] = pd.to_numeric(df[name], errors="coerce")
    df["scope_label"] = df.record_scope.map(VALUES).fillna(df.record_scope)
    df["study_label"] = df.investigation_id + " · " + df.acronym
    df["pillar_label"] = df.safety_pillar.map(VALUES).fillna(df.safety_pillar)
    df["ignition_label"] = (
        raw.ignition_success.str.lower()
        .map({"true": "Success", "false": "Failure"})
        .fillna("No data")
    )
    df["quality_label"] = df.data_quality_flags.ne("").map(
        {True: "With flags", False: "No flags recorded"}
    )
    # This is a scenario membership test, not a safety verdict or gravity measurement.
    df["scenario_lunar"] = (
        df.pressure_psi.gt(0)
        & df.pressure_psi.le(10.2)
        & df.oxygen_pct.ge(30)
        & df.oxygen_pct.le(100)
    )
    return raw, df


def filter_records(
    df: pd.DataFrame,
    categories: dict | None = None,
    text: str = "",
    lunar: bool = False,
    numeric: dict | None = None,
    keep_missing: bool = True,
) -> pd.DataFrame:
    out = df.copy()
    for column, selected in (categories or {}).items():
        if selected:
            out = out[out[column].isin(selected)]
    if text.strip():
        columns = [
            "record_id",
            "test_id",
            "acronym",
            "fuel",
            "material",
            "hardware",
            "visual_phenomena",
        ]
        searchable = (
            out[columns]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .str.casefold()
        )
        for token in text.casefold().split():
            out = out[
                searchable.loc[out.index].str.contains(token, regex=False)
            ]
    if lunar:
        out = out[out.scenario_lunar]
    for column, (low, high) in (numeric or {}).items():
        mask = out[column].between(low, high)
        if keep_missing:
            mask |= out[column].isna()
        out = out[mask]
    return out.copy()


def scalar_records(
    df: pd.DataFrame, x: str, y: str, include_summaries: bool = False
) -> pd.DataFrame:
    out = df.dropna(subset=[x, y]).copy()
    if not include_summaries:
        out = out[out.record_scope != "study_summary"]
    for name in {x, y}:
        if name in {
            "pressure_psi",
            "pressure_kpa",
            "ppo2_psi",
            "droplet_initial_diameter_mm",
        }:
            out = out[out[name] > 0]
        if name == "oxygen_pct":
            out = out[out[name].between(0, 100)]
        if name in {"burn_time_s", "duration_s"}:
            out = out[
                (out[name] >= 0)
                & ~out.data_quality_flags.str.contains(
                    "invalid_ignition_time|ambiguous_midnight_duration",
                    regex=True,
                )
            ]
    return out


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["study_label", "scope_label"], sort=True)
        .size()
        .rename("count")
        .reset_index()
    )


def search_evidence(
    database: Path, query: str, project: dict | None = None, limit: int = 8
) -> list[dict]:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)
    if not tokens:
        return []
    match = " AND ".join('"' + t + '"' for t in tokens[:20])
    sql = """SELECT k.doc_id, p.page_number, k.text, k.citation_json, p.method,
             p.quality_flags_json FROM search JOIN chunks k ON search.chunk_id=k.chunk_id
             JOIN pages p ON p.page_id=k.page_id WHERE search MATCH ?"""
    args = [match]
    if project is not None:
        docids = sorted(
            set(
                project["direct_document_ids"]
                + project["related_document_ids"]
            )
        )
        if not docids:
            return []
        sql += " AND k.doc_id IN (" + ",".join("?" for _ in docids) + ")"
        args.extend(docids)
    sql += " ORDER BY rank LIMIT ?"
    args.append(min(max(limit, 1), 30))
    with closing(connect(database)) as db:
        return [dict(r) for r in db.execute(sql, args)]


def evidence_page(database: Path, page_id: str) -> dict:
    with closing(connect(database)) as db:
        row = db.execute(
            "SELECT * FROM pages WHERE page_id=?", (page_id,)
        ).fetchone()
        return dict(row) if row else {}


def record_differences(database: Path, record_id: str) -> list[dict]:
    with closing(connect(database)) as db:
        return [
            dict(r)
            for r in db.execute(
                "SELECT field,preferred_json,archive_json,resolution FROM"
                " source_differences WHERE record_id=?",
                (record_id,),
            )
        ]


def archive_records(database: Path, investigation_id: str) -> list[dict]:
    with closing(connect(database)) as db:
        return [
            json.loads(r[0])
            for r in db.execute(
                "SELECT record_json FROM supplementary_records WHERE"
                " investigation_id=?",
                (investigation_id,),
            )
        ]


def normalize(text: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(c)
    )


def interpret_request(
    query: str, df: pd.DataFrame
) -> tuple[pd.DataFrame, str, list[str]]:
    """Bounded, transparent local intent matching; never claims unrestricted NLP."""
    q = normalize(query)
    out = df.copy()
    notes = []
    ids = {"PSI-" + n for n in re.findall(r"\bpsi[- ]?(\d+)\b", q)}
    families = {
        "flex": ["PSI-68", "PSI-69", "PSI-142"],
        "bass": ["PSI-25", "PSI-26"],
        "same": ["PSI-101", "PSI-102"],
        "spice": ["PSI-107"],
        "cfi": ["PSI-39", "PSI-159"],
        "saffire": ["PSI-98", "PSI-99", "PSI-100"],
    }
    if not ids:
        for word, matches in families.items():
            if re.search(r"\b" + word + r"\b", q):
                ids.update(matches)
    if ids:
        out = out[out.investigation_id.isin(ids)]
        notes.append("Studies: " + ", ".join(sorted(ids)))
    mode = "Atmosphere"
    for words, result in [
        (("material", "solid", "specimen"), "Materials"),
        (("compar", "coverage", "studies"), "Comparison"),
        (("ignition", "ignit", "success", "failure"), "Ignition"),
        (("quality", "missing", "absent", "gap"), "Quality"),
    ]:
        if any(word in q for word in words):
            mode = result
    if "lunar" in q or "moon" in q:
        out = out[out.scenario_lunar]
        notes.append(
            "Scenario: P ≤ 10.2 psia and O₂ ≥ 30%; does not imply lunar gravity."
        )
    if "microgravity" in q:
        out = out[out.gravity_regime == "microgravity_context"]
        notes.append("Context: microgravity")
    for fuel in ["methane", "ethylene", "heptane", "methanol", "butane"]:
        if fuel in q:
            out = out[out.fuel.str.contains(fuel, case=False, regex=False)]
            notes.append("Fuel: " + fuel)
    notes.append("Suggested view: " + mode)
    recognized = len(notes) > 1 or any(
        w in q
        for w in [
            "atmosphere",
            "oxygen",
            "pressure",
            "material",
            "compar",
            "ignition",
            "quality",
            "coverage",
            "gap",
        ]
    )
    if not recognized:
        notes.append(
            "Request not fully recognized. Use axis controls and filters to"
            " refine it."
        )
    if "cool" in q:
        notes.append(
            "Cool flames are referenced in documentary evidence; they are not"
            " inferred from ignition outcome."
        )
    return out, mode, notes
