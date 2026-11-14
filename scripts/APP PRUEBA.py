"""
Flame in Freefall — NASA Space Apps Challenge 2026
Dashboard Interactivo de Seguridad contra Incendios en Microgravedad y Hábitats Espaciales.
Archivo: app(1).py (Versión blindada contra NameError, KeyError y desajustes de ruta CSV).
"""

from __future__ import annotations

import io
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------------
# 0. GUARDIA DE EJECUCIÓN STREAMLIT (Evita ruido si se pulsa 'Play' en VS Code)
# -----------------------------------------------------------------------------
def _check_streamlit_runtime() -> None:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is None:
            print(
                "\n[AVISO FLAME IN FREEFALL] Este archivo es una aplicación web de Streamlit.\n"
                "No lo ejecutes con 'python app(1).py'. Lánzalo desde tu terminal con:\n\n"
                '    streamlit run "app(1).py"\n'
            )
    except Exception:
        pass


_check_streamlit_runtime()

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS AEROESPACIALES
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Flame in Freefall | NASA Space Apps 2026",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .main-header {
        background: linear-gradient(135deg, #0B132B 0%, #1C2541 60%, #2B2D42 100%);
        padding: 1.4rem 1.8rem;
        border-radius: 12px;
        border-left: 6px solid #FF6B35;
        color: #FFFFFF;
        margin-bottom: 1.2rem;
    }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .main-header p { margin: 0.35rem 0 0 0; color: #CBD5E1; font-size: 0.95rem; }
    .safety-banner-critical {
        background-color: #3B0D11;
        border: 1px solid #EF4444;
        border-left: 6px solid #EF4444;
        color: #FEE2E2;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .doi-card {
        background-color: #0F172A;
        border: 1px solid #334155;
        border-left: 4px solid #38BDF8;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.7rem;
        color: #E2E8F0;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONSTANTES FÍSICAS Y OPERACIONALES NASA (PLIEGO FLAME IN FREEFALL)
# -----------------------------------------------------------------------------
ATM_TO_PSI: float = 14.6959488
KPA_TO_PSI: float = 0.1450377
LUNAR_MAX_PRESSURE_PSI: float = 10.2   # Hábitats lunares / rovers presurizados <= 10.2 psi
LUNAR_MIN_O2_PCT: float = 30.0         # Atmósfera enriquecida >= 30% O2 (+40% inflamabilidad)
EARTH_PRESSURE_PSI: float = 14.6959
EARTH_O2_PCT: float = 20.95
EVA_PRESSURE_PSI: float = 4.3
EVA_O2_PCT: float = 100.0
EXPLORATION_ATMOS_PSI: float = 8.2
EXPLORATION_ATMOS_O2_PCT: float = 34.0

GREEN_LIGHT_IDS: Set[str] = {
    "PSI-159", "PSI-68", "PSI-69", "PSI-26", "PSI-25",
    "PSI-98", "PSI-99", "PSI-100", "PSI-20", "PSI-102", "PSI-101", "PSI-22",
}
RED_LIGHT_IDS: Set[str] = {"PSI-181", "PSI-108", "PSI-47"}

# -----------------------------------------------------------------------------
# 3. CATÁLOGO MAESTRO DE LAS 26 INVESTIGACIONES NASA PSI
# -----------------------------------------------------------------------------
MASTER_26_PSI_REGISTRY: List[Dict[str, Any]] = [
    {
        "investigation_id": "PSI-68", "acronym": "FLEX-2",
        "title": "Flame Extinguishment Experiment - 2",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "GREEN",
        "safety_pillar": "suppression", "hardware": "CIR-MDCA",
        "gravity_regime": "microgravity_context", "fuel_class": "liquid",
        "pressure_range_psi": "7.35 - 44.09 psi (0.5 - 3.0 atm)", "o2_range_pct": "10.0% - 40.0%",
        "covers_lunar_envelope": True, "irl_score_max": 87.5, "parent_or_linked_ids": "PSI-69",
        "doi": "Resolver en 'Cite this Investigation' (PSI-68)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-68",
        "gap_notes": "Cubre envolvente lunar (0.5-3.0 atm, 10-40% O2). Pendiente Final Report PDF.",
        "download_priority": "P2 - Completar Reports/", "target_files": "Tablas extinción metil butanoato y d^2(t).",
    },
    {
        "investigation_id": "PSI-159", "acronym": "ACME CFI-G",
        "title": "Advanced Combustion via Microgravity Experiments / Cool Flames Investigation with Gases",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "GREEN",
        "safety_pillar": "prevention", "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context", "fuel_class": "gas",
        "pressure_range_psi": "7.18 - 48.01 psi", "o2_range_pct": "12.0% - 85.0%",
        "covers_lunar_envelope": True, "irl_score_max": 87.5, "parent_or_linked_ids": "PSI-10",
        "doi": "Resolver en 'Cite this Investigation' (PSI-159)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-159",
        "gap_notes": "333 registros limpios (48 en Zona Crítica Lunar hasta 85% O2; 861 filas vacías filtradas).",
        "download_priority": "Completado (Núcleo Activo)", "target_files": "Ingestado en dataset maestro.",
    },
    {
        "investigation_id": "PSI-25", "acronym": "BASS-II",
        "title": "Burning and Suppression of Solids - II",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "GREEN",
        "safety_pillar": "prevention", "hardware": "MSG-SPICE",
        "gravity_regime": "microgravity_context", "fuel_class": "solid",
        "pressure_range_psi": "14.70 psi (1.0 atm)", "o2_range_pct": "13.6% - 22.2%",
        "covers_lunar_envelope": False, "irl_score_max": 81.0, "parent_or_linked_ids": "PSI-26, PSI-62",
        "doi": "Resolver en 'Cite this Investigation' (PSI-25)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25",
        "gap_notes": "129 registros limpios en túnel de ventilación ISS.",
        "download_priority": "P2 - Completar Final Report PDF", "target_files": "PSI-25 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-10", "acronym": "ACME Flame Design",
        "title": "Advanced Combustion via Microgravity Experiments / Flame Design",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "AMBER",
        "safety_pillar": "soot_and_flame_design", "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context", "fuel_class": "gas",
        "pressure_range_psi": "6.26 - 44.36 psi", "o2_range_pct": "19.8% - 85.0%",
        "covers_lunar_envelope": True, "irl_score_max": 77.0, "parent_or_linked_ids": "PSI-159",
        "doi": "Resolver en 'Cite this Investigation' (PSI-10)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-10",
        "gap_notes": "327 registros limpios (18 ensayos en Zona Crítica Lunar).",
        "download_priority": "Completado (Núcleo Activo)", "target_files": "Ingestado en dataset maestro.",
    },
    {
        "investigation_id": "PSI-69", "acronym": "FLEX",
        "title": "Flame Extinguishment Experiment",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "GREEN",
        "safety_pillar": "suppression", "hardware": "CIR-MDCA",
        "gravity_regime": "microgravity_context", "fuel_class": "liquid",
        "pressure_range_psi": "10.18 - 44.86 psi", "o2_range_pct": "12.0% - 34.0%",
        "covers_lunar_envelope": True, "irl_score_max": 73.5, "parent_or_linked_ids": "PSI-68, PSI-117, PSI-142",
        "doi": "Resolver en 'Cite this Investigation' (PSI-69)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-69",
        "gap_notes": "274 registros limpios de supresión con CO2 y He (LOI).",
        "download_priority": "P2 - Completar Final Report PDF", "target_files": "PSI-69 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-101", "acronym": "SAME-R",
        "title": "Smoke Aerosol Measurement Experiment - Reflight",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "GREEN",
        "safety_pillar": "detection", "hardware": "MSG-SAME",
        "gravity_regime": "microgravity_context", "fuel_class": "solid",
        "pressure_range_psi": "14.70 psi", "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False, "irl_score_max": 67.0, "parent_or_linked_ids": "PSI-102, PSI-115",
        "doi": "Resolver en 'Cite this Investigation' (PSI-101)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-101",
        "gap_notes": "109 registros limpios (espuma ignífuga Pyrell®).",
        "download_priority": "P2 - Completar Final Report PDF", "target_files": "PSI-101 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-26", "acronym": "BASS",
        "title": "Burning and Suppression of Solids",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "GREEN",
        "safety_pillar": "prevention", "hardware": "MSG-SPICE",
        "gravity_regime": "microgravity_context", "fuel_class": "solid",
        "pressure_range_psi": "14.70 psi", "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False, "irl_score_max": 67.0, "parent_or_linked_ids": "PSI-25, PSI-62",
        "doi": "Resolver en 'Cite this Investigation' (PSI-26)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-26",
        "gap_notes": "122 registros limpios (tejido 75% algodón / 25% fibra de vidrio vs. NASA-STD-6001).",
        "download_priority": "P2 - Completar Final Report PDF", "target_files": "PSI-26 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-102", "acronym": "SAME",
        "title": "Smoke and Aerosol Measurement Experiment",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "GREEN",
        "safety_pillar": "detection", "hardware": "MSG-SAME",
        "gravity_regime": "microgravity_context", "fuel_class": "solid",
        "pressure_range_psi": "14.70 psi", "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False, "irl_score_max": 67.0, "parent_or_linked_ids": "PSI-101, PSI-115",
        "doi": "Resolver en 'Cite this Investigation' (PSI-102)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-102",
        "gap_notes": "8 resúmenes de granulometría de aerosoles en microgravedad.",
        "download_priority": "P2 - Completar Final Report PDF", "target_files": "PSI-102 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-20", "acronym": "ACME BRE",
        "title": "Advanced Combustion via Microgravity Experiments - Burning Rate Emulator",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "GREEN",
        "safety_pillar": "prevention", "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context", "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi", "o2_range_pct": "21.0% - 40.0%",
        "covers_lunar_envelope": False, "irl_score_max": 63.0, "parent_or_linked_ids": "PSI-26",
        "doi": "Resolver en 'Cite this Investigation' (PSI-20)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-20",
        "gap_notes": "18 registros limpios de emulación de tasa de quema de sólidos.",
        "download_priority": "Completado (Núcleo Activo)", "target_files": "Ingestado en dataset maestro.",
    },
    {
        "investigation_id": "PSI-39", "acronym": "CFI",
        "title": "Cool Flames Investigation",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "AMBER",
        "safety_pillar": "cool_flame_chemistry", "hardware": "CIR-MDCA",
        "gravity_regime": "microgravity_context", "fuel_class": "liquid",
        "pressure_range_psi": "3.67 - 73.48 psi (0.25 - 5.0 atm)", "o2_range_pct": "17.0% - 21.0%",
        "covers_lunar_envelope": False, "irl_score_max": 63.0, "parent_or_linked_ids": "PSI-68, PSI-69",
        "doi": "Resolver en 'Cite this Investigation' (PSI-39)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-39",
        "gap_notes": "79 registros limpios de llamas frías subatmosféricas (n-dodecano).",
        "download_priority": "Completado (Núcleo Activo)", "target_files": "Ingestado en dataset maestro.",
    },
    {
        "investigation_id": "PSI-22", "acronym": "ACME E-FIELD Flames",
        "title": "Advanced Combustion via Microgravity Experiments / Electric-Field Effects in Laminar Diffusion Flames",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "GREEN",
        "safety_pillar": "partial_gravity_proxy", "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context", "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi", "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False, "irl_score_max": 54.0, "parent_or_linked_ids": "LUCI / FM2",
        "doi": "Resolver en 'Cite this Investigation' (PSI-22)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-22",
        "gap_notes": "24 registros limpios. Puente electrostático para simular gravedad parcial (0.16g / 0.38g).",
        "download_priority": "Completado (Núcleo Activo)", "target_files": "Ingestado en dataset maestro.",
    },
    {
        "investigation_id": "PSI-23", "acronym": "ACME s-Flame",
        "title": "Advanced Combustion via Microgravity Experiments / Structure and Response of Spherical Diffusion Flames",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "AMBER",
        "safety_pillar": "fundamental_cfd_calibration", "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context", "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi", "o2_range_pct": "21.0% - 30.0%",
        "covers_lunar_envelope": False, "irl_score_max": 51.0, "parent_or_linked_ids": "PSI-21",
        "doi": "Resolver en 'Cite this Investigation' (PSI-23)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-23",
        "gap_notes": "18 registros limpios de cinética química en llamas esféricas.",
        "download_priority": "Completado (Núcleo Activo)", "target_files": "Ingestado en dataset maestro.",
    },
    {
        "investigation_id": "PSI-106", "acronym": "SLICE",
        "title": "Structure and Liftoff In Combustion Experiment",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "AMBER",
        "safety_pillar": "prevention", "hardware": "MSG-SPICE",
        "gravity_regime": "microgravity_context", "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi", "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False, "irl_score_max": 49.0, "parent_or_linked_ids": "PSI-107",
        "doi": "Resolver en 'Cite this Investigation' (PSI-106)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-106",
        "gap_notes": "12 registros limpios de estabilidad y desprendimiento de llama bajo flujo.",
        "download_priority": "P2 - Completar Final Report PDF", "target_files": "PSI-106 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-107", "acronym": "SPICE",
        "title": "Smoke Point In Co-flow Experiment",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "AMBER",
        "safety_pillar": "prevention", "hardware": "MSG-SPICE",
        "gravity_regime": "microgravity_context", "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi", "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False, "irl_score_max": 49.0, "parent_or_linked_ids": "PSI-106, PSI-60",
        "doi": "Resolver en 'Cite this Investigation' (PSI-107)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-107",
        "gap_notes": "435 registros limpios de punto de humo en túnel MSG.",
        "download_priority": "P2 - Completar Final Report PDF", "target_files": "PSI-107 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-142", "acronym": "Counterflow FLEX",
        "title": "Quantitative Studies of Cool Flame Transitions at Radiation / Stretch Extinction Using Counterflow Flames",
        "research_area": "Combustion Science", "project_type": "Ground Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "AMBER",
        "safety_pillar": "cfd_modeling_validation", "hardware": "GROUND-CFD",
        "gravity_regime": "ground_context", "fuel_class": "liquid",
        "pressure_range_psi": "10.18 - 44.86 psi", "o2_range_pct": "12.0% - 34.0%",
        "covers_lunar_envelope": True, "irl_score_max": 44.0, "parent_or_linked_ids": "PSI-69, PSI-117",
        "doi": "10.1016/j.combustflame.2017.01.028", "doi_verification": "VERIFIED_PUBLICATION_DOIS",
        "known_publications_dois": [
            "10.1016/j.combustflame.2017.01.028",
            "10.1016/j.proci.2018.07.050",
            "10.1016/j.combustflame.2018.03.013",
            "10.1016/j.proci.2018.06.161",
            "10.1016/j.proci.2018.06.162",
            "10.1016/j.proci.2018.06.163",
        ],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-142",
        "gap_notes": "8 resúmenes en 1g con 6 DOIs de publicaciones verificados en CSV.",
        "download_priority": "Completado (Núcleo Activo)", "target_files": "Ingestado en dataset maestro.",
    },
    {
        "investigation_id": "PSI-21", "acronym": "ACME CLD Flame",
        "title": "Advanced Combustion via Microgravity Experiments / Coflow Laminar Diffusion Flame",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE", "traffic_light": "AMBER",
        "safety_pillar": "fundamental_cfd_calibration", "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context", "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi", "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False, "irl_score_max": 37.0, "parent_or_linked_ids": "PSI-23",
        "doi": "Resolver en 'Cite this Investigation' (PSI-21)", "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-21",
        "gap_notes": "32 registros limpios de dilución extrema y submodelos de hollín.",
        "download_priority": "Completado (Núcleo Activo)", "target_files": "Ingestado en dataset maestro.",
    },
    # --- 2 REGISTROS EXCLUIDOS EN AUDITORÍA ---
    {
        "investigation_id": "PSI-108", "acronym": "STDCE-1",
        "title": "Surface Tension Driven Convection Experiment-1",
        "research_area": "Fluid Physics", "project_type": "Microgravity Investigation",
        "ingestion_status": "EXCLUDED_AUDIT", "traffic_light": "RED",
        "safety_pillar": "excluded_fluid_physics", "hardware": "ISS/Shuttle-Fluids",
        "gravity_regime": "microgravity_context", "fuel_class": "none",
        "pressure_range_psi": "N/A", "o2_range_pct": "N/A",
        "covers_lunar_envelope": False, "irl_score_max": 0.0, "parent_or_linked_ids": "N/A",
        "doi": "Excluido (Fluid Physics - no aplicable a combustión)", "doi_verification": "EXCLUDED_NOISE",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-108",
        "gap_notes": "38 filas excluidas por pertenecer a Física de Fluidos.",
        "download_priority": "Excluido (Auditado)", "target_files": "No descargar.",
    },
    {
        "investigation_id": "PSI-47", "acronym": "DAFT",
        "title": "Dust and Aerosol Measurement Feasibility Test (Registro #26 PSI)",
        "research_area": "Combustion Science (Calibración)", "project_type": "Microgravity Investigation",
        "ingestion_status": "EXCLUDED_AUDIT", "traffic_light": "RED",
        "safety_pillar": "excluded_dust_calibration", "hardware": "MSG-SAME",
        "gravity_regime": "microgravity_context", "fuel_class": "none",
        "pressure_range_psi": "N/A", "o2_range_pct": "N/A",
        "covers_lunar_envelope": False, "irl_score_max": 0.0, "parent_or_linked_ids": "PSI-101, PSI-102",
        "doi": "Excluido (Calibración Arizona Road Dust)", "doi_verification": "EXCLUDED_NOISE",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-47",
        "gap_notes": "Resuelve registro #26 ('1 - 25 of 26'). 2 filas excluidas por calibración de polvo.",
        "download_priority": "Excluido (Auditado)", "target_files": "Solo referencia de exclusión.",
    },
    # --- 8 INVESTIGACIONES PENDIENTES DE INGESTA ---
    {
        "investigation_id": "PSI-98", "acronym": "SAFFIRE-I",
        "title": "Spacecraft Fire Safety Experiment-I",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "PENDING_INGESTION", "traffic_light": "GREEN",
        "safety_pillar": "prevention", "hardware": "CYGNUS-SAFFIRE",
        "gravity_regime": "microgravity_context", "fuel_class": "solid",
        "pressure_range_psi": "~14.7 psi (Cygnus)", "o2_range_pct": "~21% O2",
        "covers_lunar_envelope": False, "irl_score_max": 86.0, "parent_or_linked_ids": "PSI-26, PSI-99, PSI-100",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-98",
        "doi_verification": "PENDING_EXTRACTION", "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-98",
        "gap_notes": "Incendio a gran escala en vehículo Cygnus (tejido Sibal).",
        "download_priority": "P1 - Crítica Vuelo (Luz Verde)", "target_files": "Termopares, radiómetros y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-99", "acronym": "SAFFIRE-II",
        "title": "Spacecraft Fire Experiment-II",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "PENDING_INGESTION", "traffic_light": "GREEN",
        "safety_pillar": "prevention", "hardware": "CYGNUS-SAFFIRE",
        "gravity_regime": "microgravity_context", "fuel_class": "solid",
        "pressure_range_psi": "~14.7 psi (Cygnus)", "o2_range_pct": "~21% O2",
        "covers_lunar_envelope": False, "irl_score_max": 86.0, "parent_or_linked_ids": "PSI-26, PSI-98, PSI-100",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-99",
        "doi_verification": "PENDING_EXTRACTION", "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-99",
        "gap_notes": "Límites de inflamabilidad a gran escala frente a NASA-STD-6001.",
        "download_priority": "P1 - Crítica Vuelo (Luz Verde)", "target_files": "CSV telemetría multi-muestra y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-100", "acronym": "SAFFIRE-III",
        "title": "Spacecraft Fire Experiment-III",
        "research_area": "Combustion Science", "project_type": "Microgravity Investigation",
        "ingestion_status": "PENDING_INGESTION", "traffic_light": "GREEN",
        "safety_pillar": "prevention", "hardware": "CYGNUS-SAFFIRE",
        "gravity_regime": "microgravity_context", "fuel_class": "solid",
        "pressure_range_psi": "~14.7 psi (Cygnus)", "o2_range_pct": "~21% O2",
        "covers_lunar_envelope": False, "irl_score_max": 88.0, "parent_or_linked_ids": "PSI-98, PSI-99, PSI-101",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-100",
        "doi_verification": "PENDING_EXTRACTION", "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-100",
        "gap_notes": "Propagación de llama y combustión sin llama (smoldering) con gases tóxicos.",
        "download_priority": "P1 - Crítica Vuelo (Luz Verde)", "target_files": "Sensores CO/CO2, termopares smoldering y PDF.",
    },
    {
        "investigation_id": "PSI-62", "acronym": "FGM / BASS",
        "title": "Concurrent Flame Spread Modeling using Flamelet Generated Manifolds",
        "research_area": "Combustion Science", "project_type": "Ground Investigation",
        "ingestion_status": "PENDING_INGESTION", "traffic_light": "AMBER",
        "safety_pillar": "cfd_modeling_validation", "hardware": "GROUND-CFD",
        "gravity_regime": "ground_context", "fuel_class": "solid",
        "pressure_range_psi": "Validado vs PSI-25/26", "o2_range_pct": "13.6% - 22.2%",
        "covers_lunar_envelope": False, "irl_score_max": 58.0, "parent_or_linked_ids": "PSI-25, PSI-26",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-62",
        "doi_verification": "PENDING_EXTRACTION", "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-62",
        "gap_notes": "Validación CFD FGM de propagación concurrente sobre BASS.",
        "download_priority": "P2 - Calibración CFD/Óptica", "target_files": "Tablas validación FGM y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-60", "acronym": "SPICE Optical Analysis",
        "title": "Computational and Experimental Analysis of SPICE Data Sets",
        "research_area": "Combustion Science", "project_type": "Ground Investigation",
        "ingestion_status": "PENDING_INGESTION", "traffic_light": "AMBER",
        "safety_pillar": "soot_and_flame_design", "hardware": "GROUND-CFD",
        "gravity_regime": "ground_context", "fuel_class": "gas",
        "pressure_range_psi": "Validado vs PSI-107", "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False, "irl_score_max": 52.0, "parent_or_linked_ids": "PSI-107",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-60",
        "doi_verification": "PENDING_EXTRACTION", "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-60",
        "gap_notes": "Pirometría RGB de imágenes RAW Nikon NEF sobre hollín 1g vs 0g.",
        "download_priority": "P2 - Calibración CFD/Óptica", "target_files": "Tablas pirometría color y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-115", "acronym": "SAME Modeling",
        "title": "Numerical Modeling of Smoke Particulate Growth in Microgravity vs. Normal Gravity",
        "research_area": "Combustion Science", "project_type": "Ground Investigation",
        "ingestion_status": "PENDING_INGESTION", "traffic_light": "AMBER",
        "safety_pillar": "detection", "hardware": "GROUND-CFD",
        "gravity_regime": "ground_context", "fuel_class": "solid",
        "pressure_range_psi": "Validado vs PSI-101/102", "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False, "irl_score_max": 56.0, "parent_or_linked_ids": "PSI-101, PSI-102",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-115",
        "doi_verification": "PENDING_EXTRACTION", "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-115",
        "gap_notes": "Simulación Navier-Stokes crecimiento partículas de humo 1g vs 0g.",
        "download_priority": "P2 - Calibración CFD/Óptica", "target_files": "Distribuciones granulométricas simuladas y PDF.",
    },
    {
        "investigation_id": "PSI-117", "acronym": "OpenFOAM FLEX",
        "title": "Effect of External Thermo-Convective Perturbation on Cool Flame Dynamics",
        "research_area": "Combustion Science", "project_type": "Ground Investigation",
        "ingestion_status": "PENDING_INGESTION", "traffic_light": "AMBER",
        "safety_pillar": "cfd_modeling_validation", "hardware": "GROUND-CFD",
        "gravity_regime": "ground_context", "fuel_class": "liquid",
        "pressure_range_psi": "Validado vs PSI-69", "o2_range_pct": "12.0% - 34.0%",
        "covers_lunar_envelope": True, "irl_score_max": 48.0, "parent_or_linked_ids": "PSI-69, PSI-142",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-117",
        "doi_verification": "PENDING_EXTRACTION", "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-117",
        "gap_notes": "Modelo CFD 3D OpenFOAM de gotas de n-alcanos bajo convección.",
        "download_priority": "P2 - Calibración CFD/Óptica", "target_files": "Contornos OpenFOAM y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-181", "acronym": "Pb-Sn / Sn-Ag-Cu Solders",
        "title": "Structure and Properties of Pb-Sn and Pb-free Sn-Ag-Cu Solders",
        "research_area": "Materials Science", "project_type": "Ground Investigation",
        "ingestion_status": "PENDING_INGESTION", "traffic_light": "RED",
        "safety_pillar": "excluded_materials_science", "hardware": "GROUND-Materials",
        "gravity_regime": "ground_context", "fuel_class": "none",
        "pressure_range_psi": "N/A", "o2_range_pct": "N/A",
        "covers_lunar_envelope": False, "irl_score_max": 0.0, "parent_or_linked_ids": "N/A",
        "doi": "No aplica (Ruido de búsqueda — Materials Science)", "doi_verification": "EXCLUDED_NOISE",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-181",
        "gap_notes": "Ruido de búsqueda (soldaduras metálicas). Bloquear en backend.",
        "download_priority": "P3 - No Descargar (Ruido Rojo)", "target_files": "Ninguno.",
    },
]


def get_master_26_df() -> pd.DataFrame:
    return pd.DataFrame(MASTER_26_PSI_REGISTRY)


# -----------------------------------------------------------------------------
# 4. SANEAMIENTO Y NORMALIZACIÓN AUTOMÁTICA DE CSV LOCAL (experiments_configurado.csv)
# -----------------------------------------------------------------------------
def _sanitize_raw_experiments_csv(raw_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    Lee experiments_configurado.csv directamente desde el disco local, ejecuta la aduana
    de seguridad aeroespacial (excluye PSI-108/PSI-47, filas vacías y duplicados), normaliza
    unidades (psi, %O2, ppO2) y construye el catálogo agregado y las 3 particiones por perfil.
    """
    df = pd.read_csv(raw_path, low_memory=False)
    master_map = {r["investigation_id"]: r for r in MASTER_26_PSI_REGISTRY}

    # 1. Normalizar ID y excluir ruido no-combustión (PSI-108, PSI-47, PSI-181)
    df["investigation_id"] = df["investigation_id"].astype(str).str.strip().str.upper()
    if "is_combustion_core" in df.columns:
        df = df[df["is_combustion_core"].fillna(False).astype(bool)]
    df = df[~df["investigation_id"].isin(RED_LIGHT_IDS)]

    # 2. Excluir filas vacías de origen (PSI-159 empty_source_row)
    if "grain_type" in df.columns:
        df = df[df["grain_type"].astype(str).str.strip() != "empty_source_row"]

    df = df.reset_index(drop=True)

    # 3. Enriquecer metadatos faltantes a nivel de estudio
    df["acronym"] = df["investigation_id"].map(lambda x: master_map.get(x, {}).get("acronym", x))
    df["traffic_light"] = df["investigation_id"].map(
        lambda x: "GREEN" if x in GREEN_LIGHT_IDS else ("RED" if x in RED_LIGHT_IDS else "AMBER")
    )
    if "safety_pillar" not in df.columns:
        df["safety_pillar"] = np.nan
    df["safety_pillar"] = df["safety_pillar"].fillna(
        df["investigation_id"].map(lambda x: master_map.get(x, {}).get("safety_pillar", "fundamental_research"))
    )
    if "hardware" not in df.columns:
        df["hardware"] = np.nan
    df["hardware"] = df["hardware"].fillna(
        df["investigation_id"].map(lambda x: master_map.get(x, {}).get("hardware", "ISS-General"))
    )
    if "gravity_regime" not in df.columns:
        df["gravity_regime"] = "microgravity_context"
    df["gravity_regime"] = df["gravity_regime"].fillna("microgravity_context")
    if "fuel_class" not in df.columns:
        df["fuel_class"] = "unknown"
    df["fuel_class"] = df["fuel_class"].fillna("unknown")

    # 4. Aduana de unidades físicas (pressure_psi, oxygen_pct, ppo2_psi)
    if "pressure_psi" not in df.columns:
        if "pressure_atm" in df.columns:
            df["pressure_psi"] = pd.to_numeric(df["pressure_atm"], errors="coerce") * ATM_TO_PSI
        elif "pressure_kpa" in df.columns:
            df["pressure_psi"] = pd.to_numeric(df["pressure_kpa"], errors="coerce") * KPA_TO_PSI
        else:
            df["pressure_psi"] = np.nan
    else:
        df["pressure_psi"] = pd.to_numeric(df["pressure_psi"], errors="coerce")

    if "oxygen_pct" not in df.columns:
        if "oxygen_fraction" in df.columns:
            ox = pd.to_numeric(df["oxygen_fraction"], errors="coerce")
            df["oxygen_pct"] = np.where(ox <= 1.0, ox * 100.0, ox)
        else:
            df["oxygen_pct"] = np.nan
    else:
        df["oxygen_pct"] = pd.to_numeric(df["oxygen_pct"], errors="coerce")

    df["ppo2_psi"] = (df["pressure_psi"] * (df["oxygen_pct"] / 100.0)).round(4)

    if "is_lunar_atmosphere" not in df.columns:
        df["is_lunar_atmosphere"] = (
            (df["pressure_psi"] <= LUNAR_MAX_PRESSURE_PSI)
            & (df["oxygen_pct"] >= LUNAR_MIN_O2_PCT)
        )
    else:
        df["is_lunar_atmosphere"] = df["is_lunar_atmosphere"].fillna(False).astype(bool)

    if "irl_score" not in df.columns:
        df["irl_score"] = df["investigation_id"].map(lambda x: master_map.get(x, {}).get("irl_score_max", 50.0))
    else:
        df["irl_score"] = pd.to_numeric(df["irl_score"], errors="coerce").fillna(
            df["investigation_id"].map(lambda x: master_map.get(x, {}).get("irl_score_max", 50.0))
        )

    # 5. Construir catálogo agregado por investigación (study_catalog_summary equivalente)
    cat_rows = []
    for inv_id, grp in df.groupby("investigation_id", sort=False):
        meta = master_map.get(inv_id, {})
        cat_rows.append({
            "investigation_id": inv_id,
            "acronym": meta.get("acronym", inv_id),
            "traffic_light": grp["traffic_light"].iloc[0],
            "safety_pillar": str(grp["safety_pillar"].iloc[0]),
            "hardware": str(grp["hardware"].iloc[0]),
            "gravity_regime": str(grp["gravity_regime"].iloc[0]),
            "total_clean_records": int(len(grp)),
            "lunar_envelope_rows": int(grp["is_lunar_atmosphere"].sum()),
            "study_covers_lunar": bool(meta.get("covers_lunar_envelope", grp["is_lunar_atmosphere"].any())),
            "irl_score_mean": round(float(grp["irl_score"].mean()), 2),
            "irl_score_max": round(float(grp["irl_score"].max()), 2),
            "doi": meta.get("doi", "Consultar ficha NASA PSI"),
        })
    df_cat = pd.DataFrame(cat_rows)

    partitions = {
        "Seguridad Aeroespacial": df.copy(),
        "Estudiantes": df.copy(),
        "Investigadores CFD": df.copy(),
    }
    return df, df_cat, partitions


def _build_embedded_fallback_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Fallback científico embebido si no hay CSVs locales en la carpeta."""
    rng = np.random.default_rng(42)
    study_specs = [
        ("PSI-68", "FLEX-2", "GREEN", "suppression", "CIR-MDCA", "microgravity_context", "liquid", 8, 0, True, 7.3480, 44.0878, 10.0, 40.0, 87.50, 87.5, "Resolver en PSI-68"),
        ("PSI-159", "ACME CFI-G", "GREEN", "prevention", "CIR-ACME", "microgravity_context", "gas", 333, 48, True, 7.1848, 48.0058, 12.0, 85.0, 78.63, 87.5, "Resolver en PSI-159"),
        ("PSI-25", "BASS-II", "GREEN", "prevention", "MSG-SPICE", "microgravity_context", "solid", 129, 0, False, 14.6959, 14.6959, 13.6, 22.2, 81.00, 81.0, "Resolver en PSI-25"),
        ("PSI-10", "ACME Flame Design", "AMBER", "soot_and_flame_design", "CIR-ACME", "microgravity_context", "gas", 327, 18, True, 6.2605, 44.3553, 19.8, 85.0, 68.91, 77.0, "Resolver en PSI-10"),
        ("PSI-69", "FLEX", "GREEN", "suppression", "CIR-MDCA", "microgravity_context", "liquid", 274, 0, True, 10.1769, 44.8594, 12.0, 34.0, 73.50, 73.5, "Resolver en PSI-69"),
        ("PSI-101", "SAME-R", "GREEN", "detection", "MSG-SAME", "microgravity_context", "solid", 109, 0, False, 14.6959, 14.6959, 21.0, 21.0, 67.00, 67.0, "Resolver en PSI-101"),
        ("PSI-26", "BASS", "GREEN", "prevention", "MSG-SPICE", "microgravity_context", "solid", 122, 0, False, 14.6959, 14.6959, 21.0, 21.0, 67.00, 67.0, "Resolver en PSI-26"),
        ("PSI-102", "SAME", "GREEN", "detection", "MSG-SAME", "microgravity_context", "solid", 8, 0, False, 14.6959, 14.6959, 21.0, 21.0, 66.06, 67.0, "Resolver en PSI-102"),
        ("PSI-20", "ACME BRE", "GREEN", "prevention", "CIR-ACME", "microgravity_context", "gas", 18, 0, False, 14.6959, 14.6959, 21.0, 40.0, 63.00, 63.0, "Resolver en PSI-20"),
        ("PSI-39", "CFI", "AMBER", "cool_flame_chemistry", "CIR-MDCA", "microgravity_context", "liquid", 79, 0, False, 3.6740, 73.4797, 17.0, 21.0, 63.00, 63.0, "Resolver en PSI-39"),
        ("PSI-22", "ACME E-FIELD Flames", "GREEN", "partial_gravity_proxy", "CIR-ACME", "microgravity_context", "gas", 24, 0, False, 14.6959, 14.6959, 21.0, 21.0, 54.00, 54.0, "Resolver en PSI-22"),
        ("PSI-23", "ACME s-Flame", "AMBER", "fundamental_cfd_calibration", "CIR-ACME", "microgravity_context", "gas", 18, 0, False, 14.6959, 14.6959, 21.0, 30.0, 51.00, 51.0, "Resolver en PSI-23"),
        ("PSI-106", "SLICE", "AMBER", "prevention", "MSG-SPICE", "microgravity_context", "gas", 12, 0, False, 14.6959, 14.6959, 21.0, 21.0, 49.00, 49.0, "Resolver en PSI-106"),
        ("PSI-107", "SPICE", "AMBER", "prevention", "MSG-SPICE", "microgravity_context", "gas", 435, 0, False, 14.6959, 14.6959, 21.0, 21.0, 49.00, 49.0, "Resolver en PSI-107"),
        ("PSI-142", "Counterflow FLEX", "AMBER", "cfd_modeling_validation", "GROUND-CFD", "ground_context", "liquid", 8, 0, True, 10.1769, 44.8594, 12.0, 34.0, 44.00, 44.0, "10.1016/j.combustflame.2017.01.028"),
        ("PSI-21", "ACME CLD Flame", "AMBER", "fundamental_cfd_calibration", "CIR-ACME", "microgravity_context", "gas", 32, 0, False, 14.6959, 14.6959, 21.0, 21.0, 37.00, 37.0, "Resolver en PSI-21"),
    ]
    cat_rows, exp_rows = [], []
    rec_counter = 1
    for inv_id, acr, tl, pillar, hw, grav, fclass, n_clean, n_lunar, covers_lunar, p_min, p_max, o_min, o_max, irl_mean, irl_max, doi in study_specs:
        cat_rows.append({
            "investigation_id": inv_id, "acronym": acr, "traffic_light": tl,
            "safety_pillar": pillar, "hardware": hw, "gravity_regime": grav,
            "total_clean_records": n_clean, "lunar_envelope_rows": n_lunar,
            "study_covers_lunar": covers_lunar, "irl_score_mean": irl_mean,
            "irl_score_max": irl_max, "doi": doi,
        })
        for idx in range(n_clean):
            is_lunar = idx < n_lunar
            if is_lunar:
                p_val = float(rng.uniform(7.18, 8.00)) if inv_id == "PSI-159" else float(rng.uniform(6.26, 7.57))
                o2_val = float(rng.uniform(30.0, 85.0))
            elif inv_id in {"PSI-159", "PSI-10", "PSI-69", "PSI-39", "PSI-23", "PSI-25"}:
                p_val = float(rng.uniform(max(10.3, p_min), p_max)) if p_max > 10.3 else float(p_min)
                o2_val = float(rng.uniform(o_min, min(29.5, o_max))) if o_max > o_min else float(o_min)
            else:
                p_val, o2_val = np.nan, np.nan
            ppo2_val = (p_val * (o2_val / 100.0)) if not np.isnan(p_val) else np.nan
            exp_rows.append({
                "record_id": f"REC-{rec_counter:04d}", "investigation_id": inv_id, "acronym": acr,
                "traffic_light": tl, "grain_type": "summary" if n_clean <= 8 else "test",
                "gravity_regime": grav, "hardware": hw, "safety_pillar": pillar,
                "fuel_class": fclass, "pressure_psi": round(p_val, 4) if not np.isnan(p_val) else np.nan,
                "oxygen_pct": round(o2_val, 2) if not np.isnan(o2_val) else np.nan,
                "ppo2_psi": round(ppo2_val, 4) if not np.isnan(ppo2_val) else np.nan,
                "is_lunar_atmosphere": bool(is_lunar),
                "irl_score": irl_max if is_lunar else irl_mean, "doi": doi,
            })
            rec_counter += 1

    df_full = pd.DataFrame(exp_rows)
    df_cat = pd.DataFrame(cat_rows)
    return df_full, df_cat, {
        "Seguridad Aeroespacial": df_full.copy(),
        "Estudiantes": df_full.copy(),
        "Investigadores CFD": df_full.copy(),
    }


@st.cache_data(show_spinner=False)
def load_all_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame], str]:
    """Busca primero CSVs procesados, luego experiments_configurado.csv en raíz/data, y finalmente fallback."""
    base_dir = Path("data/processed")
    full_path = base_dir / "experiments_limpio_completo.csv"
    cat_path = base_dir / "study_catalog_summary.csv"

    if full_path.exists() and cat_path.exists():
        df_full = pd.read_csv(full_path, low_memory=False)
        df_cat = pd.read_csv(cat_path, low_memory=False)
        part_map = {
            "Seguridad Aeroespacial": base_dir / "partition_seguridad_lunar.csv",
            "Estudiantes": base_dir / "partition_estudiantes.csv",
            "Investigadores CFD": base_dir / "partition_investigadores_cfd.csv",
        }
        parts = {k: (pd.read_csv(p, low_memory=False) if p.exists() else df_full.copy()) for k, p in part_map.items()}
        return df_full, df_cat, parts, "CSV Procesados (data/processed)"

    # Detección automática de experiments_configurado.csv en raíz o en data/
    for candidate in [Path("experiments_configurado.csv"), Path("data/experiments_configurado.csv"), Path("data/raw/experiments_configurado.csv")]:
        if candidate.exists():
            df_full, df_cat, parts = _sanitize_raw_experiments_csv(candidate)
            return df_full, df_cat, parts, f"CSV Local Saneado ({candidate.name})"

    df_full, df_cat, parts = _build_embedded_fallback_datasets()
    return df_full, df_cat, parts, "Baseline Científico Embebido"


# -----------------------------------------------------------------------------
# 5. GRÁFICO INTERACTIVO DE ENVOLVENTE ATMOSFÉRICA (P_psi vs %O2)
# -----------------------------------------------------------------------------
def build_atmospheric_envelope_figure(
    df: pd.DataFrame,
    show_study_envelopes: bool = True,
    highlight_partial_grav_bounds: bool = True,
) -> go.Figure:
    fig = go.Figure()

    # Zona Crítica Lunar (P <= 10.2 psi y %O2 >= 30%)
    fig.add_shape(
        type="rect", x0=30.0, x1=100.0, y0=0.0, y1=10.2,
        fillcolor="rgba(239, 68, 68, 0.16)",
        line=dict(color="rgba(239, 68, 68, 0.85)", width=2, dash="dash"),
        layer="below",
    )

    if show_study_envelopes:
        fig.add_shape(
            type="rect", x0=10.0, x1=40.0, y0=7.35, y1=44.09,
            fillcolor="rgba(16, 185, 129, 0.06)",
            line=dict(color="rgba(16, 185, 129, 0.55)", width=1.5, dash="dot"),
            layer="below",
        )
        fig.add_shape(
            type="rect", x0=12.0, x1=34.0, y0=10.18, y1=44.86,
            fillcolor="rgba(56, 189, 248, 0.05)",
            line=dict(color="rgba(56, 189, 248, 0.45)", width=1.2, dash="dot"),
            layer="below",
        )

    if highlight_partial_grav_bounds:
        fig.add_shape(
            type="line", x0=0.0, x1=100.0, y0=10.2, y1=10.2,
            line=dict(color="#F87171", width=1.3, dash="dash"),
        )

    # Isolíneas de ppO2
    o2_grid = np.linspace(8.0, 100.0, 200)
    for ppo2_target, label, color in [
        (3.06, "ppO2 = 3.06 psi (Normoxia / Base Lunar)", "rgba(148, 163, 184, 0.55)"),
        (4.30, "ppO2 = 4.30 psi (Traje EVA 100% O2)", "rgba(251, 191, 36, 0.65)"),
        (6.00, "ppO2 = 6.00 psi (Riesgo Hiperóxico Severo)", "rgba(248, 113, 113, 0.65)"),
    ]:
        p_curve = ppo2_target / (o2_grid / 100.0)
        valid_mask = (p_curve >= 1.0) & (p_curve <= 75.0)
        fig.add_trace(
            go.Scatter(
                x=o2_grid[valid_mask], y=p_curve[valid_mask], mode="lines",
                name=label, line=dict(color=color, width=1.4, dash="dot"),
            )
        )

    # Blindaje de columnas antes de graficar
    scalar_df = df.dropna(subset=["pressure_psi", "oxygen_pct"]).copy() if {"pressure_psi", "oxygen_pct"}.issubset(df.columns) else pd.DataFrame()
    if not scalar_df.empty:
        for col_safe in ["investigation_id", "acronym", "hardware"]:
            if col_safe not in scalar_df.columns:
                scalar_df[col_safe] = "N/A"
            scalar_df[col_safe] = scalar_df[col_safe].fillna("N/A").astype(str)

        if "is_lunar_atmosphere" not in scalar_df.columns:
            scalar_df["is_lunar_atmosphere"] = (
                (scalar_df["pressure_psi"] <= LUNAR_MAX_PRESSURE_PSI)
                & (scalar_df["oxygen_pct"] >= LUNAR_MIN_O2_PCT)
            )
        else:
            scalar_df["is_lunar_atmosphere"] = scalar_df["is_lunar_atmosphere"].fillna(False).astype(bool)

        non_lunar = scalar_df[~scalar_df["is_lunar_atmosphere"]]
        lunar = scalar_df[scalar_df["is_lunar_atmosphere"]]

        fig.add_trace(
            go.Scatter(
                x=non_lunar["oxygen_pct"], y=non_lunar["pressure_psi"], mode="markers",
                name="Ensayos Microgravedad / Tierra (Nominal)",
                marker=dict(size=7, color="#38BDF8", opacity=0.65),
                customdata=non_lunar[["investigation_id", "acronym", "hardware"]].to_numpy(),
                hovertemplate="<b>%{customdata[0]} (%{customdata[1]})</b><br>O2: %{x:.1f}% | P: %{y:.2f} psi<br>Hardware: %{customdata[2]}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=lunar["oxygen_pct"], y=lunar["pressure_psi"], mode="markers",
                name="Zona Crítica Lunar (P <= 10.2 psi y O2 >= 30%)",
                marker=dict(size=9, color="#EF4444", symbol="diamond"),
                customdata=lunar[["investigation_id", "acronym", "hardware"]].to_numpy(),
                hovertemplate="<b>⚠️ ZONA LUNAR — %{customdata[0]} (%{customdata[1]})</b><br>O2: %{x:.1f}% | P: %{y:.2f} psi<br>Hardware: %{customdata[2]}<extra></extra>",
            )
        )

    for r_name, rx, ry, r_col, r_sym in [
        ("Tierra / ISS (14.7 psi, 21% O2)", EARTH_O2_PCT, EARTH_PRESSURE_PSI, "#10B981", "circle"),
        ("Hábitat Lunar (10.2 psi, 30% O2)", LUNAR_MIN_O2_PCT, LUNAR_MAX_PRESSURE_PSI, "#F59E0B", "star"),
        ("Atmósfera Exploración (8.2 psi, 34% O2)", EXPLORATION_ATMOS_O2_PCT, EXPLORATION_ATMOS_PSI, "#FB923C", "star"),
        ("Traje EVA NASA (4.3 psi, 100% O2)", EVA_O2_PCT, EVA_PRESSURE_PSI, "#A855F7", "hexagram"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=[rx], y=[ry], mode="markers+text", name=r_name,
                text=[r_name.split("(")[0].strip()], textposition="top center",
                marker=dict(size=12, color=r_col, symbol=r_sym, line=dict(width=1.5, color="#FFFFFF")),
            )
        )

    fig.update_layout(
        title="Envolvente de Seguridad Atmosférica: Presión Absoluta (psia) vs. Concentración de Oxígeno (% O2)",
        xaxis_title="Concentración Volumétrica de Oxígeno (% O2)",
        yaxis_title="Presión Absoluta de Cabina / Cámara (psia)",
        xaxis=dict(range=[5, 105], gridcolor="rgba(148,163,184,0.15)"),
        yaxis=dict(range=[0, 52], gridcolor="rgba(148,163,184,0.15)"),
        template="plotly_dark", height=540,
        legend=dict(orientation="h", yanchor="bottom", y=-0.34, xanchor="left", x=0),
        margin=dict(l=40, r=30, t=55, b=120),
    )
    return fig


# -----------------------------------------------------------------------------
# 6. ASISTENTE DE CITAS DOI Y GENERADOR DE INFORMES
# -----------------------------------------------------------------------------
def format_citation(row: Dict[str, Any], style: str = "APA") -> str:
    inv_id, acr, title, doi, url = row["investigation_id"], row["acronym"], row["title"], row["doi"], row["psi_url"]
    pubs = row.get("known_publications_dois", [])
    if style == "BibTeX":
        clean_doi = pubs[0] if pubs else doi
        return (
            f"@dataset{{nasa_psi_{inv_id.lower().replace('-', '_')},\n"
            f"  author = {{NASA Physical Sciences Informatics (PSI)}},\n"
            f"  title = {{{inv_id}: {acr} - {title}}},\n  year = {{2026}},\n"
            f"  publisher = {{NASA SMD Open Source Science}},\n  note = {{DOI: {clean_doi}}},\n  url = {{{url}}}\n}}"
        )
    if style == "IEEE":
        doi_str = f"doi: {pubs[0]}" if pubs else f"DOI Ref: {doi}"
        return f'NASA PSI, "{inv_id} ({acr}): {title}," NASA SMD Open Source Science, {doi_str}. Available: {url}'
    doi_str = f"https://doi.org/{pubs[0]}" if pubs else f"[{doi}] — {url}"
    return f"NASA Physical Sciences Informatics (PSI). (2026). {inv_id} ({acr}): {title} [Data set]. NASA SMD Open Source Science. {doi_str}"


def query_doi_knowledge_base(user_query: str, citation_style: str = "APA") -> Dict[str, Any]:
    master_df = get_master_26_df()
    q_lower = user_query.strip().lower()
    mentioned_ids = {f"PSI-{m}" for m in re.findall(r"\bpsi[-\s]?(\d{1,4})\b", q_lower)}
    keywords = {
        "saffire": ["PSI-98", "PSI-99", "PSI-100"], "flex-2": ["PSI-68"],
        "flex": ["PSI-68", "PSI-69", "PSI-117", "PSI-142"], "bass": ["PSI-25", "PSI-26", "PSI-62"],
        "same": ["PSI-101", "PSI-102", "PSI-115"], "spice": ["PSI-107", "PSI-60", "PSI-106"],
        "acme": ["PSI-10", "PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-159"],
        "cfi": ["PSI-159", "PSI-39"], "e-field": ["PSI-22"], "counterflow": ["PSI-142"],
    }
    for kw, ids in keywords.items():
        if kw in q_lower:
            mentioned_ids.update(ids)

    if mentioned_ids:
        matched_df = master_df[master_df["investigation_id"].isin(mentioned_ids)].copy()
        summary = f"Investigaciones identificadas: {', '.join(sorted(mentioned_ids))}."
    elif any(w in q_lower for w in ["verificado", "verified", "doi exacto", "10.1016"]):
        matched_df = master_df[master_df["doi_verification"] == "VERIFIED_PUBLICATION_DOIS"].copy()
        summary = "Únicamente **PSI-142 (Counterflow FLEX)** tiene 6 DOIs de publicaciones verificados embebidos en CSV."
    elif any(w in q_lower for w in ["pendiente", "faltan", "brecha", "gap"]):
        matched_df = master_df[master_df["ingestion_status"] == "PENDING_INGESTION"].copy()
        summary = "Las 8 investigaciones pendientes de ingesta requieren extraer su DOI desde la landing page de NASA PSI."
    else:
        matched_df = master_df[master_df["traffic_light"] == "GREEN"].copy()
        summary = "Mostrando las investigaciones críticas de Semáforo VERDE y sus enlaces de atribución NASA PSI."

    records = []
    for _, r in matched_df.iterrows():
        rd = r.to_dict()
        rd["formatted_citation"] = format_citation(rd, style=citation_style)
        records.append(rd)
    return {"intent_summary": summary, "matched_count": len(records), "records": records}


def generate_jury_html_report(df_full: pd.DataFrame, team_name: str, target_mission: str, include_appendix: bool) -> str:
    master_df = get_master_26_df()
    pending_df = master_df[master_df["ingestion_status"] == "PENDING_INGESTION"]
    n_clean = len(df_full)
    n_lunar = int(df_full["is_lunar_atmosphere"].sum()) if "is_lunar_atmosphere" in df_full.columns else 0
    gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    rows_html = "".join(
        f"<tr><td><b>{r['investigation_id']}</b></td><td>{r['acronym']}</td><td>{r['traffic_light']}</td><td>{r['gap_notes']}</td></tr>"
        for _, r in pending_df.iterrows()
    )
    doi_html = ""
    if include_appendix:
        d_rows = "".join(
            f"<tr><td><b>{r['investigation_id']}</b></td><td>{r['acronym']}</td><td>{r['ingestion_status']}</td><td>{r['doi']}</td></tr>"
            for _, r in master_df.iterrows()
        )
        doi_html = f"<h2>Apéndice DOI (NASA SMD Open Source Science)</h2><table border='1' cellpadding='6'><tr><th>ID</th><th>Acrónimo</th><th>Estado</th><th>DOI</th></tr>{d_rows}</table>"
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>Informe NASA Space Apps</title></head>
    <body style="font-family:sans-serif;padding:24px;"><h1>FLAME IN FREEFALL — Informe Técnico</h1>
    <p><b>Equipo:</b> {team_name} | <b>Misión:</b> {target_mission} | <b>Fecha:</b> {gen_date}</p>
    <p><b>Registros limpios:</b> {n_clean:,} | <b>Ensayos Zona Crítica Lunar (&le;10.2 psi, &ge;30% O2):</b> {n_lunar}</p>
    <p style="background:#FEE2E2;padding:12px;border-left:4px solid #DC2626;"><b>ALERTA GRAVEDAD PARCIAL:</b> 0 ensayos reales en 0.16g/0.38g en NASA PSI; riesgo acotado entre 0g y 1g + proxy PSI-22.</p>
    <h2>Brechas (8 estudios pendientes)</h2><table border="1" cellpadding="6"><tr><th>ID</th><th>Acrónimo</th><th>Semáforo</th><th>Brecha</th></tr>{rows_html}</table>
    {doi_html}</body></html>"""


# -----------------------------------------------------------------------------
# 7. INTERFAZ PRINCIPAL STREAMLIT (FLUJO ESTRICTO: df_base -> filtros -> filtered)
# -----------------------------------------------------------------------------
def main() -> None:
    df_full, df_cat, partitions, data_source_label = load_all_datasets()
    master_26_df = get_master_26_df()

    st.markdown(
        """
        <div class="main-header">
            <h1>🔥 FLAME IN FREEFALL — Seguridad contra Incendios en Microgravedad y Hábitats Lunares</h1>
            <p>NASA Space Apps Challenge 2026 • Repositorio NASA PSI • Auditoría de Envolvente Lunar, Gravedad Parcial y Trazabilidad SMD Open Source Science</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_p1, col_p2, col_p3 = st.columns([2, 2, 1.5])
    with col_p1:
        selected_profile = st.selectbox(
            "👤 Perfil Operacional del Usuario",
            options=["Seguridad Aeroespacial", "Estudiantes", "Investigadores CFD"],
            index=0,
        )
    with col_p2:
        selected_gravity = st.selectbox(
            "🪐 Régimen Gravitacional Objetivo",
            options=[
                "Microgravedad Orbital (0g — ISS / Cygnus)",
                "Gravedad Parcial Lunar (0.16g — Artemis Base / Rover)",
                "Gravedad Parcial Marciana (0.38g — Hábitat Marte)",
                "Comparativa Tierra vs. Espacio (1g <-> 0g)",
            ],
            index=1,
        )
    with col_p3:
        st.metric("Fuente Activa", data_source_label, f"{len(df_full):,} filas limpias")

    # Paso 1: Base saneada para el perfil activo (SIEMPRE definida antes de cualquier filtro)
    df_base = partitions.get(selected_profile, df_full).copy()

    if "0.16g" in selected_gravity or "0.38g" in selected_gravity:
        st.markdown(
            """
            <div class="safety-banner-critical">
                <strong>🚨 ALERTA DE SEGURIDAD REFORZADA — AUSENCIA DE DATOS EXPERIMENTALES EN GRAVEDAD PARCIAL (0.16g / 0.38g):</strong><br>
                Actualmente existen <strong>0 ensayos físicos reales</strong> en gravedad lunar (0.16g) o marciana (0.38g)
                en NASA PSI (a la espera de <em>LUCI</em> y <em>FM2</em>). En atmósferas hiperóxicas (&le; 10.2 psi y &ge; 30% O<sub>2</sub>,
                inflamabilidad &gt;40% mayor que en Tierra), el sistema acota el riesgo entre <strong>0g</strong> y <strong>1g</strong>
                y usa <strong>PSI-22 (ACME E-FIELD Flames)</strong> como proxy electrostático.
            </div>
            """,
            unsafe_allow_html=True,
        )

    tab_env, tab_profile, tab_gap = st.tabs([
        "🛰️ Envolvente Atmosférica & Seguridad Lunar",
        f"🧭 Vista Especializada: {selected_profile}",
        "🔍 Auditoría de Cobertura y Brechas (Gap Analysis)",
    ])

    # --- PESTAÑA 1 ---
    with tab_env:
        c1, c2, c3, c4 = st.columns(4)
        n_scalar = int((df_full["pressure_psi"].notna() & df_full["oxygen_pct"].notna()).sum()) if {"pressure_psi", "oxygen_pct"}.issubset(df_full.columns) else 0
        n_lunar = int(df_full["is_lunar_atmosphere"].sum()) if "is_lunar_atmosphere" in df_full.columns else 0
        c1.metric("Estudios PSI Activos", f"{len(df_cat)} / 26", "9 Verde | 7 Ámbar")
        c2.metric("Coordenadas Escalares (P, %O2)", f"{n_scalar:,}", "Unidades normalizadas psia")
        c3.metric("Ensayos Zona Crítica Lunar", f"{n_lunar}", "P <= 10.2 psi y %O2 >= 30%")
        c4.metric("IRL Máximo Alcanzado", "87.5 / 100", "PSI-68 FLEX-2 & PSI-159")

        opt_c1, opt_c2 = st.columns(2)
        show_envelopes = opt_c1.checkbox("Mostrar cajas paramétricas (PSI-68 FLEX-2, PSI-69 FLEX)", value=True)
        show_bounds = opt_c2.checkbox("Resaltar umbral de presión lunar (10.2 psia)", value=True)

        st.plotly_chart(
            build_atmospheric_envelope_figure(df_full, show_study_envelopes=show_envelopes, highlight_partial_grav_bounds=show_bounds),
            use_container_width=True,
        )

        st.subheader("Ranking de Relevancia Lunar (IRL) — Investigaciones Ingestadas")
        st.dataframe(
            df_cat.sort_values(by=["irl_score_max", "total_clean_records"], ascending=False),
            use_container_width=True,
            hide_index=True,
        )

    # --- PESTAÑA 2 (Opciones leídas SIEMPRE desde df_base antes de construir filtered) ---
    with tab_profile:
        st.subheader(f"Panel Operacional — Perfil: {selected_profile}")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            inv_options = sorted(df_base["investigation_id"].dropna().astype(str).unique()) if "investigation_id" in df_base.columns else []
            selected_invs = st.multiselect("Filtrar por Investigación (ID PSI)", options=inv_options, default=[])
        with col_f2:
            tl_options = sorted(df_base["traffic_light"].dropna().astype(str).unique()) if "traffic_light" in df_base.columns else ["GREEN", "AMBER"]
            selected_tls = st.multiselect("Filtrar por Semáforo de Solvencia", options=tl_options, default=tl_options)
        with col_f3:
            only_lunar = st.checkbox("Solo Zona Crítica Lunar (P <= 10.2 psi y %O2 >= 30%)", value=False)

        # Paso 2: Construcción segura de `filtered` DESPUÉS de recoger los widgets
        filtered = df_base.copy()
        if selected_invs and "investigation_id" in filtered.columns:
            filtered = filtered[filtered["investigation_id"].astype(str).isin(selected_invs)]
        if selected_tls and "traffic_light" in filtered.columns:
            filtered = filtered[filtered["traffic_light"].astype(str).isin(selected_tls)]
        if only_lunar and "is_lunar_atmosphere" in filtered.columns:
            filtered = filtered[filtered["is_lunar_atmosphere"] == True]

        if selected_profile == "Seguridad Aeroespacial":
            st.info(
                "📌 **Criterio NASA-STD-6001:** En microgravedad y baja presión, la ausencia de convección natural "
                "altera los límites de inflamabilidad. Contrasta **PSI-25/26 (BASS)** frente a **PSI-98/99/100 (SAFFIRE)**."
            )
        elif selected_profile == "Estudiantes":
            st.info(
                "🎓 **Física de la Llama (1g vs. 0g):** Sin flotabilidad, la llama abandona la forma de lágrima y se convierte "
                "en una **esfera azul difusiva**, pudiendo sostener llamas frías (*Cool Flames*) a baja temperatura."
            )
            col_e1, col_e2 = st.columns(2)
            cat_safe = df_cat.copy()
            cat_safe["safety_pillar"] = cat_safe["safety_pillar"].fillna("Sin clasificar").astype(str)
            with col_e1:
                st.plotly_chart(
                    px.pie(cat_safe, names="safety_pillar", values="total_clean_records", title="Registros por Pilar de Seguridad", template="plotly_dark"),
                    use_container_width=True,
                )
            with col_e2:
                st.plotly_chart(
                    px.bar(
                        cat_safe, x="acronym", y="irl_score_max", color="traffic_light",
                        color_discrete_map={"GREEN": "#10B981", "AMBER": "#F59E0B"},
                        title="Índice de Relevancia Lunar (IRL) por Experimento", template="plotly_dark",
                    ),
                    use_container_width=True,
                )
        else:
            st.info(
                "🔬 **Acoplamiento Vuelo (0g) ↔ Validación CFD Tierra:** Exporta condiciones de contorno normalizadas "
                "(psia, fracción molar $X_{O_2}$, $ppO_2$) y verifica las citas DOI exigidas por NASA SMD Open Source Science."
            )

        st.metric("Registros Activos en Selección", f"{len(filtered):,}", f"de {len(df_base):,} saneados")
        st.dataframe(filtered.head(250), use_container_width=True, hide_index=True)

        st.download_button(
            label=f"⬇️ Descargar Selección CSV ({selected_profile})",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"flame_in_freefall_{selected_profile.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )

    # --- PESTAÑA 3: AUDITORÍA Y BRECHAS ---
    with tab_gap:
        st.header("🔍 Auditoría de Cobertura y Brechas (Gap Analysis) — Repositorio NASA PSI")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Cobertura Catálogo PSI", "16 / 26 (61.5%)", "8 pendientes + 2 excluidos")
        g2.metric("Brecha Crítica Luz Verde", "3 Estudios", "SAFFIRE-I, II y III (Cygnus)")
        g3.metric("Brecha Calibración CFD", "4 Estudios", "PSI-62, PSI-60, PSI-115, PSI-117")
        g4.metric("Ruido Bloqueado", "3 Estudios (Rojo)", "PSI-108, PSI-47, PSI-181")

        filter_status = st.multiselect(
            "Filtrar auditoría de 26 registros por estado:",
            options=["PENDING_INGESTION", "INGESTED_ACTIVE", "EXCLUDED_AUDIT"],
            default=["PENDING_INGESTION"],
        )
        audit_view = master_26_df[master_26_df["ingestion_status"].isin(filter_status)][[
            "investigation_id", "acronym", "traffic_light", "ingestion_status",
            "safety_pillar", "hardware", "irl_score_max", "download_priority", "gap_notes", "psi_url",
        ]]
        st.dataframe(audit_view, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("🤖 Asistente de Consulta de Citas DOI (NASA SMD Open Source Science)")
        default_q = "¿Qué estudios tienen DOI verificado actualmente y cuáles faltan por extraer?"
        if "doi_query_input" not in st.session_state:
            st.session_state["doi_query_input"] = default_q

        b1, b2, b3 = st.columns(3)
        if b1.button("🔎 Ver DOIs verificados vs. pendientes"):
            st.session_state["doi_query_input"] = "¿Qué estudios tienen DOI verificado actualmente y cuáles faltan por extraer?"
        if b2.button("🔥 Citas SAFFIRE-I/II/III"):
            st.session_state["doi_query_input"] = "Dame las citas DOI de SAFFIRE-I, SAFFIRE-II y SAFFIRE-III (PSI-98, PSI-99, PSI-100)"
        if b3.button("🧪 Citas FLEX / PSI-142"):
            st.session_state["doi_query_input"] = "Muéstrame los DOIs verificados de PSI-142 y citas de FLEX PSI-68 y PSI-69"

        qc1, qc2 = st.columns([3, 1])
        user_doi_query = qc1.text_input("Consulta sobre citas DOI o estudios PSI:", key="doi_query_input")
        citation_fmt = qc2.selectbox("Formato de Cita", ["APA", "IEEE", "BibTeX"], index=0)

        if user_doi_query.strip():
            doi_res = query_doi_knowledge_base(user_doi_query, citation_style=citation_fmt)
            st.success(f"**Diagnóstico ({doi_res['matched_count']} registros):** {doi_res['intent_summary']}")
            for rec in doi_res["records"]:
                st.markdown(
                    f'<div class="doi-card"><strong>{rec["investigation_id"]} — {rec["acronym"]}</strong> '
                    f'| Semáforo: <strong>{rec["traffic_light"]}</strong> | Estado: <code>{rec["ingestion_status"]}</code><br>'
                    f'<small><strong>DOI:</strong> {rec["doi"]} • <a href="{rec["psi_url"]}" target="_blank" style="color:#38BDF8;">Abrir ficha NASA PSI ↗</a></small></div>',
                    unsafe_allow_html=True,
                )
                st.code(rec["formatted_citation"], language="bibtex" if citation_fmt == "BibTeX" else "text")

        st.markdown("---")
        st.subheader("📑 Exportar Informe Técnico HTML para el Jurado")
        rc1, rc2, rc3 = st.columns([2, 2, 1])
        team_in = rc1.text_input("Equipo / Proyecto", value="DROP TABLE USERS — Flame in Freefall")
        mission_in = rc2.text_input("Escenario Objetivo", value="Hábitats Lunares Artemis (<= 10.2 psi, >= 30% O2)")
        inc_app = rc3.checkbox("Incluir Apéndice DOI", value=True)
        html_out = generate_jury_html_report(df_full, team_in, mission_in, inc_app)
        st.download_button(
            label="🌐 Descargar Informe Técnico HTML (.html)",
            data=html_out.encode("utf-8"),
            file_name="Flame_in_Freefall_Jury_Report.html",
            mime="text/html",
        )


if __name__ == "__main__":
    main()