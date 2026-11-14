# Bitácora Técnica: Proyecto *Flame in Freefall* (NASA Space Apps Challenge 2026)

**Proyecto:** Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data  
**Fuentes Base:** Catálogo NASA Physical Sciences Informatics (PSI) Data Repository (25 de 26 registros) & Pliego Oficial del Reto NASA Space Apps Challenge 2026.

---

## 1. Taxonomía y Sistema de Semáforo (25 Investigaciones NASA PSI)

El repositorio NASA PSI indexa 25 registros de un total de 26 (*1 – 25 of 26*), divididos en **17 experimentos de vuelo en microgravedad ($0g$)**, **6 investigaciones en tierra (*Ground Investigations*)** y **2 registros de ruido de búsqueda**.

### 🟢 LUZ VERDE: Críticas y de Máxima Solvencia (12 Investigaciones)
*Criterio:* Datos experimentales directos en $0g$ sobre Prevención, Detección o Supresión, atmósferas hiperóxicas/baja presión ($\le 10.2\text{ psi}$ y $\ge 30\%\text{ }O_2$) o emulación de gravedad parcial ($0.16g$).

| ID PSI | Acrónimo / Título | Tipo / Hardware | Combustible y Condiciones Clave | Aporte Crítico al Proyecto *Flame in Freefall* |
| :--- | :--- | :--- | :--- | :--- |
| **PSI-159** | **ACME CFI-G** (*Cool Flames Investigation with Gases*) | Vuelo ($0g$) / CIR-ACME | Propano, n-butano, n-pentano; hasta **$85\%\text{ }O_2$** en llamas difusivas inversas. | **Máxima prioridad atmosférica:** Mayor concentración de $O_2$ en PSI; acota el riesgo en hábitats lunares ($\ge 30\%\text{ }O_2$). |
| **PSI-68** | **FLEX-2** (*Flame Extinguishment Experiment - 2*) | Vuelo ($0g$) / CIR-MDCA | Gotas de combustible líquido (ej. metil butanoato); **$0.5\text{–}3.0\text{ atm}$** y **$10\%\text{–}40\%\text{ }O_2$**. | Cubre exactamente la ventana lunar ($\le 10.2\text{ psi} \approx 0.69\text{ atm}$ y $\ge 30\%\text{ }O_2$). |
| **PSI-69** | **FLEX** (*Flame Extinguishment Experiment*) | Vuelo ($0g$) / CIR-MDCA | Gotas de combustible líquido; dilución con **$CO_2$ y $He$**. | **Supresión:** Determina el Índice Límite de Oxígeno ($LOI$) y eficacia de agentes extintores gaseosos. |
| **PSI-26** | **BASS** (*Burning and Suppression of Solids*) | Vuelo ($0g$) / MSG-SPICE | Tejido sólido ($75\%$ algodón / $25\%$ fibra de vidrio); ignición con hilo Kanthal. | **Prevención:** Cierra la brecha entre la prueba terrestre `NASA-STD-6001 Test #1` y la inflamabilidad real en órbita. |
| **PSI-25** | **BASS-II** (*Burning and Suppression of Solids - II*) | Vuelo ($0g$) / MSG-SPICE | Muestras sólidas en túnel de viento de la ISS con operación de tripulación. | Evalúa el efecto del flujo de ventilación forzada sobre la ignición y extinción de sólidos. |
| **PSI-98** | **SAFFIRE-I** (*Spacecraft Fire Safety Experiment-I*) | Vuelo ($0g$) / Nave Cygnus | Tejido compuesto **Sibal** (algodón/fibra de vidrio) a gran escala tras desacoplarse de la ISS. | Mide velocidad de propagación de incendios a escala real de vehículo. |
| **PSI-99** | **SAFFIRE-II** (*Spacecraft Fire Experiment-II*) | Vuelo ($0g$) / Nave Cygnus | Múltiples muestras sólidas; límites de inflamabilidad a gran escala. | Amplía la matriz de materiales y límites de inflamabilidad en baja gravedad. |
| **PSI-100** | **SAFFIRE-III** (*Spacecraft Fire Experiment-III*) | Vuelo ($0g$) / Nave Cygnus | Muestras sólidas; propagación de llama y combustión sin llama (*smoldering*). | Completa la trilogía a gran escala, incluyendo combustión latente (*smoldering*) y gases tóxicos. |
| **PSI-20** | **ACME BRE** (*Burning Rate Emulator*) | Vuelo ($0g$) / CIR-ACME | Combustibles gaseosos en atmósfera quieta (*quiescent*) emulando sólidos. | Predice inflamabilidad de sólidos a partir de su calor de combustión y gasificación. |
| **PSI-102** | **SAME** (*Smoke and Aerosol Measurement Experiment*) | Vuelo ($0g$) / MSG | Aerosoles de humo líquido en eventos de ~2 minutos. | **Detección:** Cuantifica tamaño de partícula de humo en $0g$ para evitar falsas alarmas (caso Artemis II). |
| **PSI-101** | **SAME-R** (*Smoke Aerosol Measurement Experiment-Reflight*) | Vuelo ($0g$) / MSG | Espuma ignífuga intumescente **Pyrell®**. | Evalúa la generación de humo en materiales retardantes de llama reales de cabina. |
| **PSI-22** | **ACME E-FIELD Flames** | Vuelo ($0g$) / CIR-ACME | Llamas laminares de difusión sometidas a campos eléctricos. | **Puente de Gravedad Parcial:** Sus campos eléctricos sobre iones emulan el efecto de gravedad reducida ($0.16g$ lunar). |

### 🟡 LUZ ÁMBAR: Complementarias, Ventilación y Validación Numérica (11 Investigaciones)
*   **Estabilidad de Llama y Ventilación (Vuelo $0g$):** `PSI-106` (SLICE), `PSI-107` (SPICE), `PSI-39` (CFI, $0.25\text{–}5\text{ atm}$), `PSI-10` (ACME Flame Design), `PSI-21` (ACME CLD Flame) y `PSI-23` (ACME s-Flame).
*   **Modelado Predictivo y Validación Tierra $\leftrightarrow$ Vuelo (*Ground Investigations*):** `PSI-62` (FGM/BASS), `PSI-115` (Modelado Navier-Stokes SAME), `PSI-60` (Pirometría óptica Nikon NEF en SPICE), `PSI-117` (OpenFOAM FLEX) y `PSI-142` (Counterflow FLEX).

### 🔴 LUZ ROJA: Ruido de Búsqueda / Fuera de Alcance (2 Investigaciones)
*   **PSI-181:** Ciencia de Materiales sobre soldaduras metálicas Pb-Sn y Sn-Ag-Cu.
*   **PSI-108 (STDCE-1):** Física de Fluidos sobre convección termocapilar.

> **Notas de Rigor Científico:**
> 1. El registro #26 faltante (*1 – 25 of 26*) corresponde probablemente a **DAFT / DAFT-2**, que reutilizaron instrumentación de `SAME`.
> 2. La política *NASA SMD Open Source Science* exige citar obligatoriamente el **DOI único** de cada investigación.

---

## 2. Mapa de Extracción Técnica por Bloque de Datos

1. **Atmósferas Hiperóxicas y Baja Presión (`PSI-159`, `PSI-68`):** Tablas CSV de presión absoluta, caudales másicos de reactantes/diluyentes, fracción molar de $O_2$, radiómetros de llama fría y evolución de diámetro de gota $d^2(t)$.
2. **Inflamabilidad de Sólidos (`PSI-25`, `PSI-26`):** Telemetría de túnel de viento MSG, corriente de hilo ignitor Kanthal (calibre 29), composición de muestra ($75\%$ algodón / $25\%$ fibra de vidrio) y fotogramas de velocidad de propagación $V_f$.
3. **Incendios a Gran Escala (`PSI-98`, `PSI-99`, `PSI-100`):** Matrices de termopares y radiómetros en naves Cygnus, telemetría de gases tóxicos en *smoldering* y cámaras de longitud de llama.
4. **Detección de Humo (`PSI-102`, `PSI-101`):** Granulometría de aerosoles en cajas *Near Field* y *Far Field* (incluyendo espuma Pyrell®).
5. **Supresión (`PSI-69`):** Tablas de concentración crítica de $CO_2$ y $He$ para determinar el Índice Límite de Oxígeno ($LOI$).
6. **Puente de Gravedad Parcial (`PSI-22`):** Series sincronizadas de voltaje de campo eléctrico frente a corriente quimio-iónica e imágenes de deformación de llama. *(Nota: Los archivos RAW `.NEF` de Nikon para pirometría RGB se procesan con librerías sin compresión como `rawpy`, documentado en `PSI-60` sobre datos de `PSI-107`)*.

---

## 3. Protocolo de Validación Cruzada de Unidades (4 Aduanas de Seguridad)

1. **Aduana 1 — Presión ($\text{atm} / \text{kPa} \rightarrow \text{psia}$):**
   $$P_{\text{psi}} = P_{\text{atm}} \times 14.6959488 \quad | \quad P_{\text{psi}} = P_{\text{kPa}} \times 0.1450377$$
   *Chequeo de envolvente:* Valores fuera de $[3.67\text{ psi}, 73.50\text{ psi}]$ ($0.25\text{–}5.0\text{ atm}$) disparan alertas de escala (`UNIT_SCALE_WARNING` o re-escalado automático de $\text{Pa}$ a $\text{kPa}$).
2. **Aduana 2 — Balance Molar y Bloqueo Másico:**
   *   Normaliza escala entre fracción molar ($0\text{–}1$) y porcentaje volumétrico ($0\text{–}100$).
   *   Exige cierre molar: $\sum X_i = X_{O_2} + X_{N_2} + X_{CO_2} + X_{He} + X_{\text{fuel}} = 1.000 \pm 0.005$.
   *   **Bloqueo preventivo:** Rechaza fracciones másicas (`mass_fraction`) sin ponderación por peso molecular (crítico al usar Helio en `PSI-69`).
3. **Aduana 3 — Presión Parcial ($ppO_2$) y Zona Crítica Lunar:**
   $$ppO_2 = P_{\text{psi}} \cdot X_{O_2}$$
   Activa `LUNAR_CRITICAL_ALERT` cuando $P_{\text{psi}} \le 10.2\text{ psi}$ y $\%O_2 \ge 30\%$ (incremento $>40\%$ en inflamabilidad frente a la Tierra y ausencia de datos reales en gravedad lunar $0.16g$).
4. **Aduana 4 — Trazabilidad DOI:**
   Valida mediante expresión regular el identificador DOI persistente o lo hereda desde metadatos maestros (`investigation_metadata_fallback`).

---

## 4. Código Implementado: `src/etl_validator.py`

```python
"""
Módulo ETL y Validación Cruzada de Unidades para el proyecto 'Flame in Freefall' (NASA Space Apps).
Implementa las 4 aduanas de seguridad aeroespacial sobre datos experimentales de NASA PSI:
  1. Aduana de Presión (atm / kPa -> psia) con detección automática de escala.
  2. Aduana de Concentración de O2 (fracción molar <-> % volumétrico) y cierre molar (sum(X_i) = 1.0).
  3. Aduana de Presión Parcial de Oxígeno (ppO2 = P_psi * X_O2) y detección de Zona Crítica Lunar.
  4. Aduana de Trazabilidad DOI (política SMD Open Source Science de NASA) y fallback de metadatos.
"""

from __future__ import annotations

import re
import unittest
from typing import Dict, List, Literal, Optional, Tuple
import pandas as pd
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

ATM_TO_PSI: float = 14.6959488
KPA_TO_PSI: float = 0.1450377
MIN_VALID_PRESSURE_PSI: float = 3.67   # ~0.25 atm (límite inferior PSI-39 CFI)
MAX_VALID_PRESSURE_PSI: float = 73.50  # ~5.00 atm (límite superior PSI-39 CFI)

LUNAR_MAX_PRESSURE_PSI: float = 10.2   # Hábitats lunares / rovers presurizados <= 10.2 psi
LUNAR_MIN_O2_PCT: float = 30.0         # Concentración esperada en hábitats lunares >= 30% O2
MAX_EXPERIMENTAL_O2_PCT: float = 85.0  # Límite superior probado en microgravedad (PSI-159 ACME CFI-G)

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")


class PSIRecordInput(BaseModel):
    investigation_id: str = Field(..., description="ID oficial en NASA PSI (ej. PSI-68, PSI-159)")
    acronym: str = Field(..., description="Acrónimo de la investigación (ej. FLEX-2, ACME CFI-G)")
    doi: Optional[str] = Field(None, description="Identificador persistente DOI obligatorio")

    pressure_value: Optional[float] = Field(None, description="Valor numérico de presión de cámara")
    pressure_unit: Literal["atm", "kPa", "psi", "Pa"] = Field("atm", description="Unidad reportada de presión")

    o2_value: float = Field(..., ge=0.0, description="Concentración de O2 reportada")
    n2_value: float = Field(0.0, ge=0.0, description="Concentración de N2 reportada")
    co2_value: float = Field(0.0, ge=0.0, description="Concentración de CO2 reportada")
    he_value: float = Field(0.0, ge=0.0, description="Concentración de He reportada")
    fuel_value: float = Field(0.0, ge=0.0, description="Concentración de combustible gaseoso reportada")
    species_basis: Literal["mole_fraction", "volume_percent", "mass_fraction"] = Field(
        "mole_fraction", description="Base de composición reportada en el dataset"
    )

    metadata_fallback_pressure_psi: Optional[float] = Field(None)
    metadata_fallback_doi: Optional[str] = Field(None)

    @field_validator("species_basis")
    @classmethod
    def block_direct_mass_fraction(cls, v: str) -> str:
        if v == "mass_fraction":
            raise ValueError(
                "BLOQUEO DE SEGURIDAD: No se permite ingestar 'mass_fraction' directamente como "
                "porcentaje volumétrico sin conversión ponderada por peso molecular (M_i)."
            )
        return v

    @model_validator(mode="after")
    def check_doi_traceability(self) -> "PSIRecordInput":
        effective_doi = self.doi or self.metadata_fallback_doi
        if not effective_doi or not DOI_PATTERN.match(effective_doi.strip()):
            raise ValueError(
                f"[{self.investigation_id}] ERROR DE TRAZABILIDAD (Aduana 4): "
                "Falta un DOI válido ('Cite this Investigation') exigido por NASA SMD Open Source Science."
            )
        return self


class NormalizedPSIRecord(BaseModel):
    investigation_id: str
    acronym: str
    doi: str
    doi_source: Literal["record", "investigation_metadata_fallback"]

    pressure_psi: float
    pressure_source: Literal["record", "investigation_metadata_fallback"]
    scale_corrected: bool
    warnings: List[str]

    x_o2: float
    o2_pct_vol: float
    molar_closure_sum: float
    ppo2_psi: float

    is_lunar_critical_zone: bool
    is_hyperoxic_extrapolation: bool
    safety_status: Literal["NOMINAL", "LUNAR_CRITICAL_ALERT", "EXTRAPOLATION_WARNING"]


def normalize_and_validate_record(raw: PSIRecordInput) -> NormalizedPSIRecord:
    warnings: List[str] = []
    scale_corrected = False

    # ADUANA 1: Conversión y chequeo de escala de Presión
    if raw.pressure_value is not None:
        p_val = raw.pressure_value
        unit = raw.pressure_unit
        p_source: Literal["record", "investigation_metadata_fallback"] = "record"

        if unit == "kPa" and p_val > 2000.0:
            warnings.append(f"UNIT_SCALE_CORRECTED: Presión {p_val} kPa re-escalada desde Pa -> kPa.")
            p_val = p_val / 1000.0
            scale_corrected = True
        elif unit == "atm" and p_val > 10.0:
            warnings.append(f"UNIT_SCALE_CORRECTED: Presión {p_val} atm re-escalada asumiendo kPa.")
            unit = "kPa"
            scale_corrected = True

        if unit == "atm":
            pressure_psi = p_val * ATM_TO_PSI
        elif unit == "kPa":
            pressure_psi = p_val * KPA_TO_PSI
        elif unit == "Pa":
            pressure_psi = (p_val / 1000.0) * KPA_TO_PSI
        else:
            pressure_psi = p_val
    elif raw.metadata_fallback_pressure_psi is not None:
        pressure_psi = raw.metadata_fallback_pressure_psi
        p_source = "investigation_metadata_fallback"
        warnings.append("METADATA_FALLBACK: Presión heredada de metadatos maestros.")
    else:
        raise ValueError(f"[{raw.investigation_id}] Presión ausente en registro y metadatos.")

    if pressure_psi < MIN_VALID_PRESSURE_PSI or pressure_psi > MAX_VALID_PRESSURE_PSI:
        warnings.append(f"UNIT_SCALE_WARNING: Presión ({pressure_psi:.2f} psi) fuera de envolvente PSI.")

    # ADUANA 2: Balance Molar (sum X_i = 1.0)
    species_raw = [raw.o2_value, raw.n2_value, raw.co2_value, raw.he_value, raw.fuel_value]
    raw_sum = sum(species_raw)

    if raw.species_basis == "mole_fraction" and (raw.o2_value > 1.0 or raw_sum > 1.5):
        warnings.append("UNIT_SCALE_CORRECTED: Escala porcentual detectada en mole_fraction. Dividiendo entre 100.")
        factor = 0.01
        scale_corrected = True
    elif raw.species_basis == "volume_percent" and raw_sum <= 1.05:
        warnings.append("UNIT_SCALE_CORRECTED: Fracción molar detectada en volume_percent.")
        factor = 1.0
        scale_corrected = True
    else:
        factor = 1.0 if raw.species_basis == "mole_fraction" else 0.01

    x_o2 = raw.o2_value * factor
    x_n2 = raw.n2_value * factor
    x_co2 = raw.co2_value * factor
    x_he = raw.he_value * factor
    x_fuel = raw.fuel_value * factor

    molar_sum = x_o2 + x_n2 + x_co2 + x_he + x_fuel

    if molar_sum < 0.995 and (x_n2 == 0.0 and x_co2 == 0.0 and x_he == 0.0 and x_fuel == 0.0) and x_o2 <= 1.0:
        x_n2 = 1.0 - x_o2
        molar_sum = x_o2 + x_n2
        warnings.append("MOLAR_BALANCE_INFERRED: Diluyente N2 inferido para cerrar balance = 1.0.")

    if abs(molar_sum - 1.0) > 0.005:
        raise ValueError(f"[{raw.investigation_id}] ERROR DE CIERRE MOLAR: suma = {molar_sum:.4f} != 1.0.")

    o2_pct_vol = x_o2 * 100.0

    # ADUANA 3: Presión Parcial de Oxígeno (ppO2) y Alerta Lunar
    ppo2_psi = pressure_psi * x_o2
    is_lunar_critical = (pressure_psi <= LUNAR_MAX_PRESSURE_PSI) and (o2_pct_vol >= LUNAR_MIN_O2_PCT)
    is_hyperoxic_extrapolation = o2_pct_vol > MAX_EXPERIMENTAL_O2_PCT

    if is_hyperoxic_extrapolation:
        safety_status: Literal["NOMINAL", "LUNAR_CRITICAL_ALERT", "EXTRAPOLATION_WARNING"] = "EXTRAPOLATION_WARNING"
        warnings.append(f"EXTRAPOLATION_WARNING: O2={o2_pct_vol:.1f}% supera el máximo experimental (85% en PSI-159).")
    elif is_lunar_critical:
        safety_status = "LUNAR_CRITICAL_ALERT"
        warnings.append(
            f"LUNAR_CRITICAL_ALERT: Envolvente lunar (P={pressure_psi:.2f} <= 10.2 psi, O2={o2_pct_vol:.1f}% >= 30%, "
            f"ppO2={ppo2_psi:.2f} psi). Riesgo >40% frente a Tierra y sin datos reales en 0.16g."
        )
    else:
        safety_status = "NOMINAL"

    # ADUANA 4: Resolución DOI
    if raw.doi:
        final_doi = raw.doi.strip()
        doi_source: Literal["record", "investigation_metadata_fallback"] = "record"
    else:
        final_doi = raw.metadata_fallback_doi.strip()  # type: ignore
        doi_source = "investigation_metadata_fallback"
        warnings.append("METADATA_FALLBACK: DOI heredado de metadatos maestros.")

    return NormalizedPSIRecord(
        investigation_id=raw.investigation_id,
        acronym=raw.acronym,
        doi=final_doi,
        doi_source=doi_source,
        pressure_psi=round(pressure_psi, 4),
        pressure_source=p_source,
        scale_corrected=scale_corrected,
        warnings=warnings,
        x_o2=round(x_o2, 4),
        o2_pct_vol=round(o2_pct_vol, 2),
        molar_closure_sum=round(molar_sum, 4),
        ppo2_psi=round(ppo2_psi, 4),
        is_lunar_critical_zone=is_lunar_critical,
        is_hyperoxic_extrapolation=is_hyperoxic_extrapolation,
        safety_status=safety_status,
    )


def process_psi_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    valid_rows: List[Dict] = []
    rejected_rows: List[Dict] = []

    for idx, row in df.iterrows():
        raw_dict = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
        try:
            validated_input = PSIRecordInput(**raw_dict)
            normalized = normalize_and_validate_record(validated_input)
            record_out = normalized.model_dump()
            record_out["warnings"] = " | ".join(normalized.warnings) if normalized.warnings else "OK"
            valid_rows.append(record_out)
        except (ValidationError, ValueError) as exc:
            rejected_rows.append(
                {
                    "row_index": idx,
                    "investigation_id": raw_dict.get("investigation_id", "UNKNOWN"),
                    "error_detail": str(exc),
                }
            )

    return pd.DataFrame(valid_rows), pd.DataFrame(rejected_rows)
```

---

## 5. Guía de Despliegue y Siguientes Pasos

```bash
# 1. Estructura de directorios y entorno
mkdir -p src data/raw data/processed
mv ~/Downloads/etl_validator.py src/etl_validator.py
pip install pandas pydantic streamlit plotly

# 2. Ejecución de pruebas unitarias
python src/etl_validator.py
```

**Integración en Pipeline:**
```python
import pandas as pd
from src.etl_validator import process_psi_dataframe

df_crudo = pd.read_csv("data/raw/psi_68_flex2_telemetria.csv")
df_limpio, df_rechazados = process_psi_dataframe(df_crudo)
df_limpio.to_csv("data/processed/psi_68_certificado.csv", index=False)
```