"""Read-only data and evidence layer for Flame in Freefall.

Curated strings are retained for exact exports. Typed analysis never fills missing
measurements from study bounds, archive records or document text.
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
DATA = ROOT / "data" / "Done DATA f_project"
CSV_PATH = DATA / "CSV DE LOS DATOS PERFECTAMENTE ORDENADOS.csv"
PACKAGE_PATH = DATA / "PROJECT_MASTER_PACKAGE.zip"

METRICS = {
    "oxygen_pct": "Oxígeno · %", "pressure_psi": "Presión absoluta · psia",
    "pressure_kpa": "Presión absoluta · kPa", "ppo2_psi": "Presión parcial O₂ · psi",
    "fuel_flow_mg_s": "Caudal de combustible · mg/s", "airflow_cm_s": "Velocidad del aire · cm/s",
    "droplet_initial_diameter_mm": "Diámetro inicial · mm", "burn_time_s": "Tiempo de combustión · s",
    "duration_s": "Duración · s", "irl_score": "IRL heredado · puntos",
}
LABELS = {
    **METRICS, "record_id": "ID del registro", "investigation_id": "Investigación",
    "investigation_name": "Nombre de origen", "experiment_type": "Tipo de experimento",
    "grain_type": "Granularidad", "source_file": "Archivo de origen", "source_row": "Fila de origen",
    "test_id": "ID del ensayo", "test_date": "Fecha del ensayo", "flame_type": "Tipo de llama",
    "fuel": "Combustible", "fuel_class": "Clase de combustible", "material": "Material / probeta",
    "hardware": "Equipo", "focus": "Objeto de estudio", "oxygen_fraction": "Fracción de oxígeno",
    "ignition_success": "Resultado de ignición", "inference_notes": "Notas de inferencia",
    "data_history_path": "Historial de datos", "reference_pdf_path": "PDF de referencia",
    "source_encoding": "Codificación de origen", "source_values_json": "Valores originales",
    "source_files": "Archivos de origen", "merge_status": "Estado de integración",
    "merge_conflicts_json": "Conflictos de integración", "record_scope": "Tipo de registro",
    "test_uid": "Identificador de ensayo compuesto", "duplicate_of_record_id": "Duplicado de",
    "pressure_atm": "Presión · atm", "oxygen_fraction_min": "Fracción O₂ mínima",
    "oxygen_fraction_max": "Fracción O₂ máxima", "pressure_kpa_min": "Presión mínima · kPa",
    "pressure_kpa_max": "Presión máxima · kPa", "droplet_initial_diameter_mm_min": "Diámetro mínimo · mm",
    "droplet_initial_diameter_mm_max": "Diámetro máximo · mm", "airflow_cm_s_min": "Aire mínimo · cm/s",
    "airflow_cm_s_max": "Aire máximo · cm/s", "is_lunar_atmosphere": "Indicador lunar de origen",
    "is_combustion_core": "Núcleo de combustión", "exclusion_reason": "Motivo de exclusión",
    "study_environment": "Entorno", "gravity_regime": "Contexto gravitatorio",
    "partial_gravity_emulation": "Emulación de gravedad parcial", "gravity_interpolation_index": "Índice de interpolación",
    "gravity_interpolation_status": "Estado de interpolación", "safety_pillar": "Área de investigación",
    "material_category": "Familia de material", "flow_regime": "Régimen de flujo",
    "visual_phenomena": "Fenómeno visual", "linked_investigation_ids": "Estudios relacionados",
    "available_linked_investigation_ids": "Relaciones disponibles", "missing_linked_investigation_ids": "Relaciones pendientes",
    "doi": "Referencia / DOI", "pdf_reference_count": "Referencias PDF", "s_atm": "Componente atmosférico IRL",
    "s_seg": "Componente de seguridad IRL", "s_grav": "Componente gravitatorio IRL", "s_mat": "Componente material IRL",
    "irl_status": "Estado del IRL", "irl_component_coverage": "Cobertura del IRL",
    "include_in_safety_ranking": "Inclusión en ranking de origen", "scoring_basis_json": "Criterios del IRL",
    "study_pressure_min_atm": "Presión mínima del estudio · atm", "study_pressure_max_atm": "Presión máxima del estudio · atm",
    "study_oxygen_min_pct": "O₂ mínimo del estudio · %", "study_oxygen_max_pct": "O₂ máximo del estudio · %",
    "data_quality_flags": "Incidencias de calidad", "numeric_details_json": "Detalle de normalización",
    "field_provenance_json": "Procedencia por campo", "rules_version": "Versión de reglas",
    "acronym": "Programa", "traffic_light": "Semáforo heredado", "safety_pillar_detail": "Área detallada",
    "doi_status": "Estado de la referencia", "earth_spin_off": "Aplicación terrestre de origen",
    "study_pressure_min_psi": "Presión mínima del estudio · psi", "study_pressure_max_psi": "Presión máxima del estudio · psi",
    "study_covers_lunar_envelope": "Cobertura lunar declarada", "safety_alert_banner": "Aviso de origen",
    "scope_label": "Tipo de registro", "ignition_label": "Ignición", "quality_label": "Calidad registrada",
    "study_label": "Estudio", "count": "Registros", "pillar_label": "Área de investigación",
}
VALUES = {
    "test": "Ensayo", "test_observation": "Observación", "study_summary": "Resumen de estudio",
    "microgravity_context": "Microgravedad", "ground_context": "Referencia terrestre",
    "gas": "Gas", "solid": "Sólido", "liquid": "Líquido", "spaceflight": "Vuelo espacial", "ground": "Tierra",
    "prevention": "Prevención", "suppression": "Supresión", "detection": "Detección",
    "soot_and_flame_design": "Hollín y diseño de llama", "cfd_modeling_validation": "Validación CFD",
    "fundamental_cfd_calibration": "Calibración CFD", "partial_gravity_proxy": "Forzado eléctrico / proxy",
    "cool_flame_chemistry": "Química de llamas frías", "forced": "Flujo forzado", "quiescent": "En reposo",
    "polymer": "Polímero", "textile": "Textil", "foam": "Espuma", "wax": "Cera",
    "GREEN": "Verde · clasificación de origen", "AMBER": "Ámbar · clasificación de origen",
    "document_report": "Síntesis documental", "dataset_assessment": "Evaluación del dataset",
    "related_document_context": "Contexto documental relacionado",
}
INSIGHTS = {
    "PSI-10": "El informe describe extinción radiativa y estabilidad bajo determinadas condiciones de etileno. Compara llamas normales e inversas sin convertir los límites generales del estudio en condiciones de cada ensayo.",
    "PSI-20": "El informe describe combustión sostenida sin flujo impuesto con oxígeno elevado. Los registros son resúmenes de un quemador que emula combustibles condensados; no certifican materiales.",
    "PSI-21": "Son resúmenes de estudio. Hay fórmulas químicas señaladas como no reconocidas; revisa las etiquetas antes de comparar combustibles. No hay PDF directo en este paquete.",
    "PSI-22": "El campo eléctrico modifica el transporte y las curvas tensión-corriente. El informe no establece una equivalencia calibrada con la gravedad lunar de 0,16 g.",
    "PSI-23": "El informe describe extinción radiativa y deja sin resolver algunos mecanismos a bajo caudal: cinética química o pérdida de calor al quemador.",
    "PSI-25": "Permite comparar probetas, geometrías y ventilación. No contiene resultados de ignición ni PDF directo para deducir una clasificación general de seguridad.",
    "PSI-26": "En los combustibles delgados de la página citada, la propagación depende de la dirección del flujo. Conserva separados los ensayos, las observaciones y el resumen.",
    "PSI-39": "El informe estudia gotas, extinción y radiación con varios combustibles. El subconjunto curado solo lista n-dodecano y no representa toda la cobertura del informe.",
    "PSI-47": "DAFT aporta contexto sobre viabilidad instrumental de aerosoles. Sus registros históricos no pertenecen al CSV curado de combustión.",
    "PSI-68": "Sus resúmenes contienen rangos y conjuntos. No combines sus extremos para inventar una condición ensayada ni una medida escalar de extinción.",
    "PSI-69": "Los registros de heptano y metanol organizan condiciones de gotas. Sin resultados de ignición ni PDF directo, no permiten deducir un umbral general de supresión.",
    "PSI-101": "Organiza estudios de humo para Kapton, Lampwick, Pyrell, silicona y Teflon. Las observaciones no son ensayos adicionales y no demuestran el rendimiento de un detector.",
    "PSI-102": "Los resúmenes SAME tienen contexto indirecto en los modelos de PSI-115. Esas simulaciones no son mediciones de las ocho filas del estudio.",
    "PSI-106": "Los resúmenes delimitan la cobertura de SLICE. No hay PDF directo que sustente un umbral numérico de estabilidad o separación de llama.",
    "PSI-107": "SPICE contiene muchas observaciones por ensayo y alertas en los tiempos. Resuelve las incidencias antes de interpretar duraciones; el número de filas no equivale a experimentos independientes.",
    "PSI-108": "Contexto histórico de física de fluidos, excluido del núcleo de combustión y ausente del CSV curado. No se incorpora a las gráficas experimentales.",
    "PSI-115": "El informe modela partículas de humo mayores en microgravedad para las configuraciones comparadas. El resultado depende del material y la geometría; no hay filas experimentales curadas.",
    "PSI-142": "Referencia terrestre para comparaciones con FLEX. Faltan observaciones emparejadas y un modelo gravitatorio; sus vínculos no permiten predecir resultados lunares.",
    "PSI-159": "El informe documenta llamas frías en una configuración restringida de n-butano. El éxito de ignición del CSV no identifica por sí mismo una llama fría.",
}

def label(value: str) -> str:
    return LABELS.get(value, VALUES.get(value, value.replace("_", " ")))

def signature(path: Path) -> tuple:
    return (str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size) if path.exists() else (str(path), None, None)

def prepare_database(package: Path = PACKAGE_PATH, cache_dir: Path | None = None) -> Path:
    """Extract only the named database atomically; never execute packaged scripts."""
    cache_dir = cache_dir or ROOT / ".cache" / "flame"
    cache_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read("PROJECT_MASTER/MANIFEST.json"))
        entry = next(x for x in manifest["files"] if x["name"] == "PROJECT_MASTER.sqlite")
        target = cache_dir / (entry["sha256"] + ".sqlite")
        if target.exists() and target.stat().st_size == entry["size_bytes"]:
            return target
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=cache_dir, suffix=".tmp", delete=False) as out:
                temporary = Path(out.name)
                digest = hashlib.sha256()
                with archive.open("PROJECT_MASTER/PROJECT_MASTER.sqlite") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                        out.write(chunk)
            if digest.hexdigest() != entry["sha256"]:
                raise ValueError("La base documental no coincide con su manifiesto SHA-256.")
            temporary.replace(target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return target

def connect(database: Path):
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection

def load_metadata(database: Path) -> tuple[list[dict], list[dict]]:
    with closing(connect(database)) as db:
        projects = [json.loads(r[0]) for r in db.execute("SELECT summary_json FROM project_summaries")]
        fields = [dict(r) for r in db.execute("SELECT * FROM field_dictionary ORDER BY position")]
    return sorted(projects, key=lambda p: int(p["investigation_id"].split("-")[1])), fields

def load_records(path: Path = CSV_PATH, fields: list[dict] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    required = {"record_id", "investigation_id", "record_scope", "oxygen_pct", "pressure_psi", "data_quality_flags"}
    if not required.issubset(raw.columns):
        raise ValueError("El CSV no contiene los campos requeridos: " + ", ".join(sorted(required - set(raw.columns))))
    if raw.record_id.duplicated().any():
        raise ValueError("El CSV contiene record_id duplicados. Revisa el origen antes de analizarlo.")
    df = raw.copy()
    for field in fields or []:
        name = field["field"]
        if name not in df:
            continue
        if field["type"] == "number":
            df[name] = pd.to_numeric(df[name], errors="coerce")
        elif field["type"] == "boolean":
            df[name] = df[name].str.lower().map({"true": True, "false": False}).astype("boolean")
    # Also works without the optional documentary package.
    for name in METRICS:
        df[name] = pd.to_numeric(df[name], errors="coerce")
    df["scope_label"] = df.record_scope.map(VALUES).fillna(df.record_scope)
    df["study_label"] = df.investigation_id + " · " + df.acronym
    df["pillar_label"] = df.safety_pillar.map(VALUES).fillna(df.safety_pillar)
    df["ignition_label"] = raw.ignition_success.str.lower().map({"true": "Éxito", "false": "Fallo"}).fillna("Sin dato")
    df["quality_label"] = df.data_quality_flags.ne("").map({True: "Con incidencias", False: "Sin incidencias registradas"})
    # This is a scenario membership test, not a safety verdict or gravity measurement.
    df["scenario_lunar"] = df.pressure_psi.gt(0) & df.pressure_psi.le(10.2) & df.oxygen_pct.ge(30) & df.oxygen_pct.le(100)
    return raw, df

def filter_records(df: pd.DataFrame, categories: dict | None = None, text: str = "", lunar: bool = False,
                   numeric: dict | None = None, keep_missing: bool = True) -> pd.DataFrame:
    out = df.copy()
    for column, selected in (categories or {}).items():
        if selected:
            out = out[out[column].isin(selected)]
    if text.strip():
        columns = ["record_id", "test_id", "acronym", "fuel", "material", "hardware", "visual_phenomena"]
        searchable = out[columns].fillna("").astype(str).agg(" ".join, axis=1).str.casefold()
        for token in text.casefold().split():
            out = out[searchable.loc[out.index].str.contains(token, regex=False)]
    if lunar:
        out = out[out.scenario_lunar]
    for column, (low, high) in (numeric or {}).items():
        mask = out[column].between(low, high)
        if keep_missing:
            mask |= out[column].isna()
        out = out[mask]
    return out.copy()

def scalar_records(df: pd.DataFrame, x: str, y: str, include_summaries: bool = False) -> pd.DataFrame:
    out = df.dropna(subset=[x, y]).copy()
    if not include_summaries:
        out = out[out.record_scope != "study_summary"]
    for name in {x, y}:
        if name in {"pressure_psi", "pressure_kpa", "ppo2_psi", "droplet_initial_diameter_mm"}:
            out = out[out[name] > 0]
        if name == "oxygen_pct":
            out = out[out[name].between(0, 100)]
        if name in {"burn_time_s", "duration_s"}:
            out = out[(out[name] >= 0) & ~out.data_quality_flags.str.contains("invalid_ignition_time|ambiguous_midnight_duration", regex=True)]
    return out

def coverage(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["study_label", "scope_label"], sort=True).size().rename("count").reset_index()

def search_evidence(database: Path, query: str, project: dict | None = None, limit: int = 8) -> list[dict]:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)
    if not tokens:
        return []
    match = " AND ".join('"' + t + '"' for t in tokens[:20])
    sql = """SELECT k.doc_id, p.page_number, k.text, k.citation_json, p.method,
             p.quality_flags_json FROM search JOIN chunks k ON search.chunk_id=k.chunk_id
             JOIN pages p ON p.page_id=k.page_id WHERE search MATCH ?"""
    args = [match]
    if project is not None:
        docids = sorted(set(project["direct_document_ids"] + project["related_document_ids"]))
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
        row = db.execute("SELECT * FROM pages WHERE page_id=?", (page_id,)).fetchone()
        return dict(row) if row else {}

def record_differences(database: Path, record_id: str) -> list[dict]:
    with closing(connect(database)) as db:
        return [dict(r) for r in db.execute("SELECT field,preferred_json,archive_json,resolution FROM source_differences WHERE record_id=?", (record_id,))]

def archive_records(database: Path, investigation_id: str) -> list[dict]:
    with closing(connect(database)) as db:
        return [json.loads(r[0]) for r in db.execute("SELECT record_json FROM supplementary_records WHERE investigation_id=?", (investigation_id,))]

def normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))

def interpret_request(query: str, df: pd.DataFrame) -> tuple[pd.DataFrame, str, list[str]]:
    """Bounded, transparent local intent matching; never claims unrestricted NLP."""
    q = normalize(query)
    out = df.copy()
    notes = []
    ids = {"PSI-" + n for n in re.findall(r"\bpsi[- ]?(\d+)\b", q)}
    families = {"flex": ["PSI-68", "PSI-69", "PSI-142"], "bass": ["PSI-25", "PSI-26"],
                "same": ["PSI-101", "PSI-102"], "spice": ["PSI-107"], "cfi": ["PSI-39", "PSI-159"],
                "saffire": ["PSI-98", "PSI-99", "PSI-100"]}
    if not ids:
        for word, matches in families.items():
            if re.search(r"\b" + word + r"\b", q):
                ids.update(matches)
    if ids:
        out = out[out.investigation_id.isin(ids)]
        notes.append("Estudios: " + ", ".join(sorted(ids)))
    mode = "Atmósfera"
    for words, result in [(('material', 'solido', 'probeta'), 'Materiales'),
                          (('compar', 'cobertura', 'estudios'), 'Comparación'),
                          (('ignicion', 'encendido', 'exito', 'fallo'), 'Ignición'),
                          (('calidad', 'faltan', 'ausente', 'brecha'), 'Calidad')]:
        if any(word in q for word in words):
            mode = result
    if "lunar" in q or "luna" in q:
        out = out[out.scenario_lunar]
        notes.append("Escenario: P ≤ 10,2 psia y O₂ ≥ 30 %; no implica gravedad lunar.")
    if "microgravedad" in q:
        out = out[out.gravity_regime == "microgravity_context"]
        notes.append("Contexto: microgravedad")
    for word, fuel in {"metano": "methane", "etileno": "ethylene", "heptano": "heptane", "metanol": "methanol", "butano": "butane"}.items():
        if word in q:
            out = out[out.fuel.str.contains(fuel, case=False, regex=False)]
            notes.append("Combustible: " + word)
    notes.append("Vista sugerida: " + mode)
    recognized = len(notes) > 1 or any(w in q for w in ["atmosfera", "oxigeno", "presion", "material", "compar", "ignicion", "calidad", "cobertura", "brecha"])
    if not recognized:
        notes.append("Consulta no reconocida por completo. Usa los controles de ejes y filtros para concretarla.")
    if "fria" in q:
        notes.append("Las llamas frías se consultan en la evidencia documental; no se deducen de la ignición.")
    return out, mode, notes
