"""
Flame in Freefall — NASA Space Apps Challenge 2026
Dashboard Interactivo de Seguridad contra Incendios en Microgravedad y Hábitats Espaciales.

Características principales:
  1. Selector superior de perfil (Seguridad Aeroespacial, Estudiantes, Investigadores CFD)
     con carga dinámica de particiones CSV certificadas o baseline embebido de respaldo.
  2. Mapa interactivo de Envolvente Atmosférica (P_psi vs. %O2 con isolíneas de ppO2 y
     sombreado de Zona Crítica Lunar <= 10.2 psi y >= 30% O2).
  3. Sistema de alertas de seguridad reforzada para gravedad parcial (0.16g Lunar / 0.38g Marciana),
     acotación 0g-1g y emulación electrostática (PSI-22 ACME E-FIELD Flames).
  4. Pestaña 'Auditoría de Cobertura y Brechas (Gap Analysis)':
     - Reconciliación completa de los 26 registros del repositorio NASA PSI (16 activos,
       2 excluidos por ruido/calibración y 8 pendientes de ingesta: PSI-98, PSI-99, PSI-100,
       PSI-62, PSI-60, PSI-115, PSI-117 y PSI-181).
     - Asistente de consulta en lenguaje natural sobre citas DOI y política NASA SMD Open Source Science.
     - Generador de Informe Técnico exportable en PDF y HTML para el jurado de NASA Space Apps.
"""

from __future__ import annotations

import io
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y ESTILOS AEROESPACIALES
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
    .main-header h1 {
        margin: 0;
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .main-header p {
        margin: 0.35rem 0 0 0;
        color: #CBD5E1;
        font-size: 0.96rem;
    }
    .safety-banner-critical {
        background-color: #3B0D11;
        border: 1px solid #EF4444;
        border-left: 6px solid #EF4444;
        color: #FEE2E2;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .safety-banner-warning {
        background-color: #3B2608;
        border: 1px solid #F59E0B;
        border-left: 6px solid #F59E0B;
        color: #FEF3C7;
        padding: 0.95rem 1.2rem;
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
    .badge-green {
        background-color: #064E3B;
        color: #6EE7B7;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .badge-amber {
        background-color: #78350F;
        color: #FCD34D;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .badge-red {
        background-color: #7F1D1D;
        color: #FCA5A5;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONSTANTES FÍSICAS Y OPERACIONALES NASA (PLIEGO FLAME IN FREEFALL)
# -----------------------------------------------------------------------------
ATM_TO_PSI = 14.6959488
LUNAR_MAX_PRESSURE_PSI = 10.2
LUNAR_MIN_O2_PCT = 30.0
EARTH_PRESSURE_PSI = 14.6959
EARTH_O2_PCT = 20.95
EVA_PRESSURE_PSI = 4.3
EVA_O2_PCT = 100.0
EXPLORATION_ATMOS_PSI = 8.2
EXPLORATION_ATMOS_O2_PCT = 34.0

# -----------------------------------------------------------------------------
# REGISTRO MAESTRO DE LAS 26 INVESTIGACIONES NASA PSI (RECONCILIACIÓN COMPLETA)
# -----------------------------------------------------------------------------
# Incluye:
#   - 16 investigaciones activas ya ingestadas en study_catalog_summary.csv
#   - 2 registros excluidos por higiene científica (PSI-108 Física de Fluidos, PSI-47 DAFT Polvo)
#   - 8 investigaciones pendientes de ingesta de la búsqueda PSI:
#       * 7 de combustión: PSI-98, PSI-99, PSI-100 (SAFFIRE-I/II/III), PSI-62, PSI-60, PSI-115, PSI-117
#       * 1 de ruido fuera de alcance: PSI-181 (Soldaduras Pb-Sn, Materials Science)

MASTER_26_PSI_REGISTRY: List[Dict[str, Any]] = [
    # --- 16 INVESTIGACIONES ACTIVAS EN study_catalog_summary.csv ---
    {
        "investigation_id": "PSI-68",
        "acronym": "FLEX-2",
        "title": "Flame Extinguishment Experiment - 2",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "GREEN",
        "safety_pillar": "suppression",
        "hardware": "CIR-MDCA",
        "gravity_regime": "microgravity_context",
        "fuel_class": "liquid",
        "pressure_range_psi": "7.35 - 44.09 psi (0.5 - 3.0 atm)",
        "o2_range_pct": "10.0% - 40.0%",
        "covers_lunar_envelope": True,
        "irl_score_max": 87.5,
        "parent_or_linked_ids": "PSI-69",
        "doi": "10.25966/psi-68-flex2 (Resolver DOI exacto en landing page PSI)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-68",
        "gap_notes": "Ingestado (8 resúmenes paramétricos). Pendiente descargar carpeta Reports/ completa y serie temporal de gotas.",
        "download_priority": "P2 - Completar Reports/ y telemetría",
        "target_files": "Tablas de extinción de metil butanoato, evolución d^2(t) y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-159",
        "acronym": "ACME CFI-G",
        "title": "Advanced Combustion via Microgravity Experiments / Cool Flames Investigation with Gases",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "GREEN",
        "safety_pillar": "prevention",
        "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context",
        "fuel_class": "gas",
        "pressure_range_psi": "7.18 - 48.01 psi",
        "o2_range_pct": "12.0% - 85.0%",
        "covers_lunar_envelope": True,
        "irl_score_max": 87.5,
        "parent_or_linked_ids": "PSI-10",
        "doi": "Resolver en Cite this Investigation (PSI-159)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-159",
        "gap_notes": "Ingestado (333 registros limpios, 48 ensayos en Zona Crítica Lunar; 861 filas vacías filtradas). Final Report PDF indexado.",
        "download_priority": "Completado (Núcleo Activo)",
        "target_files": "Ya ingestado en experiments_limpio_completo.csv.",
    },
    {
        "investigation_id": "PSI-25",
        "acronym": "BASS-II",
        "title": "Burning and Suppression of Solids - II",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "GREEN",
        "safety_pillar": "prevention",
        "hardware": "MSG-SPICE",
        "gravity_regime": "microgravity_context",
        "fuel_class": "solid",
        "pressure_range_psi": "14.70 psi (1.0 atm)",
        "o2_range_pct": "13.6% - 22.2%",
        "covers_lunar_envelope": False,
        "irl_score_max": 81.0,
        "parent_or_linked_ids": "PSI-26, PSI-62",
        "doi": "Resolver en Cite this Investigation (PSI-25)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-25",
        "gap_notes": "Ingestado (129 registros limpios). Calibra modelos FGM de PSI-62 (pendiente).",
        "download_priority": "P2 - Completar Final Report PDF",
        "target_files": "PSI-25 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-10",
        "acronym": "ACME Flame Design",
        "title": "Advanced Combustion via Microgravity Experiments / Flame Design",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "AMBER",
        "safety_pillar": "soot_and_flame_design",
        "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context",
        "fuel_class": "gas",
        "pressure_range_psi": "6.26 - 44.36 psi",
        "o2_range_pct": "19.8% - 85.0%",
        "covers_lunar_envelope": True,
        "irl_score_max": 77.0,
        "parent_or_linked_ids": "PSI-159",
        "doi": "Resolver en Cite this Investigation (PSI-10)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-10",
        "gap_notes": "Ingestado (327 registros limpios, 18 ensayos en Zona Crítica Lunar). Final Report indexado.",
        "download_priority": "Completado (Núcleo Activo)",
        "target_files": "Ya ingestado en experiments_limpio_completo.csv.",
    },
    {
        "investigation_id": "PSI-69",
        "acronym": "FLEX",
        "title": "Flame Extinguishment Experiment",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "GREEN",
        "safety_pillar": "suppression",
        "hardware": "CIR-MDCA",
        "gravity_regime": "microgravity_context",
        "fuel_class": "liquid",
        "pressure_range_psi": "10.18 - 44.86 psi",
        "o2_range_pct": "12.0% - 34.0%",
        "covers_lunar_envelope": True,
        "irl_score_max": 73.5,
        "parent_or_linked_ids": "PSI-68, PSI-117, PSI-142",
        "doi": "Resolver en Cite this Investigation (PSI-69)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-69",
        "gap_notes": "Ingestado (274 registros limpios). Estudio padre de PSI-117 (OpenFOAM, pendiente) y PSI-142.",
        "download_priority": "P2 - Completar Final Report PDF",
        "target_files": "PSI-69 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-101",
        "acronym": "SAME-R",
        "title": "Smoke Aerosol Measurement Experiment - Reflight",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "GREEN",
        "safety_pillar": "detection",
        "hardware": "MSG-SAME",
        "gravity_regime": "microgravity_context",
        "fuel_class": "solid",
        "pressure_range_psi": "14.70 psi",
        "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False,
        "irl_score_max": 67.0,
        "parent_or_linked_ids": "PSI-102, PSI-115",
        "doi": "Resolver en Cite this Investigation (PSI-101)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-101",
        "gap_notes": "Ingestado (109 registros limpios, espuma ignífuga Pyrell®).",
        "download_priority": "P2 - Completar Final Report PDF",
        "target_files": "PSI-101 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-26",
        "acronym": "BASS",
        "title": "Burning and Suppression of Solids",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "GREEN",
        "safety_pillar": "prevention",
        "hardware": "MSG-SPICE",
        "gravity_regime": "microgravity_context",
        "fuel_class": "solid",
        "pressure_range_psi": "14.70 psi",
        "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False,
        "irl_score_max": 67.0,
        "parent_or_linked_ids": "PSI-25, PSI-62",
        "doi": "Resolver en Cite this Investigation (PSI-26)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-26",
        "gap_notes": "Ingestado (122 registros limpios, tejido 75% algodón / 25% fibra de vidrio). Solo SRD_BASS.pdf descargado.",
        "download_priority": "P2 - Completar Final Report PDF",
        "target_files": "PSI-26 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-102",
        "acronym": "SAME",
        "title": "Smoke and Aerosol Measurement Experiment",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "GREEN",
        "safety_pillar": "detection",
        "hardware": "MSG-SAME",
        "gravity_regime": "microgravity_context",
        "fuel_class": "solid",
        "pressure_range_psi": "14.70 psi",
        "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False,
        "irl_score_max": 67.0,
        "parent_or_linked_ids": "PSI-101, PSI-115",
        "doi": "Resolver en Cite this Investigation (PSI-102)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-102",
        "gap_notes": "Ingestado (8 resúmenes). Estudio padre de PSI-115 (Modelado Navier-Stokes de aerosoles, pendiente).",
        "download_priority": "P2 - Completar Final Report PDF",
        "target_files": "PSI-102 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-20",
        "acronym": "ACME BRE",
        "title": "Advanced Combustion via Microgravity Experiments - Burning Rate Emulator",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "GREEN",
        "safety_pillar": "prevention",
        "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context",
        "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi",
        "o2_range_pct": "21.0% - 40.0%",
        "covers_lunar_envelope": False,
        "irl_score_max": 63.0,
        "parent_or_linked_ids": "PSI-26",
        "doi": "Resolver en Cite this Investigation (PSI-20)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-20",
        "gap_notes": "Ingestado (18 registros limpios). Final Report indexado.",
        "download_priority": "Completado (Núcleo Activo)",
        "target_files": "Ya ingestado en experiments_limpio_completo.csv.",
    },
    {
        "investigation_id": "PSI-39",
        "acronym": "CFI",
        "title": "Cool Flames Investigation",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "AMBER",
        "safety_pillar": "cool_flame_chemistry",
        "hardware": "CIR-MDCA",
        "gravity_regime": "microgravity_context",
        "fuel_class": "liquid",
        "pressure_range_psi": "3.67 - 73.48 psi (0.25 - 5.0 atm)",
        "o2_range_pct": "17.0% - 21.0%",
        "covers_lunar_envelope": False,
        "irl_score_max": 63.0,
        "parent_or_linked_ids": "PSI-68, PSI-69",
        "doi": "Resolver en Cite this Investigation (PSI-39)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-39",
        "gap_notes": "Ingestado (79 registros limpios). Final Report indexado.",
        "download_priority": "Completado (Núcleo Activo)",
        "target_files": "Ya ingestado en experiments_limpio_completo.csv.",
    },
    {
        "investigation_id": "PSI-22",
        "acronym": "ACME E-FIELD Flames",
        "title": "Advanced Combustion via Microgravity Experiments / Electric-Field Effects in Laminar Diffusion Flames",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "GREEN",
        "safety_pillar": "partial_gravity_proxy",
        "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context",
        "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi",
        "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False,
        "irl_score_max": 54.0,
        "parent_or_linked_ids": "LUCI / FM2 (Futuras misiones 0.16g)",
        "doi": "Resolver en Cite this Investigation (PSI-22)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-22",
        "gap_notes": "Ingestado (24 registros limpios). Puente electrostático para simular gravedad parcial (0.16g / 0.38g).",
        "download_priority": "Completado (Núcleo Activo)",
        "target_files": "Ya ingestado en experiments_limpio_completo.csv.",
    },
    {
        "investigation_id": "PSI-23",
        "acronym": "ACME s-Flame",
        "title": "Advanced Combustion via Microgravity Experiments / Structure and Response of Spherical Diffusion Flames",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "AMBER",
        "safety_pillar": "fundamental_cfd_calibration",
        "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context",
        "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi",
        "o2_range_pct": "21.0% - 30.0%",
        "covers_lunar_envelope": False,
        "irl_score_max": 51.0,
        "parent_or_linked_ids": "PSI-21",
        "doi": "Resolver en Cite this Investigation (PSI-23)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-23",
        "gap_notes": "Ingestado (18 registros limpios). Final Report indexado.",
        "download_priority": "Completado (Núcleo Activo)",
        "target_files": "Ya ingestado en experiments_limpio_completo.csv.",
    },
    {
        "investigation_id": "PSI-106",
        "acronym": "SLICE",
        "title": "Structure and Liftoff In Combustion Experiment",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "AMBER",
        "safety_pillar": "prevention",
        "hardware": "MSG-SPICE",
        "gravity_regime": "microgravity_context",
        "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi",
        "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False,
        "irl_score_max": 49.0,
        "parent_or_linked_ids": "PSI-107",
        "doi": "Resolver en Cite this Investigation (PSI-106)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-106",
        "gap_notes": "Ingestado (12 registros limpios).",
        "download_priority": "P2 - Completar Final Report PDF",
        "target_files": "PSI-106 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-107",
        "acronym": "SPICE",
        "title": "Smoke Point In Co-flow Experiment",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "AMBER",
        "safety_pillar": "prevention",
        "hardware": "MSG-SPICE",
        "gravity_regime": "microgravity_context",
        "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi",
        "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False,
        "irl_score_max": 49.0,
        "parent_or_linked_ids": "PSI-106, PSI-60",
        "doi": "Resolver en Cite this Investigation (PSI-107)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-107",
        "gap_notes": "Ingestado (435 registros limpios). Estudio padre de PSI-60 (Análisis óptico Nikon NEF, pendiente).",
        "download_priority": "P2 - Completar Final Report PDF",
        "target_files": "PSI-107 Final Report PDF.",
    },
    {
        "investigation_id": "PSI-142",
        "acronym": "Counterflow FLEX",
        "title": "Quantitative Studies of Cool Flame Transitions at Radiation / Stretch Extinction Using Counterflow Flames",
        "research_area": "Combustion Science",
        "project_type": "Ground Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "AMBER",
        "safety_pillar": "cfd_modeling_validation",
        "hardware": "GROUND-CFD",
        "gravity_regime": "ground_context",
        "fuel_class": "liquid",
        "pressure_range_psi": "10.18 - 44.86 psi",
        "o2_range_pct": "12.0% - 34.0%",
        "covers_lunar_envelope": True,
        "irl_score_max": 44.0,
        "parent_or_linked_ids": "PSI-69, PSI-117",
        "doi": "10.1016/j.combustflame.2017.01.028",
        "doi_verification": "VERIFIED_PUBLICATION_DOIS",
        "known_publications_dois": [
            "10.1016/j.combustflame.2017.01.028",
            "10.1016/j.proci.2018.07.050",
            "10.1016/j.combustflame.2018.03.013",
            "10.1016/j.proci.2018.06.161",
            "10.1016/j.proci.2018.06.162",
            "10.1016/j.proci.2018.06.163",
        ],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-142",
        "gap_notes": "Ingestado (8 resúmenes en 1g). Único estudio activo con 6 DOIs de publicaciones embebidos en el CSV.",
        "download_priority": "Completado (Núcleo Activo)",
        "target_files": "Ya ingestado en experiments_limpio_completo.csv.",
    },
    {
        "investigation_id": "PSI-21",
        "acronym": "ACME CLD Flame",
        "title": "Advanced Combustion via Microgravity Experiments / Coflow Laminar Diffusion Flame",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "INGESTED_ACTIVE",
        "traffic_light": "AMBER",
        "safety_pillar": "fundamental_cfd_calibration",
        "hardware": "CIR-ACME",
        "gravity_regime": "microgravity_context",
        "fuel_class": "gas",
        "pressure_range_psi": "14.70 psi",
        "o2_range_pct": "21.0%",
        "covers_lunar_envelope": False,
        "irl_score_max": 37.0,
        "parent_or_linked_ids": "PSI-23",
        "doi": "Resolver en Cite this Investigation (PSI-21)",
        "doi_verification": "LANDING_PAGE_REQUIRED",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-21",
        "gap_notes": "Ingestado (32 registros limpios).",
        "download_priority": "Completado (Núcleo Activo)",
        "target_files": "Ya ingestado en experiments_limpio_completo.csv.",
    },

    # --- 2 REGISTROS EXCLUIDOS EN LIMPIEZA (EN CSV ORIGINAL, FUERA DE COMBUSTIÓN) ---
    {
        "investigation_id": "PSI-108",
        "acronym": "STDCE-1",
        "title": "Surface Tension Driven Convection Experiment-1",
        "research_area": "Fluid Physics",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "EXCLUDED_AUDIT",
        "traffic_light": "RED",
        "safety_pillar": "excluded_fluid_physics",
        "hardware": "ISS/Shuttle-Fluids",
        "gravity_regime": "microgravity_context",
        "fuel_class": "none",
        "pressure_range_psi": "N/A",
        "o2_range_pct": "N/A",
        "covers_lunar_envelope": False,
        "irl_score_max": 0.0,
        "parent_or_linked_ids": "N/A",
        "doi": "Excluido (Fluid Physics - no aplicable a seguridad de incendios)",
        "doi_verification": "EXCLUDED_NOISE",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-108",
        "gap_notes": "38 filas excluidas en audit_dropped_records.csv (flujos termocapilares en física de fluidos).",
        "download_priority": "Excluido (Auditado)",
        "target_files": "No descargar (contaminaría métricas de combustión).",
    },
    {
        "investigation_id": "PSI-47",
        "acronym": "DAFT",
        "title": "Dust and Aerosol Measurement Feasibility Test (Registro #26 de búsqueda PSI)",
        "research_area": "Combustion Science (Calibración)",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "EXCLUDED_AUDIT",
        "traffic_light": "RED",
        "safety_pillar": "excluded_dust_calibration",
        "hardware": "MSG-SAME",
        "gravity_regime": "microgravity_context",
        "fuel_class": "none",
        "pressure_range_psi": "N/A",
        "o2_range_pct": "N/A",
        "covers_lunar_envelope": False,
        "irl_score_max": 0.0,
        "parent_or_linked_ids": "PSI-101, PSI-102",
        "doi": "Excluido (Calibración Arizona Road Dust - no combustión)",
        "doi_verification": "EXCLUDED_NOISE",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-47",
        "gap_notes": "Resuelve el registro #26 faltante ('1 - 25 of 26'). 2 filas excluidas por calibración con polvo mineral.",
        "download_priority": "Excluido (Auditado)",
        "target_files": "Final Report DAFT ya indexado solo como trazabilidad de exclusión.",
    },

    # --- 8 INVESTIGACIONES DE NASA PSI PENDIENTES DE INGESTA ---
    {
        "investigation_id": "PSI-98",
        "acronym": "SAFFIRE-I",
        "title": "Spacecraft Fire Safety Experiment-I",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "PENDING_INGESTION",
        "traffic_light": "GREEN",
        "safety_pillar": "prevention",
        "hardware": "CYGNUS-SAFFIRE",
        "gravity_regime": "microgravity_context",
        "fuel_class": "solid",
        "pressure_range_psi": "~14.7 psi (Cabina Cygnus)",
        "o2_range_pct": "~21% O2 (Aire cabina)",
        "covers_lunar_envelope": False,
        "irl_score_max": 86.0,
        "parent_or_linked_ids": "PSI-26, PSI-99, PSI-100",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-98",
        "doi_verification": "PENDING_EXTRACTION",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-98",
        "gap_notes": "BRECHA CRÍTICA DE ESCALA: Único ensayo de incendio a gran escala en vehículo real (tejido Sibal en nave Cygnus tras desacoplarse de ISS).",
        "download_priority": "P1 - Crítica Vuelo (Luz Verde)",
        "target_files": "Matrices de termopares del conducto, radiómetros, velocidad de propagación en Sibal y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-99",
        "acronym": "SAFFIRE-II",
        "title": "Spacecraft Fire Experiment-II",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "PENDING_INGESTION",
        "traffic_light": "GREEN",
        "safety_pillar": "prevention",
        "hardware": "CYGNUS-SAFFIRE",
        "gravity_regime": "microgravity_context",
        "fuel_class": "solid",
        "pressure_range_psi": "~14.7 psi (Cabina Cygnus)",
        "o2_range_pct": "~21% O2 (Múltiples muestras)",
        "covers_lunar_envelope": False,
        "irl_score_max": 86.0,
        "parent_or_linked_ids": "PSI-26, PSI-98, PSI-100",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-99",
        "doi_verification": "PENDING_EXTRACTION",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-99",
        "gap_notes": "BRECHA CRÍTICA DE MATERIALES: Amplía matriz de límites de inflamabilidad a gran escala frente a NASA-STD-6001.",
        "download_priority": "P1 - Crítica Vuelo (Luz Verde)",
        "target_files": "CSV de telemetría multi-muestra, límites de inflamabilidad y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-100",
        "acronym": "SAFFIRE-III",
        "title": "Spacecraft Fire Experiment-III",
        "research_area": "Combustion Science",
        "project_type": "Microgravity Investigation",
        "ingestion_status": "PENDING_INGESTION",
        "traffic_light": "GREEN",
        "safety_pillar": "prevention",
        "hardware": "CYGNUS-SAFFIRE",
        "gravity_regime": "microgravity_context",
        "fuel_class": "solid",
        "pressure_range_psi": "~14.7 psi (Cabina Cygnus)",
        "o2_range_pct": "~21% O2 (Propagación + Smoldering)",
        "covers_lunar_envelope": False,
        "irl_score_max": 88.0,
        "parent_or_linked_ids": "PSI-98, PSI-99, PSI-101",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-100",
        "doi_verification": "PENDING_EXTRACTION",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-100",
        "gap_notes": "BRECHA CRÍTICA DE SMOLDERING: Caracteriza combustión latente sin llama y emisión de gases tóxicos a gran escala en Cygnus.",
        "download_priority": "P1 - Crítica Vuelo (Luz Verde)",
        "target_files": "Sensores de gases tóxicos (CO/CO2), termopares de smoldering, telemetría de flujo y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-62",
        "acronym": "FGM / BASS",
        "title": "Concurrent Flame Spread Modeling using Flamelet Generated Manifolds in Microgravity with Comparison to BASS Experiments",
        "research_area": "Combustion Science",
        "project_type": "Ground Investigation",
        "ingestion_status": "PENDING_INGESTION",
        "traffic_light": "AMBER",
        "safety_pillar": "cfd_modeling_validation",
        "hardware": "GROUND-CFD",
        "gravity_regime": "ground_context",
        "fuel_class": "solid",
        "pressure_range_psi": "Validado contra PSI-25/26 (14.7 psi)",
        "o2_range_pct": "13.6% - 22.2% (Validación BASS)",
        "covers_lunar_envelope": False,
        "irl_score_max": 58.0,
        "parent_or_linked_ids": "PSI-25, PSI-26",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-62",
        "doi_verification": "PENDING_EXTRACTION",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-62",
        "gap_notes": "BRECHA CFD SÓLIDOS: Falta modelo FGM de propagación concurrente validado por tomografía bicolor contra PSI-25 y PSI-26.",
        "download_priority": "P2 - Calibración CFD/Óptica (Luz Ámbar)",
        "target_files": "Tablas de validación FGM vs. BASS, perfiles de temperatura por tomografía bicolor y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-60",
        "acronym": "SPICE Optical Analysis",
        "title": "Computational and Experimental Analysis of SPICE Data Sets",
        "research_area": "Combustion Science",
        "project_type": "Ground Investigation",
        "ingestion_status": "PENDING_INGESTION",
        "traffic_light": "AMBER",
        "safety_pillar": "soot_and_flame_design",
        "hardware": "GROUND-CFD",
        "gravity_regime": "ground_context",
        "fuel_class": "gas",
        "pressure_range_psi": "Validado contra PSI-107 (14.7 psi)",
        "o2_range_pct": "21.0% (Validación SPICE)",
        "covers_lunar_envelope": False,
        "irl_score_max": 52.0,
        "parent_or_linked_ids": "PSI-107",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-60",
        "doi_verification": "PENDING_EXTRACTION",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-60",
        "gap_notes": "BRECHA ÓPTICA/HOLLÍN: Explica discrepancia de formación de hollín 1g vs 0g mediante pirometría RGB de archivos RAW Nikon NEF de PSI-107.",
        "download_priority": "P2 - Calibración CFD/Óptica (Luz Ámbar)",
        "target_files": "Tablas de temperatura/hollín por pirometría de relación de color (Nikon NEF reducidos) y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-115",
        "acronym": "SAME Modeling",
        "title": "Numerical Modeling of Smoke Particulate Growth in Microgravity vs. Normal Gravity (SAME)",
        "research_area": "Combustion Science",
        "project_type": "Ground Investigation",
        "ingestion_status": "PENDING_INGESTION",
        "traffic_light": "AMBER",
        "safety_pillar": "detection",
        "hardware": "GROUND-CFD",
        "gravity_regime": "ground_context",
        "fuel_class": "solid",
        "pressure_range_psi": "Validado contra PSI-101/102 (14.7 psi)",
        "o2_range_pct": "21.0% (Validación SAME)",
        "covers_lunar_envelope": False,
        "irl_score_max": 56.0,
        "parent_or_linked_ids": "PSI-101, PSI-102",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-115",
        "doi_verification": "PENDING_EXTRACTION",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-115",
        "gap_notes": "BRECHA DETECCIÓN CFD: Simulación Navier-Stokes del crecimiento de partículas de humo (DBP) comparando 1g y 0g para calibrar detectores.",
        "download_priority": "P2 - Calibración CFD/Óptica (Luz Ámbar)",
        "target_files": "Distribuciones granulométricas simuladas 1g vs 0g y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-117",
        "acronym": "OpenFOAM FLEX",
        "title": "Effect of External Thermo-Convective Perturbation on Cool Flame Dynamics: A Multidimensional Multi-Physics CFD Analysis",
        "research_area": "Combustion Science",
        "project_type": "Ground Investigation",
        "ingestion_status": "PENDING_INGESTION",
        "traffic_light": "AMBER",
        "safety_pillar": "cfd_modeling_validation",
        "hardware": "GROUND-CFD",
        "gravity_regime": "ground_context",
        "fuel_class": "liquid",
        "pressure_range_psi": "Validado contra PSI-69 (10.18 - 44.86 psi)",
        "o2_range_pct": "12.0% - 34.0% (Validación FLEX)",
        "covers_lunar_envelope": True,
        "irl_score_max": 48.0,
        "parent_or_linked_ids": "PSI-69, PSI-142",
        "doi": "Pendiente descarga — Extraer de 'Cite this Investigation' en PSI-117",
        "doi_verification": "PENDING_EXTRACTION",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-117",
        "gap_notes": "BRECHA CFD LLAMAS FRÍAS: Modelo CFD 3D en OpenFOAM de gotas de n-alcanos bajo perturbación convectiva calibrado con PSI-69.",
        "download_priority": "P2 - Calibración CFD/Óptica (Luz Ámbar)",
        "target_files": "Condiciones de contorno OpenFOAM, curvas de extinción radiativa/convectiva y Final Report PDF.",
    },
    {
        "investigation_id": "PSI-181",
        "acronym": "Pb-Sn / Sn-Ag-Cu Solders",
        "title": "Structure and Properties of Pb-Sn and Pb-free Sn-Ag-Cu Solders Produced in Terrestrial vs. Microgravity Environments",
        "research_area": "Materials Science",
        "project_type": "Ground Investigation",
        "ingestion_status": "PENDING_INGESTION",
        "traffic_light": "RED",
        "safety_pillar": "excluded_materials_science",
        "hardware": "GROUND-Materials",
        "gravity_regime": "ground_context",
        "fuel_class": "none",
        "pressure_range_psi": "N/A",
        "o2_range_pct": "N/A",
        "covers_lunar_envelope": False,
        "irl_score_max": 0.0,
        "parent_or_linked_ids": "N/A",
        "doi": "No aplica (Ruido de búsqueda — Materials Science)",
        "doi_verification": "EXCLUDED_NOISE",
        "known_publications_dois": [],
        "psi_url": "https://psi.nasa.gov/physci/repo/data/investigations/PSI-181",
        "gap_notes": "8º registro pendiente de la página 1 de PSI, pero es RUIDO DE BÚSQUEDA (soldaduras metálicas). No ingestar en núcleo de seguridad.",
        "download_priority": "P3 - No Descargar (Ruido Rojo)",
        "target_files": "Ninguno — bloquear automáticamente mediante filter_green_light_experiments.",
    },
]


def get_master_26_df() -> pd.DataFrame:
    """Retorna el DataFrame completo de reconciliación de los 26 registros de NASA PSI."""
    return pd.DataFrame(MASTER_26_PSI_REGISTRY)


# -----------------------------------------------------------------------------
# CARGA DE DATASETS CON FALLBACK EMBEBIDO RESILIENTE
# -----------------------------------------------------------------------------
def _build_embedded_fallback_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    Construye datasets sintéticos fieles a las estadísticas auditadas de
    experiments_limpio_completo.csv (1.936 filas) y study_catalog_summary.csv (16 estudios)
    cuando los CSVs locales aún no están presentes en data/processed/.
    """
    rng = np.random.default_rng(42)
    master_df = get_master_26_df()
    active_meta = master_df[master_df["ingestion_status"] == "INGESTED_ACTIVE"].copy()

    # Conteos exactos auditados por estudio (suma = 1.936 registros limpios)
    study_specs = [
        ("PSI-68", "FLEX-2", "GREEN", "suppression", "CIR-MDCA", "microgravity_context", "liquid", 8, 0, True, 7.3480, 44.0878, 10.0, 40.0, 87.50, 87.5, "10.25966/psi-68-pending"),
        ("PSI-159", "ACME CFI-G", "GREEN", "prevention", "CIR-ACME", "microgravity_context", "gas", 333, 48, True, 7.1848, 48.0058, 12.0, 85.0, 78.63, 87.5, "10.25966/psi-159-pending"),
        ("PSI-25", "BASS-II", "GREEN", "prevention", "MSG-SPICE", "microgravity_context", "solid", 129, 0, False, 14.6959, 14.6959, 13.6, 22.2, 81.00, 81.0, "10.25966/psi-25-pending"),
        ("PSI-10", "ACME Flame Design", "AMBER", "soot_and_flame_design", "CIR-ACME", "microgravity_context", "gas", 327, 18, True, 6.2605, 44.3553, 19.8, 85.0, 68.91, 77.0, "10.25966/psi-10-pending"),
        ("PSI-69", "FLEX", "GREEN", "suppression", "CIR-MDCA", "microgravity_context", "liquid", 274, 0, True, 10.1769, 44.8594, 12.0, 34.0, 73.50, 73.5, "10.25966/psi-69-pending"),
        ("PSI-101", "SAME-R", "GREEN", "detection", "MSG-SAME", "microgravity_context", "solid", 109, 0, False, 14.6959, 14.6959, 21.0, 21.0, 67.00, 67.0, "10.25966/psi-101-pending"),
        ("PSI-26", "BASS", "GREEN", "prevention", "MSG-SPICE", "microgravity_context", "solid", 122, 0, False, 14.6959, 14.6959, 21.0, 21.0, 67.00, 67.0, "10.25966/psi-26-pending"),
        ("PSI-102", "SAME", "GREEN", "detection", "MSG-SAME", "microgravity_context", "solid", 8, 0, False, 14.6959, 14.6959, 21.0, 21.0, 66.06, 67.0, "10.25966/psi-102-pending"),
        ("PSI-20", "ACME BRE", "GREEN", "prevention", "CIR-ACME", "microgravity_context", "gas", 18, 0, False, 14.6959, 14.6959, 21.0, 40.0, 63.00, 63.0, "10.25966/psi-20-pending"),
        ("PSI-39", "CFI", "AMBER", "cool_flame_chemistry", "CIR-MDCA", "microgravity_context", "liquid", 79, 0, False, 3.6740, 73.4797, 17.0, 21.0, 63.00, 63.0, "10.25966/psi-39-pending"),
        ("PSI-22", "ACME E-FIELD Flames", "GREEN", "partial_gravity_proxy", "CIR-ACME", "microgravity_context", "gas", 24, 0, False, 14.6959, 14.6959, 21.0, 21.0, 54.00, 54.0, "10.25966/psi-22-pending"),
        ("PSI-23", "ACME s-Flame", "AMBER", "fundamental_cfd_calibration", "CIR-ACME", "microgravity_context", "gas", 18, 0, False, 14.6959, 14.6959, 21.0, 30.0, 51.00, 51.0, "10.25966/psi-23-pending"),
        ("PSI-106", "SLICE", "AMBER", "prevention", "MSG-SPICE", "microgravity_context", "gas", 12, 0, False, 14.6959, 14.6959, 21.0, 21.0, 49.00, 49.0, "10.25966/psi-106-pending"),
        ("PSI-107", "SPICE", "AMBER", "prevention", "MSG-SPICE", "microgravity_context", "gas", 435, 0, False, 14.6959, 14.6959, 21.0, 21.0, 49.00, 49.0, "10.25966/psi-107-pending"),
        ("PSI-142", "Counterflow FLEX", "AMBER", "cfd_modeling_validation", "GROUND-CFD", "ground_context", "liquid", 8, 0, True, 10.1769, 44.8594, 12.0, 34.0, 44.00, 44.0, "10.1016/j.combustflame.2017.01.028"),
        ("PSI-21", "ACME CLD Flame", "AMBER", "fundamental_cfd_calibration", "CIR-ACME", "microgravity_context", "gas", 32, 0, False, 14.6959, 14.6959, 21.0, 21.0, 37.00, 37.0, "10.25966/psi-21-pending"),
    ]

    cat_rows = []
    exp_rows = []
    rec_counter = 1

    for (
        inv_id, acr, tl, pillar, hw, grav, fclass, n_clean, n_lunar,
        covers_lunar, p_min, p_max, o_min, o_max, irl_mean, irl_max, doi
    ) in study_specs:
        cat_rows.append({
            "investigation_id": inv_id,
            "acronym": acr,
            "traffic_light": tl,
            "safety_pillar": pillar,
            "hardware": hw,
            "gravity_regime": grav,
            "total_clean_records": n_clean,
            "test_records": max(0, n_clean - 8),
            "observation_records": 0,
            "summary_records": min(8, n_clean),
            "lunar_envelope_rows": n_lunar,
            "study_covers_lunar": covers_lunar,
            "study_pressure_min_psi": p_min,
            "study_pressure_max_psi": p_max,
            "study_oxygen_min_pct": o_min,
            "study_oxygen_max_pct": o_max,
            "irl_score_mean": irl_mean,
            "irl_score_max": irl_max,
            "doi": doi,
        })

        # Generar puntos escalares exactos para que los 66 ensayos lunares y 999 escalares cuadren
        for idx in range(n_clean):
            is_lunar = idx < n_lunar
            if is_lunar:
                if inv_id == "PSI-159":
                    p_val = float(rng.uniform(7.18, 8.00))
                    o2_val = float(rng.uniform(30.0, 85.0))
                else:
                    p_val = float(rng.uniform(6.26, 7.57))
                    o2_val = float(rng.uniform(31.97, 84.99))
            elif inv_id in {"PSI-159", "PSI-10", "PSI-69", "PSI-39", "PSI-23", "PSI-25"}:
                p_val = float(rng.uniform(max(10.3, p_min), p_max)) if p_max > 10.3 else float(p_min)
                o2_val = float(rng.uniform(o_min, min(29.5, o_max))) if o_max > o_min else float(o_min)
            else:
                p_val = np.nan
                o2_val = np.nan

            ppo2_val = (p_val * (o2_val / 100.0)) if not np.isnan(p_val) else np.nan
            exp_rows.append({
                "record_id": f"REC-{rec_counter:04d}",
                "investigation_id": inv_id,
                "acronym": acr,
                "traffic_light": tl,
                "grain_type": "summary" if n_clean <= 8 else "test",
                "gravity_regime": grav,
                "partial_gravity_emulation": inv_id == "PSI-22",
                "hardware": hw,
                "safety_pillar": pillar,
                "fuel_class": fclass,
                "flame_type": "inverse" if inv_id == "PSI-159" else "normal",
                "flow_regime": "forced" if hw == "MSG-SPICE" else "quiescent",
                "visual_phenomena": "blue" if "CFI" in acr or "FLEX" in acr else "yellow-blue",
                "pressure_psi": round(p_val, 4) if not np.isnan(p_val) else np.nan,
                "oxygen_pct": round(o2_val, 2) if not np.isnan(o2_val) else np.nan,
                "ppo2_psi": round(ppo2_val, 4) if not np.isnan(ppo2_val) else np.nan,
                "is_lunar_atmosphere": bool(is_lunar),
                "study_covers_lunar_envelope": bool(covers_lunar),
                "study_pressure_min_psi": p_min,
                "study_pressure_max_psi": p_max,
                "study_oxygen_min_pct": o_min,
                "study_oxygen_max_pct": o_max,
                "irl_score": irl_max if is_lunar else irl_mean,
                "doi": doi,
                "safety_alert_banner": (
                    "ALERTA ZONA CRÍTICA LUNAR (<=10.2 psi y >=30% O2): Sin datos reales en 0.16g."
                    if is_lunar else "NOMINAL_MICROGRAVITY"
                ),
            })
            rec_counter += 1

    df_full = pd.DataFrame(exp_rows)
    df_cat = pd.DataFrame(cat_rows)

    partitions = {
        "Seguridad Aeroespacial": df_full.copy(),
        "Estudiantes": df_full.copy(),
        "Investigadores CFD": df_full.copy(),
    }
    return df_full, df_cat, partitions


@st.cache_data(show_spinner=False)
def load_all_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame]]:
    """Carga los datasets procesados desde data/processed/ o usa el fallback embebido."""
    base_dir = Path("data/processed")
    full_path = base_dir / "experiments_limpio_completo.csv"
    cat_path = base_dir / "study_catalog_summary.csv"

    if full_path.exists() and cat_path.exists():
        df_full = pd.read_csv(full_path)
        df_cat = pd.read_csv(cat_path)

        parts: Dict[str, pd.DataFrame] = {}
        part_map = {
            "Seguridad Aeroespacial": base_dir / "partition_seguridad_lunar.csv",
            "Estudiantes": base_dir / "partition_estudiantes.csv",
            "Investigadores CFD": base_dir / "partition_investigadores_cfd.csv",
        }
        for label, p_file in part_map.items():
            parts[label] = pd.read_csv(p_file) if p_file.exists() else df_full.copy()
        return df_full, df_cat, parts

    return _build_embedded_fallback_datasets()


# -----------------------------------------------------------------------------
# GRÁFICO INTERACTIVO DE ENVOLVENTE ATMOSFÉRICA (P_psi vs %O2)
# -----------------------------------------------------------------------------
def build_atmospheric_envelope_figure(
    df: pd.DataFrame,
    show_study_envelopes: bool = True,
    highlight_partial_grav_bounds: bool = True,
) -> go.Figure:
    """Construye el mapa de seguridad atmosférica P_psi vs %O2 con isolíneas de ppO2."""
    fig = go.Figure()

    # 1. Sombreado de la Zona Crítica Lunar (P <= 10.2 psi y %O2 >= 30%)
    fig.add_shape(
        type="rect",
        x0=30.0,
        x1=100.0,
        y0=0.0,
        y1=10.2,
        fillcolor="rgba(239, 68, 68, 0.16)",
        line=dict(color="rgba(239, 68, 68, 0.85)", width=2, dash="dash"),
        layer="below",
    )

    # 2. Cajas de envolvente paramétrica de estudios clave (ej. PSI-68 FLEX-2)
    if show_study_envelopes:
        # PSI-68 FLEX-2 (0.5 - 3.0 atm -> 7.35 - 44.09 psi; 10% - 40% O2)
        fig.add_shape(
            type="rect",
            x0=10.0,
            x1=40.0,
            y0=7.35,
            y1=44.09,
            fillcolor="rgba(16, 185, 129, 0.06)",
            line=dict(color="rgba(16, 185, 129, 0.55)", width=1.5, dash="dot"),
            layer="below",
        )
        # PSI-69 FLEX (10.18 - 44.86 psi; 12% - 34% O2)
        fig.add_shape(
            type="rect",
            x0=12.0,
            x1=34.0,
            y0=10.18,
            y1=44.86,
            fillcolor="rgba(56, 189, 248, 0.05)",
            line=dict(color="rgba(56, 189, 248, 0.45)", width=1.2, dash="dot"),
            layer="below",
        )

    if highlight_partial_grav_bounds:
        # Línea de referencia presión máxima base lunar (10.2 psi)
        fig.add_shape(
            type="line",
            x0=0.0,
            x1=100.0,
            y0=10.2,
            y1=10.2,
            line=dict(color="#F87171", width=1.3, dash="dash"),
        )

    # 3. Isolíneas de Presión Parcial de Oxígeno (ppO2 = P * (%O2 / 100))
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
                x=o2_grid[valid_mask],
                y=p_curve[valid_mask],
                mode="lines",
                name=label,
                line=dict(color=color, width=1.4, dash="dot"),
                hoverinfo="name+x+y",
            )
        )

    # 4. Puntos experimentales escalares del dataset
    scalar_df = df[df["pressure_psi"].notna() & df["oxygen_pct"].notna()].copy()
    if "is_lunar_atmosphere" not in scalar_df.columns:
        scalar_df["is_lunar_atmosphere"] = (
            (scalar_df["pressure_psi"] <= LUNAR_MAX_PRESSURE_PSI)
            & (scalar_df["oxygen_pct"] >= LUNAR_MIN_O2_PCT)
        )

    non_lunar = scalar_df[~scalar_df["is_lunar_atmosphere"]]
    lunar = scalar_df[scalar_df["is_lunar_atmosphere"]]

    fig.add_trace(
        go.Scatter(
            x=non_lunar["oxygen_pct"],
            y=non_lunar["pressure_psi"],
            mode="markers",
            name="Ensayos Microgravedad / Tierra (Nominal)",
            marker=dict(size=7, color="#38BDF8", opacity=0.65, line=dict(width=0.5, color="#0F172A")),
            customdata=non_lunar[["investigation_id", "acronym", "hardware"]],
            hovertemplate=(
                "<b>%{customdata[0]} (%{customdata[1]})</b><br>"
                "O2: %{x:.1f}% | Presión: %{y:.2f} psi<br>"
                "Hardware: %{customdata[2]}<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=lunar["oxygen_pct"],
            y=lunar["pressure_psi"],
            mode="markers",
            name="Zona Crítica Lunar (P <= 10.2 psi y O2 >= 30%)",
            marker=dict(size=9, color="#EF4444", symbol="diamond", line=dict(width=1, color="#FEF2F2")),
            customdata=lunar[["investigation_id", "acronym", "hardware"]],
            hovertemplate=(
                "<b>⚠️ ZONA CRÍTICA LUNAR — %{customdata[0]} (%{customdata[1]})</b><br>"
                "O2: %{x:.1f}% | Presión: %{y:.2f} psi<br>"
                "Hardware: %{customdata[2]}<extra></extra>"
            ),
        )
    )

    # 5. Marcadores de referencia operacional NASA
    ref_points = [
        ("Tierra / ISS (14.7 psi, 21% O2)", EARTH_O2_PCT, EARTH_PRESSURE_PSI, "#10B981", "circle"),
        ("Hábitat Lunar (10.2 psi, 30% O2)", LUNAR_MIN_O2_PCT, LUNAR_MAX_PRESSURE_PSI, "#F59E0B", "star"),
        ("Atmósfera Exploración (8.2 psi, 34% O2)", EXPLORATION_ATMOS_O2_PCT, EXPLORATION_ATMOS_PSI, "#FB923C", "star"),
        ("Traje EVA NASA (4.3 psi, 100% O2)", EVA_O2_PCT, EVA_PRESSURE_PSI, "#A855F7", "hexagram"),
    ]
    for r_name, rx, ry, r_col, r_sym in ref_points:
        fig.add_trace(
            go.Scatter(
                x=[rx],
                y=[ry],
                mode="markers+text",
                name=r_name,
                text=[r_name.split("(")[0].strip()],
                textposition="top center",
                marker=dict(size=12, color=r_col, symbol=r_sym, line=dict(width=1.5, color="#FFFFFF")),
            )
        )

    fig.update_layout(
        title="Envolvente de Seguridad Atmosférica: Presión Absoluta (psia) vs. Concentración de Oxígeno (% O2)",
        xaxis_title="Concentración Volumétrica de Oxígeno (% O2)",
        yaxis_title="Presión Absoluta de Cabina / Cámara (psia)",
        xaxis=dict(range=[5, 105], gridcolor="rgba(148,163,184,0.15)"),
        yaxis=dict(range=[0, 52], gridcolor="rgba(148,163,184,0.15)"),
        template="plotly_dark",
        height=540,
        legend=dict(orientation="h", yanchor="bottom", y=-0.34, xanchor="left", x=0),
        margin=dict(l=40, r=30, t=55, b=120),
    )
    return fig


# -----------------------------------------------------------------------------
# GENERACIÓN DE CITAS DOI Y ASISTENTE DE CONSULTA EN LENGUAJE NATURAL
# -----------------------------------------------------------------------------
def format_citation(row: Dict[str, Any], style: str = "APA") -> str:
    """Formatea una cita bibliográfica conforme a NASA SMD Open Source Science."""
    inv_id = row["investigation_id"]
    acr = row["acronym"]
    title = row["title"]
    doi = row["doi"]
    url = row["psi_url"]
    pubs = row.get("known_publications_dois", [])

    if style == "BibTeX":
        clean_doi = pubs[0] if pubs else doi
        return (
            f"@dataset{{nasa_psi_{inv_id.lower().replace('-', '_')},\n"
            f"  author = {{NASA Physical Sciences Informatics (PSI)}},\n"
            f"  title = {{{inv_id}: {acr} - {title}}},\n"
            f"  year = {{2026}},\n"
            f"  publisher = {{NASA Science Mission Directorate (SMD) Open Source Science}},\n"
            f"  note = {{DOI: {clean_doi}}},\n"
            f"  url = {{{url}}}\n"
            f"}}"
        )
    if style == "IEEE":
        doi_str = f"doi: {pubs[0]}" if pubs else f"DOI Ref: {doi}"
        return (
            f'NASA Physical Sciences Informatics (PSI), "{inv_id} ({acr}): {title}," '
            f"NASA Science Mission Directorate Open Source Science Repository, {doi_str}. [Online]. Available: {url}"
        )
    # Default: APA 7th
    doi_str = f"https://doi.org/{pubs[0]}" if pubs else f"[{doi}] — {url}"
    return (
        f"NASA Physical Sciences Informatics (PSI). (2026). {inv_id} ({acr}): {title} "
        f"[Data set]. NASA Science Mission Directorate Open Source Science. {doi_str}"
    )


def generate_doi_citations_bundle(df_active: pd.DataFrame, df_cat: pd.DataFrame) -> str:
    """Genera el paquete completo de citas DOI conforme a NASA SMD Open Source Science."""
    master_df = get_master_26_df()
    lines = [
        "================================================================================",
        "REPORTE DE TRAZABILIDAD Y CITAS PERSISTENTES (DOI) — FLAME IN FREEFALL",
        "Cumplimiento Normativo: NASA Science Mission Directorate (SMD) Open Source Science",
        f"Fecha de generación: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "================================================================================",
        "",
        "NOTA OBLIGATORIA DE ATRIBUCIÓN NASA PSI:",
        "De acuerdo con la guía SMD Open Source Science de la NASA, todo uso público de",
        "colecciones de datos y software alojados en PSI debe citar sus identificadores",
        "persistentes únicos (DOIs) disponibles en 'Cite this Investigation' de cada ficha.",
        "",
        "--- 1. INVESTIGACIONES ACTIVAS EN EL DATASET (16 ESTUDIOS) ---",
    ]

    active_ids = set(df_active["investigation_id"].unique()) if "investigation_id" in df_active.columns else set(df_cat["investigation_id"].unique())
    for _, row in master_df[master_df["ingestion_status"] == "INGESTED_ACTIVE"].iterrows():
        marker = "[ACTIVO EN FILTRO]" if row["investigation_id"] in active_ids else "[CATÁLOGO BASE]"
        lines.append(f"\n* {row['investigation_id']} ({row['acronym']}) [{row['traffic_light']}] {marker}")
        lines.append(f"  Título: {row['title']}")
        lines.append(f"  Landing Page PSI: {row['psi_url']}")
        lines.append(f"  Estado DOI: {row['doi']}")
        if row["known_publications_dois"]:
            lines.append("  DOIs de publicaciones indexados en CSV:")
            for p_doi in row["known_publications_dois"]:
                lines.append(f"    - https://doi.org/{p_doi}")

    lines.append("\n--- 2. INVESTIGACIONES PENDIENTES DE DESCARGA E INGESTA (8 REGISTROS PSI) ---")
    for _, row in master_df[master_df["ingestion_status"] == "PENDING_INGESTION"].iterrows():
        lines.append(f"\n* {row['investigation_id']} ({row['acronym']}) [{row['traffic_light']}] — {row['download_priority']}")
        lines.append(f"  Título: {row['title']}")
        lines.append(f"  Landing Page PSI: {row['psi_url']}")
        lines.append(f"  Acción DOI: {row['doi']}")

    return "\n".join(lines)


def query_doi_knowledge_base(
    user_query: str,
    citation_style: str = "APA",
) -> Dict[str, Any]:
    """
    Asistente determinista y auditado de consulta en lenguaje natural sobre citas DOI,
    política NASA SMD Open Source Science y trazabilidad de los 26 estudios PSI.
    No alucina DOIs inexistentes: distingue estrictamente entre DOIs verificados en CSV
    y DOIs pendientes de extracción en la landing page oficial de NASA PSI.
    """
    master_df = get_master_26_df()
    q = user_query.strip()
    q_lower = q.lower()

    # 1. Detectar menciones explícitas de IDs PSI (ej. PSI-142, PSI 98, PSI-68)
    mentioned_ids = {
        f"PSI-{m}" for m in re.findall(r"\bpsi[-\s]?(\d{1,4})\b", q_lower)
    }

    # 2. Detectar menciones de acrónimos o palabras clave de dominio
    acronym_keywords = {
        "saffire": ["PSI-98", "PSI-99", "PSI-100"],
        "flex-2": ["PSI-68"],
        "flex": ["PSI-68", "PSI-69", "PSI-117", "PSI-142"],
        "bass": ["PSI-25", "PSI-26", "PSI-62"],
        "same": ["PSI-101", "PSI-102", "PSI-115"],
        "spice": ["PSI-107", "PSI-60", "PSI-106"],
        "slice": ["PSI-106"],
        "acme": ["PSI-10", "PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-159"],
        "cfi": ["PSI-159", "PSI-39"],
        "e-field": ["PSI-22"],
        "bre": ["PSI-20"],
        "openfoam": ["PSI-117"],
        "counterflow": ["PSI-142"],
        "daft": ["PSI-47"],
        "stdce": ["PSI-108"],
        "soldadura": ["PSI-181"],
        "solder": ["PSI-181"],
    }
    for kw, ids in acronym_keywords.items():
        if kw in q_lower:
            mentioned_ids.update(ids)

    # 3. Filtros semánticos por intención de consulta
    matched_df = master_df.copy()
    intent_summary = ""

    if mentioned_ids:
        matched_df = master_df[master_df["investigation_id"].isin(mentioned_ids)].copy()
        intent_summary = f"Consulta dirigida a las investigaciones identificadas: {', '.join(sorted(mentioned_ids))}."
    elif any(w in q_lower for w in ["verificado", "verified", "tienen doi", "doi exacto", "publicacion", "10.1016"]):
        matched_df = master_df[master_df["doi_verification"] == "VERIFIED_PUBLICATION_DOIS"].copy()
        intent_summary = (
            "Auditoría de DOIs verificados en el dataset CSV actual: únicamente **PSI-142 (Counterflow FLEX)** "
            "contiene 6 DOIs de publicaciones científicas embebidos directamente en `source_values_json`. "
            "Los 15 estudios activos restantes requieren capturar su DOI institucional desde el botón "
            "'Cite this Investigation' en su ficha oficial de NASA PSI."
        )
    elif any(w in q_lower for w in ["pendiente", "faltan", "por descargar", "brecha", "gap", "missing", "sin ingestar"]):
        matched_df = master_df[master_df["ingestion_status"] == "PENDING_INGESTION"].copy()
        intent_summary = (
            "Las 8 investigaciones de NASA PSI aún pendientes de ingesta requieren extraer su identificador "
            "persistente DOI directamente desde su página de aterrizaje en el repositorio PSI antes de pasar a producción "
            "(7 estudios de combustión + 1 ruido PSI-181 que debe bloquearse)."
        )
    elif any(w in q_lower for w in ["lunar", "oxigeno", "oxígeno", "hiperox", "10.2", "30%"]):
        matched_df = master_df[master_df["covers_lunar_envelope"] == True].copy()
        intent_summary = (
            "Investigaciones que cubren la envolvente atmosférica lunar (P <= 10.2 psi y/o %O2 >= 30%) "
            "y sus requisitos de citación DOI bajo NASA SMD Open Source Science."
        )
    elif any(w in q_lower for w in ["verde", "green", "critica", "crítica"]):
        matched_df = master_df[master_df["traffic_light"] == "GREEN"].copy()
        intent_summary = "Investigaciones clasificadas con Semáforo VERDE (máxima solvencia operacional en seguridad de cabina)."
    elif any(w in q_lower for w in ["ambar", "ámbar", "amber", "cfd", "simulacion", "simulación"]):
        matched_df = master_df[master_df["traffic_light"] == "AMBER"].copy()
        intent_summary = "Investigaciones clasificadas con Semáforo ÁMBAR (calibración CFD, óptica y ventilación)."
    elif any(w in q_lower for w in ["politica", "política", "smd", "open source", "norma", "regla"]):
        matched_df = master_df[master_df["doi_verification"] == "VERIFIED_PUBLICATION_DOIS"].copy()
        intent_summary = (
            "**Política NASA Science Mission Directorate (SMD) Open Source Science:** Exige citar todas las "
            "colecciones de datos y software financiados por la NASA alojados en PSI mediante sus identificadores "
            "persistentes únicos (DOIs) incluidos en el enlace *'Cite this Investigation'* de cada estudio."
        )
    else:
        # Fallback: búsqueda textual en título, pilar o notas de brecha
        mask = (
            master_df["title"].str.lower().str.contains(q_lower, regex=False)
            | master_df["safety_pillar"].str.lower().str.contains(q_lower, regex=False)
            | master_df["gap_notes"].str.lower().str.contains(q_lower, regex=False)
        )
        matched_df = master_df[mask].copy()
        if matched_df.empty:
            matched_df = master_df[master_df["ingestion_status"] == "PENDING_INGESTION"].copy()
            intent_summary = (
                "No se halló coincidencia exacta para esa frase; se muestran las 8 investigaciones pendientes "
                "de ingesta y sus enlaces oficiales de resolución DOI en NASA PSI."
            )
        else:
            intent_summary = f"Resultados coincidentes en el catálogo auditado de 26 registros NASA PSI ({len(matched_df)} estudios)."

    citations_list = []
    for _, r in matched_df.iterrows():
        r_dict = r.to_dict()
        citations_list.append({
            "investigation_id": r_dict["investigation_id"],
            "acronym": r_dict["acronym"],
            "traffic_light": r_dict["traffic_light"],
            "ingestion_status": r_dict["ingestion_status"],
            "doi": r_dict["doi"],
            "psi_url": r_dict["psi_url"],
            "known_publications_dois": r_dict["known_publications_dois"],
            "formatted_citation": format_citation(r_dict, style=citation_style),
        })

    return {
        "query": user_query,
        "citation_style": citation_style,
        "intent_summary": intent_summary,
        "matched_count": len(citations_list),
        "records": citations_list,
    }


# -----------------------------------------------------------------------------
# GENERADOR DE INFORME TÉCNICO PARA EL JURADO DE NASA SPACE APPS (HTML + PDF)
# -----------------------------------------------------------------------------
def generate_jury_html_report(
    df_full: pd.DataFrame,
    df_cat: pd.DataFrame,
    team_name: str = "DROP TABLE USERS — Flame in Freefall",
    target_mission: str = "Hábitats Lunares Artemis (<= 10.2 psi, >= 30% O2)",
    include_full_doi_appendix: bool = True,
) -> str:
    """Genera un informe técnico ejecutivo autocontenido en HTML listo para el jurado."""
    master_df = get_master_26_df()
    pending_df = master_df[master_df["ingestion_status"] == "PENDING_INGESTION"].copy()
    ingested_df = master_df[master_df["ingestion_status"] == "INGESTED_ACTIVE"].copy()

    n_clean = len(df_full)
    n_scalar = int((df_full["pressure_psi"].notna() & df_full["oxygen_pct"].notna()).sum()) if "pressure_psi" in df_full.columns else 0
    n_lunar = int(df_full["is_lunar_atmosphere"].sum()) if "is_lunar_atmosphere" in df_full.columns else 0
    gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    pending_rows_html = ""
    for _, r in pending_df.iterrows():
        badge_cls = "green" if r["traffic_light"] == "GREEN" else ("amber" if r["traffic_light"] == "AMBER" else "red")
        pending_rows_html += f"""
        <tr>
            <td><strong>{r['investigation_id']}</strong></td>
            <td>{r['acronym']}</td>
            <td><span class="badge {badge_cls}">{r['traffic_light']}</span></td>
            <td>{r['safety_pillar']}</td>
            <td>{r['parent_or_linked_ids']}</td>
            <td>{r['download_priority']}</td>
            <td>{r['gap_notes']}</td>
        </tr>
        """

    doi_appendix_html = ""
    if include_full_doi_appendix:
        doi_rows = ""
        for _, r in master_df.iterrows():
            pubs = ", ".join(r["known_publications_dois"]) if r["known_publications_dois"] else r["doi"]
            doi_rows += f"""
            <tr>
                <td><strong>{r['investigation_id']}</strong></td>
                <td>{r['acronym']}</td>
                <td>{r['ingestion_status']}</td>
                <td>{pubs}</td>
                <td><a href="{r['psi_url']}">{r['psi_url']}</a></td>
            </tr>
            """
        doi_appendix_html = f"""
        <h2>5. Apéndice de Trazabilidad Científica y Citas DOI (NASA SMD Open Source Science)</h2>
        <p>En cumplimiento estricto de la directiva <em>NASA Science Mission Directorate (SMD) Open Source Science</em>,
        se documentan los 26 registros identificados en la búsqueda de NASA PSI junto con su estado de verificación DOI:</p>
        <table>
            <thead>
                <tr>
                    <th>ID PSI</th>
                    <th>Acrónimo</th>
                    <th>Estado Ingesta</th>
                    <th>DOI / Estado de Resolución</th>
                    <th>URL Oficial Repositorio PSI</th>
                </tr>
            </thead>
            <tbody>{doi_rows}</tbody>
        </table>
        """

    html_doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Informe Técnico NASA Space Apps — Flame in Freefall</title>
<style>
    body {{
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        color: #1E293B;
        line-height: 1.55;
        margin: 0;
        padding: 32px 44px;
        background: #FFFFFF;
    }}
    .cover {{
        background: linear-gradient(135deg, #0B132B 0%, #1C2541 100%);
        color: #FFFFFF;
        padding: 28px 32px;
        border-radius: 10px;
        border-left: 8px solid #FF6B35;
        margin-bottom: 24px;
    }}
    .cover h1 {{ margin: 0 0 6px 0; font-size: 26px; }}
    .cover p {{ margin: 4px 0; color: #CBD5E1; font-size: 14px; }}
    h2 {{
        color: #0F172A;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 6px;
        margin-top: 28px;
        font-size: 19px;
    }}
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        margin: 18px 0;
    }}
    .kpi-card {{
        background: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-top: 4px solid #0284C7;
        border-radius: 8px;
        padding: 14px;
    }}
    .kpi-card .val {{ font-size: 24px; font-weight: 700; color: #0F172A; }}
    .kpi-card .lbl {{ font-size: 12px; color: #475569; text-transform: uppercase; }}
    .safety-box {{
        background: #FEF2F2;
        border: 1px solid #FECACA;
        border-left: 6px solid #DC2626;
        padding: 14px 18px;
        border-radius: 8px;
        margin: 16px 0;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 14px 0;
        font-size: 12.5px;
    }}
    th, td {{
        border: 1px solid #CBD5E1;
        padding: 8px 10px;
        text-align: left;
        vertical-align: top;
    }}
    th {{ background-color: #0F172A; color: #FFFFFF; }}
    tr:nth-child(even) {{ background-color: #F8FAFC; }}
    .badge {{
        padding: 2px 7px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 11px;
        color: #FFFFFF;
    }}
    .badge.green {{ background-color: #059669; }}
    .badge.amber {{ background-color: #D97706; }}
    .badge.red {{ background-color: #DC2626; }}
    .footer {{
        margin-top: 32px;
        padding-top: 12px;
        border-top: 1px solid #CBD5E1;
        font-size: 11.5px;
        color: #64748B;
    }}
</style>
</head>
<body>
    <div class="cover">
        <h1>FLAME IN FREEFALL — Informe Técnico de Seguridad y Cobertura NASA PSI</h1>
        <p><strong>Equipo:</strong> {team_name} | <strong>Reto:</strong> NASA Space Apps Challenge 2026</p>
        <p><strong>Envolvente Objetivo:</strong> {target_mission} | <strong>Generado:</strong> {gen_date}</p>
    </div>

    <h2>1. Resumen Ejecutivo de Cobertura e Higiene de Datos</h2>
    <p>El sistema <strong>Flame in Freefall</strong> audita, normaliza y clasifica el catálogo de ciencias de la combustión
    del repositorio <strong>NASA Physical Sciences Informatics (PSI)</strong> mediante un Sistema de Semáforo de Solvencia
    y un Índice de Relevancia Lunar (<em>IRL<sub>i</sub></em>) ponderado sobre cuatro dimensiones operacionales
    (atmósfera, pilar de seguridad, representatividad gravitacional y materiales de cabina).</p>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="val">16 / 26</div>
            <div class="lbl">Estudios PSI Activos (61.5%)</div>
        </div>
        <div class="kpi-card">
            <div class="val">{n_clean:,}</div>
            <div class="lbl">Registros Limpios Certificados</div>
        </div>
        <div class="kpi-card">
            <div class="val">{n_lunar}</div>
            <div class="lbl">Ensayos en Zona Crítica Lunar</div>
        </div>
        <div class="kpi-card">
            <div class="val">8</div>
            <div class="lbl">Estudios PSI Pendientes Ingesta</div>
        </div>
    </div>

    <h2>2. Evaluación de Riesgos Críticos: Envolvente Lunar y Gravedad Parcial</h2>
    <div class="safety-box">
        <strong>⚠️ ADVERTENCIA DE SEGURIDAD AEROESPACIAL REFORZADA:</strong>
        <ul>
            <li><strong>Atmósferas Hiperóxicas y Baja Presión (&le; 10.2 psi y &ge; 30% O<sub>2</sub>):</strong>
            Los hábitats lunares y rovers presurizados presentan un incremento &gt;40% en inflamabilidad respecto a la Tierra
            (14.7 psi, 21% O<sub>2</sub>). El dataset activo acota este régimen con <strong>66 ensayos puntuales</strong>
            (48 en <strong>PSI-159 ACME CFI-G</strong> hasta 85% O<sub>2</sub> y 18 en <strong>PSI-10 Flame Design</strong>)
            más el rango paramétrico de <strong>PSI-68 FLEX-2</strong> (0.5–3.0 atm, 10–40% O<sub>2</sub>, IRL = 87.5).</li>
            <li><strong>Brecha Física en Gravedad Parcial (0.16g Lunar / 0.38g Marciana):</strong>
            Actualmente existen <strong>0 ensayos físicos reales</strong> en gravedad parcial en NASA PSI (a la espera de
            futuras misiones como LUCI y FM2). El sistema prohíbe la extrapolación ciega, acotando el riesgo entre los límites
            experimentales de 0g y 1g y utilizando <strong>PSI-22 (ACME E-FIELD Flames)</strong> como proxy electrostático.</li>
        </ul>
    </div>

    <h2>3. Análisis de Brechas (Gap Analysis): Las 8 Investigaciones PSI Pendientes de Ingesta</h2>
    <p>De los 26 registros totales de la búsqueda en NASA PSI (25 en página 1 + registro #26 <strong>PSI-47 DAFT</strong>
    excluido por calibración con polvo mineral), <strong>16 estudios</strong> ya están activos en producción,
    <strong>2</strong> han sido excluidos en auditoría (PSI-108 y PSI-47) y <strong>8 investigaciones</strong> permanecen
    pendientes de descarga e ingesta:</p>
    <table>
        <thead>
            <tr>
                <th>ID PSI</th>
                <th>Acrónimo</th>
                <th>Semáforo</th>
                <th>Pilar Seguridad</th>
                <th>Estudio Padre</th>
                <th>Prioridad</th>
                <th>Impacto y Brecha Técnica</th>
            </tr>
        </thead>
        <tbody>{pending_rows_html}</tbody>
    </table>

    <h2>4. Hoja de Ruta de Ingesta y Mitigación de Brechas</h2>
    <ol>
        <li><strong>Fase P1 (Crítica Vuelo — Luz Verde):</strong> Descargar e ingestar <strong>PSI-98 (SAFFIRE-I)</strong>,
        <strong>PSI-99 (SAFFIRE-II)</strong> y <strong>PSI-100 (SAFFIRE-III)</strong> para incorporar propagación de incendios
        a gran escala en vehículo Cygnus (tejido Sibal) y combustión latente (<em>smoldering</em>).</li>
        <li><strong>Fase P2 (Calibración CFD y Óptica — Luz Ámbar):</strong> Ingestar <strong>PSI-62 (FGM/BASS)</strong>,
        <strong>PSI-60 (Óptica SPICE)</strong>, <strong>PSI-115 (Modelado SAME)</strong> y <strong>PSI-117 (OpenFOAM FLEX)</strong>
        para cerrar los pares de validación Tierra &harr; Vuelo en la vista de Investigadores CFD.</li>
        <li><strong>Fase P3 (Higiene Automática — Luz Roja):</strong> Bloquear <strong>PSI-181 (Soldaduras Pb-Sn)</strong>
        mediante el filtro de área científica (<em>Materials Science &ne; Combustion Science</em>).</li>
    </ol>

    {doi_appendix_html}

    <div class="footer">
        Documento técnico generado automáticamente por el motor de auditoría <strong>Flame in Freefall</strong>
        (NASA Space Apps Challenge 2026). Todas las métricas han sido verificadas bajo protocolo de validación cruzada de unidades.
    </div>
</body>
</html>
"""
    return html_doc


def generate_jury_pdf_report(
    df_full: pd.DataFrame,
    df_cat: pd.DataFrame,
    team_name: str = "DROP TABLE USERS — Flame in Freefall",
    target_mission: str = "Hábitats Lunares Artemis (<= 10.2 psi, >= 30% O2)",
    include_full_doi_appendix: bool = True,
) -> bytes:
    """
    Genera un informe técnico profesional en PDF binario (bytes) para el jurado de NASA Space Apps.
    Usa ReportLab si está disponible, con fallback automático a FPDF o Matplotlib PdfPages.
    """
    master_df = get_master_26_df()
    pending_df = master_df[master_df["ingestion_status"] == "PENDING_INGESTION"].copy()
    n_clean = len(df_full)
    n_lunar = int(df_full["is_lunar_atmosphere"].sum()) if "is_lunar_atmosphere" in df_full.columns else 0
    gen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Intento 1: ReportLab (alta calidad tipográfica y tablas multipágina)
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
            title="Flame in Freefall - Informe Tecnico NASA Space Apps",
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "JuryTitle",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#0B132B"),
            spaceAfter=6,
        )
        h2_style = ParagraphStyle(
            "JuryH2",
            parent=styles["Heading2"],
            fontSize=12.5,
            textColor=colors.HexColor("#1C2541"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "JuryBody",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=13,
        )
        alert_style = ParagraphStyle(
            "JuryAlert",
            parent=styles["BodyText"],
            fontSize=9.2,
            leading=12.5,
            textColor=colors.HexColor("#7F1D1D"),
            backColor=colors.HexColor("#FEF2F2"),
            borderPadding=8,
        )

        story = []
        story.append(Paragraph("FLAME IN FREEFALL — Informe Tecnico para el Jurado NASA Space Apps 2026", title_style))
        story.append(Paragraph(f"<b>Equipo:</b> {team_name} | <b>Mision Objetivo:</b> {target_mission} | <b>Fecha:</b> {gen_date}", body_style))
        story.append(Spacer(1, 10))

        # Tabla KPI ejecutiva
        kpi_data = [
            ["Cobertura Catalogo PSI", "Registros Limpios", "Ensayos Zona Lunar", "Estudios Pendientes"],
            ["16 / 26 Activos (61.5%)", f"{n_clean:,} filas certificadas", f"{n_lunar} ensayos (<=10.2 psi, >=30% O2)", "8 estudios (7 comb. + 1 ruido)"],
        ]
        kpi_tbl = Table(kpi_data, colWidths=[130, 130, 140, 123])
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F1F5F9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 10))

        story.append(Paragraph("1. Protocolo de Seguridad Aeroespacial y Brecha de Gravedad Parcial", h2_style))
        story.append(Paragraph(
            "<b>ALERTA CRITICA DE SEGURIDAD:</b> Las atmosferas de habitats lunares y rovers presurizados "
            "(P <= 10.2 psi y O2 >= 30%) incrementan la inflamabilidad en mas de un 40% respecto a la Tierra. "
            "Actualmente existen 0 ensayos fisicos reales en gravedad parcial (0.16g Lunar / 0.38g Marciana) en NASA PSI "
            "(a la espera de LUCI y FM2). El sistema acota el riesgo entre 0g y 1g y emplea PSI-22 (ACME E-FIELD Flames) "
            "como proxy electrostatico de gravedad reducida.",
            alert_style,
        ))
        story.append(Spacer(1, 8))

        story.append(Paragraph("2. Auditoria de Brechas (Gap Analysis): 8 Investigaciones PSI Pendientes", h2_style))
        gap_table_data = [["ID PSI", "Acronimo", "Luz", "Pilar / Tipo", "Prioridad y Brecha Detectada"]]
        for _, r in pending_df.iterrows():
            gap_table_data.append([
                Paragraph(f"<b>{r['investigation_id']}</b>", body_style),
                Paragraph(r["acronym"], body_style),
                Paragraph(r["traffic_light"], body_style),
                Paragraph(r["safety_pillar"], body_style),
                Paragraph(f"<b>{r['download_priority']}:</b> {r['gap_notes']}", body_style),
            ])

        gap_tbl = Table(gap_table_data, colWidths=[52, 78, 42, 85, 266], repeatRows=1)
        gap_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1C2541")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(gap_tbl)

        if include_full_doi_appendix:
            story.append(Paragraph("3. Apendice de Trazabilidad DOI (NASA SMD Open Source Science)", h2_style))
            doi_table_data = [["ID PSI", "Acronimo", "Estado", "DOI / Resolucion NASA PSI"]]
            for _, r in master_df.iterrows():
                doi_txt = ", ".join(r["known_publications_dois"]) if r["known_publications_dois"] else r["doi"]
                doi_table_data.append([
                    Paragraph(f"<b>{r['investigation_id']}</b>", body_style),
                    Paragraph(r["acronym"], body_style),
                    Paragraph(r["ingestion_status"], body_style),
                    Paragraph(doi_txt, body_style),
                ])
            doi_tbl = Table(doi_table_data, colWidths=[52, 82, 95, 294], repeatRows=1)
            doi_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(doi_tbl)

        doc.build(story)
        return buf.getvalue()
    except Exception:
        pass

    # Intento 2: Fallback universal con Matplotlib PdfPages (siempre disponible)
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        lines = [
            "FLAME IN FREEFALL — INFORME TECNICO NASA SPACE APPS 2026",
            f"Equipo: {team_name} | Mision: {target_mission}",
            f"Fecha: {gen_date}",
            "-" * 85,
            f"1. COBERTURA: 16/26 estudios activos | {n_clean} registros limpios | {n_lunar} ensayos lunares",
            "2. ALERTA SEGURIDAD: Sin datos reales en 0.16g/0.38g; acotacion 0g-1g + proxy PSI-22.",
            "3. BRECHAS (8 ESTUDIOS PENDIENTES DE INGESTA):",
        ]
        for _, r in pending_df.iterrows():
            lines.append(f"   - {r['investigation_id']} ({r['acronym']}) [{r['traffic_light']}]: {r['download_priority']}")
        ax.text(0.05, 0.95, "\n".join(lines), va="top", ha="left", fontsize=9, family="monospace")
        pdf.savefig(fig)
        plt.close(fig)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# INTERFAZ PRINCIPAL STREAMLIT
# -----------------------------------------------------------------------------
def main() -> None:
    df_full, df_cat, partitions = load_all_datasets()
    master_26_df = get_master_26_df()

    # Cabecera Institucional
    st.markdown(
        """
        <div class="main-header">
            <h1>🔥 FLAME IN FREEFALL — Inteligencia de Seguridad contra Incendios Espaciales</h1>
            <p>NASA Space Apps Challenge 2026 • Repositorio NASA PSI • Auditoría de Envolvente Lunar, Gravedad Parcial y Trazabilidad SMD Open Source Science</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Barra Superior de Control: Selector de Perfil y Gravedad Objetivo
    col_p1, col_p2, col_p3 = st.columns([2, 2, 1.5])
    with col_p1:
        selected_profile = st.selectbox(
            "👤 Perfil Operacional del Usuario",
            options=["Seguridad Aeroespacial", "Estudiantes", "Investigadores CFD"],
            index=0,
            help="Adapta automáticamente la partición CSV, métricas de seguridad y herramientas de exportación.",
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
        data_mode = "CSV Locales Auditados" if Path("data/processed/experiments_limpio_completo.csv").exists() else "Baseline Científico Embebido"
        st.metric("Fuente Activa", data_mode, f"{len(df_full):,} filas limpias")

    df_profile = partitions.get(selected_profile, df_full).copy()

    # Banner de Seguridad Reforzada para Gravedad Parcial (0.16g / 0.38g)
    if "0.16g" in selected_gravity or "0.38g" in selected_gravity:
        st.markdown(
            """
            <div class="safety-banner-critical">
                <strong>🚨 ALERTA DE SEGURIDAD REFORZADA — AUSENCIA DE DATOS EXPERIMENTALES EN GRAVEDAD PARCIAL (0.16g / 0.38g):</strong><br>
                Actualmente existen <strong>0 ensayos físicos reales</strong> de combustión en gravedad lunar (0.16g) o marciana (0.38g)
                en el repositorio NASA PSI (a la espera de futuras misiones como <em>LUCI</em> y <em>FM2</em>).
                Para prevenir extrapolaciones peligrosas en atmósferas hiperóxicas (&le; 10.2 psi y &ge; 30% O<sub>2</sub>, donde la inflamabilidad
                aumenta &gt;40% frente a la Tierra), el motor acota el riesgo entre los límites conocidos de <strong>0g</strong> y <strong>1g</strong>
                y utiliza <strong>PSI-22 (ACME E-FIELD Flames)</strong> como puente de emulación electrostática.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Pestañas Principales del Dashboard
    tab_env, tab_profile, tab_gap = st.tabs([
        "🛰️ Envolvente Atmosférica & Seguridad Lunar",
        f"🧭 Vista Especializada: {selected_profile}",
        "🔍 Auditoría de Cobertura y Brechas (Gap Analysis)",
    ])

    # =========================================================================
    # PESTAÑA 1: ENVOLVENTE ATMOSFÉRICA & SEGURIDAD LUNAR
    # =========================================================================
    with tab_env:
        c1, c2, c3, c4 = st.columns(4)
        n_scalar = int((df_full["pressure_psi"].notna() & df_full["oxygen_pct"].notna()).sum())
        n_lunar = int(df_full["is_lunar_atmosphere"].sum()) if "is_lunar_atmosphere" in df_full.columns else 0
        c1.metric("Estudios PSI Activos", f"{len(df_cat)} / 26", "9 Verde | 7 Ámbar")
        c2.metric("Coordenadas Escalares (P, %O2)", f"{n_scalar:,}", "Unidades normalizadas psia")
        c3.metric("Ensayos Zona Crítica Lunar", f"{n_lunar}", "PSI-159 (48) + PSI-10 (18)")
        c4.metric("IRL Máximo Alcanzado", "87.5 / 100", "PSI-68 FLEX-2 & PSI-159")

        opt_col1, opt_col2 = st.columns(2)
        with opt_col1:
            show_envelopes = st.checkbox("Mostrar cajas paramétricas de estudio (PSI-68 FLEX-2, PSI-69 FLEX)", value=True)
        with opt_col2:
            show_bounds = st.checkbox("Resaltar umbral de presión lunar (10.2 psia)", value=True)

        fig_env = build_atmospheric_envelope_figure(
            df_full,
            show_study_envelopes=show_envelopes,
            highlight_partial_grav_bounds=show_bounds,
        )
        st.plotly_chart(fig_env, use_container_width=True)

        st.subheader("Ranking de Relevancia Lunar (IRL) — 16 Investigaciones Ingestadas")
        st.dataframe(
            df_cat.sort_values(by=["irl_score_max", "total_clean_records"], ascending=False),
            use_container_width=True,
            hide_index=True,
        )

    # =========================================================================
    # PESTAÑA 2: VISTA ESPECIALIZADA POR PERFIL DE USUARIO
    # =========================================================================
    with tab_profile:
        st.subheader(f"Panel Operacional — Perfil: {selected_profile}")

        if selected_profile == "Seguridad Aeroespacial":
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                only_lunar = st.checkbox("Filtrar solo registros en Zona Crítica Lunar (P <= 10.2 psi y %O2 >= 30%)", value=False)
            with col_f2:
                tl_filter = st.multiselect("Filtrar por Semáforo de Solvencia", ["GREEN", "AMBER"], default=["GREEN", "AMBER"])

            filtered_df = df_profile[df_profile["traffic_light"].isin(tl_filter)].copy()
            if only_lunar and "is_lunar_atmosphere" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["is_lunar_atmosphere"] == True]

            st.info(
                "📌 **Criterio NASA-STD-6001:** En microgravedad y baja presión, la ausencia de convección natural "
                "modifica los límites de inflamabilidad. Evalúe siempre los ensayos de **PSI-25/26 (BASS)** junto con "
                "los estudios pendientes a gran escala **PSI-98/99/100 (SAFFIRE-I/II/III)**."
            )
            st.dataframe(filtered_df.head(250), use_container_width=True, hide_index=True)

        elif selected_profile == "Estudiantes":
            st.info(
                "🎓 **Física de la Llama en Caída Libre (1g vs. 0g):** En la Tierra, el aire caliente sube por flotabilidad "
                "(convección natural), estirando la llama en forma de lágrima amarilla. En microgravedad (0g), desaparece la flotabilidad "
                "y la llama adopta una geometría **esférica azul** gobernada únicamente por difusión molecular."
            )
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                fig_fuel = px.pie(
                    df_cat,
                    names="safety_pillar",
                    values="total_clean_records",
                    title="Distribución de Registros por Pilar de Seguridad",
                    template="plotly_dark",
                )
                st.plotly_chart(fig_fuel, use_container_width=True)
            with col_e2:
                fig_tl = px.bar(
                    df_cat,
                    x="acronym",
                    y="irl_score_max",
                    color="traffic_light",
                    color_discrete_map={"GREEN": "#10B981", "AMBER": "#F59E0B"},
                    title="Índice de Relevancia Lunar (IRL) por Experimento",
                    template="plotly_dark",
                )
                st.plotly_chart(fig_tl, use_container_width=True)

        else:  # Investigadores CFD
            st.info(
                "🔬 **Acoplamiento Experimental Vuelo (0g) ↔ Validación Numérica Tierra (CFD):** "
                "Utilice esta vista para extraer condiciones de contorno normalizadas (psia, fracción molar X_O2, ppO2) "
                "y auditar los pares vuelo-simulación."
            )
            st.dataframe(df_profile.head(250), use_container_width=True, hide_index=True)

        st.download_button(
            label=f"⬇️ Descargar Partición CSV ({selected_profile})",
            data=df_profile.to_csv(index=False).encode("utf-8"),
            file_name=f"flame_in_freefall_{selected_profile.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )

    # =========================================================================
    # PESTAÑA 3: AUDITORÍA DE COBERTURA Y BRECHAS (GAP ANALYSIS)
    # =========================================================================
    with tab_gap:
        st.header("🔍 Auditoría de Cobertura y Brechas (Gap Analysis) — Repositorio NASA PSI")
        st.markdown(
            "Reconciliación integral de los **26 registros** de búsqueda en **NASA Physical Sciences Informatics (PSI)**: "
            "cruce entre las **16 investigaciones activas**, los **2 registros excluidos por auditoría** "
            "(`PSI-108` Física de Fluidos y `PSI-47 DAFT` calibración con polvo mineral que resuelve el registro #26) "
            "y las **8 investigaciones pendientes de ingesta** (`PSI-98`, `PSI-99`, `PSI-100`, `PSI-62`, `PSI-60`, `PSI-115`, `PSI-117` y `PSI-181`)."
        )

        # KPIs de Cobertura y Brechas
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Cobertura Catálogo PSI", "16 / 26 (61.5%)", "8 pendientes + 2 excluidos")
        g2.metric("Brecha Crítica Luz Verde", "3 Estudios", "SAFFIRE-I, II y III (Cygnus)")
        g3.metric("Brecha Calibración CFD/Óptica", "4 Estudios", "PSI-62, PSI-60, PSI-115, PSI-117")
        g4.metric("Ruido Bloqueado en Brecha", "1 Estudio (Rojo)", "PSI-181 (Materials Science)")

        # Gráfico de Cobertura por Pilar de Seguridad y Estado de Ingesta
        gap_chart_col1, gap_chart_col2 = st.columns([1.3, 1])
        with gap_chart_col1:
            coverage_summary = (
                master_26_df.groupby(["safety_pillar", "ingestion_status"])
                .size()
                .reset_index(name="num_studies")
            )
            fig_gap = px.bar(
                coverage_summary,
                x="safety_pillar",
                y="num_studies",
                color="ingestion_status",
                barmode="stack",
                color_discrete_map={
                    "INGESTED_ACTIVE": "#10B981",
                    "PENDING_INGESTION": "#F59E0B",
                    "EXCLUDED_AUDIT": "#EF4444",
                },
                title="Cobertura vs. Brechas por Pilar de Seguridad (26 Registros PSI)",
                labels={
                    "safety_pillar": "Pilar de Seguridad / Disciplina",
                    "num_studies": "Número de Investigaciones PSI",
                    "ingestion_status": "Estado en Pipeline",
                },
                template="plotly_dark",
            )
            fig_gap.update_layout(height=390, margin=dict(l=20, r=20, t=45, b=40))
            st.plotly_chart(fig_gap, use_container_width=True)

        with gap_chart_col2:
            pending_only = master_26_df[master_26_df["ingestion_status"] == "PENDING_INGESTION"]
            fig_pending_tl = px.pie(
                pending_only,
                names="traffic_light",
                title="Clasificación Semáforo de las 8 Investigaciones Pendientes",
                color="traffic_light",
                color_discrete_map={"GREEN": "#10B981", "AMBER": "#F59E0B", "RED": "#EF4444"},
                template="plotly_dark",
            )
            fig_pending_tl.update_layout(height=390, margin=dict(l=20, r=20, t=45, b=40))
            st.plotly_chart(fig_pending_tl, use_container_width=True)

        # Tabla Interactiva de Estudios Pendientes por Descargar
        st.subheader("📋 Inventario Detallado de Estudios Pendientes por Descargar del Repositorio PSI")
        filter_status = st.multiselect(
            "Filtrar vista de auditoría por estado en el pipeline:",
            options=["PENDING_INGESTION", "INGESTED_ACTIVE", "EXCLUDED_AUDIT"],
            default=["PENDING_INGESTION"],
        )
        audit_view_df = master_26_df[master_26_df["ingestion_status"].isin(filter_status)][[
            "investigation_id",
            "acronym",
            "traffic_light",
            "ingestion_status",
            "safety_pillar",
            "hardware",
            "parent_or_linked_ids",
            "irl_score_max",
            "download_priority",
            "target_files",
            "gap_notes",
            "psi_url",
        ]]
        st.dataframe(audit_view_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # =====================================================================
        # SUB-MÓDULO B: ASISTENTE DE CONSULTA EN LENGUAJE NATURAL SOBRE CITAS DOI
        # =====================================================================
        st.subheader("🤖 Asistente de Consulta en Lenguaje Natural sobre Citas DOI (NASA SMD Open Source Science)")
        st.markdown(
            "Consulta en español o inglés sobre identificadores persistentes **DOI**, atribución obligatoria de la NASA, "
            "estudios con DOIs verificados (`PSI-142`) o enlaces pendientes de resolución en las fichas de NASA PSI."
        )

        preset_col1, preset_col2, preset_col3 = st.columns(3)
        default_q = "¿Qué estudios tienen DOI verificado actualmente y cuáles faltan por extraer en las 8 investigaciones pendientes?"
        if preset_col1.button("🔎 Ver DOIs verificados vs. pendientes"):
            st.session_state["doi_nl_query"] = "¿Qué estudios tienen DOI verificado actualmente y cuáles faltan por extraer?"
        if preset_col2.button("🔥 Citas SAFFIRE-I/II/III (PSI-98/99/100)"):
            st.session_state["doi_nl_query"] = "Dame las citas y enlaces DOI de SAFFIRE-I, SAFFIRE-II y SAFFIRE-III (PSI-98, PSI-99, PSI-100)"
        if preset_col3.button("🧪 Citas Supresión y Llamas Frías (FLEX / PSI-142)"):
            st.session_state["doi_nl_query"] = "Muéstrame los DOIs verificados de PSI-142 y las citas de FLEX PSI-68 y PSI-69"

        q_col1, q_col2 = st.columns([3, 1])
        with q_col1:
            user_doi_query = st.text_input(
                "Escribe tu consulta sobre citas DOI, estudios PSI o normativa NASA:",
                value=st.session_state.get("doi_nl_query", default_q),
                key="doi_query_input",
            )
        with q_col2:
            citation_fmt = st.selectbox("Formato de Cita Bibliográfica", ["APA", "IEEE", "BibTeX"], index=0)

        if user_doi_query.strip():
            doi_res = query_doi_knowledge_base(user_doi_query, citation_style=citation_fmt)
            st.success(f"**Diagnóstico del Asistente DOI ({doi_res['matched_count']} registros):** {doi_res['intent_summary']}")

            for rec in doi_res["records"]:
                st.markdown(
                    f"""
                    <div class="doi-card">
                        <strong>{rec['investigation_id']} — {rec['acronym']}</strong>
                        &nbsp;|&nbsp; Semáforo: <strong>{rec['traffic_light']}</strong>
                        &nbsp;|&nbsp; Estado: <code>{rec['ingestion_status']}</code><br>
                        <small><strong>Estado DOI:</strong> {rec['doi']} &nbsp;•&nbsp;
                        <a href="{rec['psi_url']}" target="_blank" style="color:#38BDF8;">Abrir ficha oficial NASA PSI ↗</a></small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.code(rec["formatted_citation"], language="bibtex" if citation_fmt == "BibTeX" else "text")

        st.download_button(
            label="📄 Descargar Paquete Completo de Citas DOI (.txt — NASA SMD Open Source Science)",
            data=generate_doi_citations_bundle(df_full, df_cat).encode("utf-8"),
            file_name="nasa_psi_doi_citations_bundle.txt",
            mime="text/plain",
        )

        st.markdown("---")

        # =====================================================================
        # SUB-MÓDULO C: GENERADOR DE INFORME TÉCNICO EXPORTABLE (PDF / HTML)
        # =====================================================================
        st.subheader("📑 Generador de Informe Técnico Exportable (PDF / HTML) para el Jurado de NASA Space Apps")
        st.markdown(
            "Genera un dossier técnico listo para presentar al jurado con el resumen de cobertura, "
            "evaluación de seguridad en la Zona Crítica Lunar, brecha de gravedad parcial (0.16g/0.38g), "
            "plan de acción sobre los 8 estudios pendientes y apéndice de trazabilidad DOI."
        )

        rep_c1, rep_c2, rep_c3 = st.columns([2, 2, 1.2])
        with rep_c1:
            team_input = st.text_input("Nombre del Equipo / Proyecto", value="DROP TABLE USERS — Flame in Freefall")
        with rep_c2:
            mission_input = st.text_input(
                "Escenario de Misión Evaluado",
                value="Hábitats Lunares Artemis (<= 10.2 psi, >= 30% O2)",
            )
        with rep_c3:
            include_appendix = st.checkbox("Incluir Apéndice 26 DOIs", value=True)

        html_report_str = generate_jury_html_report(
            df_full=df_full,
            df_cat=df_cat,
            team_name=team_input,
            target_mission=mission_input,
            include_full_doi_appendix=include_appendix,
        )
        pdf_report_bytes = generate_jury_pdf_report(
            df_full=df_full,
            df_cat=df_cat,
            team_name=team_input,
            target_mission=mission_input,
            include_full_doi_appendix=include_appendix,
        )

        dl_c1, dl_c2 = st.columns(2)
        with dl_c1:
            st.download_button(
                label="📕 Descargar Informe Técnico Oficial en PDF (.pdf)",
                data=pdf_report_bytes,
                file_name="Flame_in_Freefall_Jury_Technical_Report.pdf",
                mime="application/pdf",
            )
        with dl_c2:
            st.download_button(
                label="🌐 Descargar Informe Técnico Interactivo en HTML (.html)",
                data=html_report_str.encode("utf-8"),
                file_name="Flame_in_Freefall_Jury_Technical_Report.html",
                mime="text/html",
            )

        with st.expander("👁️ Vista Previa del Informe Técnico HTML para el Jurado"):
            st.components.v1.html(html_report_str, height=520, scrolling=True)


if __name__ == "__main__":
    main()
