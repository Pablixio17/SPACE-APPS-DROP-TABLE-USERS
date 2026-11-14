from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configuracion de pagina
st.set_page_config(page_title="NASA PSI Fire Safety Explorer", layout="wide")

ROOT = Path(__file__).resolve().parents[1]
MASTER_PATH = ROOT / "data" / "processed" / "experiments.csv"

NUMERIC_LABELS = {
    "oxygen_fraction": "Fracción molar de O₂ (0 - 1)",
    "pressure_kpa": "Presión ambiental (kPa)",
    "fuel_flow_mg_s": "Flujo de combustible (mg/s)",
    "airflow_cm_s": "Velocidad de flujo de aire (cm/s)",
    "droplet_initial_diameter_mm": "Diámetro inicial de gota (mm)",
    "burn_time_s": "Tiempo de combustión (s)",
    "duration_s": "Duración del ensayo (s)",
}

CATEGORICAL_LABELS = {
    "fuel": "Combustible",
    "fuel_class": "Clase de combustible",
    "hardware": "Hardware (CIR / MDCA / MSG)",
    "investigation_id": "Investigación (PSI ID)",
    "focus": "Enfoque del estudio",
    "material": "Material de muestra",
    "flame_type": "Tipo de llama",
    "ignition_success": "Ignición exitosa",
}


@st.cache_data
def build_placeholder_data() -> pd.DataFrame:
    """Genera registros ficticios con el mismo esquema de prepare_data.py."""
    rng = np.random.default_rng(42)
    rows = []

#TODO ================
    studies = [
        ("PSI-108", "ACME_BRE", "propane", "gaseous", "CIR", "Combustión gaseosa", "Laminar diffusion", "N/A"),
        ("PSI-115", "ACME_CFI-G", "methane", "gaseous", "CIR", "Combustión gaseosa", "Cool flame (inside-out)", "N/A"),
        ("PSI-122", "FLEX-2", "n-dodecane", "liquid droplet", "MDCA (en CIR)", "Combustión de gotas", "Droplet flame", "N/A"),
        ("PSI-131", "BASS-II", "gaseous", "solid", "MSG (SPICE flow duct)", "Inflamabilidad de sólidos", "Concurrent flow", "PMMA"),
        ("PSI-140", "SAME-R", "ethylene", "gaseous", "CIR", "Smoke and aerosol detection", "Overheated wire", "Silicone"),
    ]

    for idx in range(60):
        inv_id, inv_name, fuel, f_class, hw, focus, flame, mat = studies[idx % len(studies)]
        o2 = float(np.round(rng.uniform(0.18, 0.85 if inv_id == "PSI-115" else 0.45), 2))
        pressure = float(np.round(rng.uniform(45.0, 105.0), 1))
        rows.append({
            "record_id": f"{inv_id}:{inv_name}:{idx + 1}",
            "investigation_id": inv_id,
            "investigation_name": inv_name,
            "test_id": f"T-{100 + idx}",
            "flame_type": flame,
            "fuel": fuel,
            "fuel_class": f_class,
            "material": mat,
            "hardware": hw,
            "focus": focus,
            "oxygen_fraction": o2,
            "pressure_kpa": pressure,
            "fuel_flow_mg_s": float(np.round(rng.uniform(0.5, 12.0), 2)),
            "airflow_cm_s": float(np.round(rng.uniform(1.0, 35.0), 1)),
            "droplet_initial_diameter_mm": float(np.round(rng.uniform(1.2, 4.5), 2)) if f_class == "liquid droplet" else np.nan,
            "burn_time_s": float(np.round(rng.uniform(3.0, 95.0), 1)),
            "duration_s": float(np.round(rng.uniform(10.0, 140.0), 1)),
            "ignition_success": bool(o2 > 0.20),
            "inference_notes": "Dato placeholder simulado para vista previa",
        })

    return pd.DataFrame(rows)

#=====================
@st.cache_data
def load_csv_data() -> pd.DataFrame:
    if MASTER_PATH.exists():
        return pd.read_csv(MASTER_PATH)
    return pd.DataFrame()



# Parametros

st.sidebar.header("Modo de vista previa")

has_real_csv = MASTER_PATH.exists()
placeholder_mode = st.sidebar.radio(
    "Fuente de la gráfica",
    options=[
        "Placeholder con datos simulados",
        "Placeholder vacío (solo estructura)",
        *(["CSV real (experiments.csv)"] if has_real_csv else []),
    ],
    index=0,
)

#TODO ============================================
chart_type = st.sidebar.selectbox(
    "Tipo de gráfica",
    ["Dispersión (Scatter)", "Distribución (Box Plot)", "Comparativa (Barras)"],
)

x_col = st.sidebar.selectbox(
    "Eje X",
    options=list(NUMERIC_LABELS.keys()) + list(CATEGORICAL_LABELS.keys()),
    index=0,  # oxygen_fraction
    format_func=lambda c: NUMERIC_LABELS.get(c, CATEGORICAL_LABELS.get(c, c)),
)

y_col = st.sidebar.selectbox(
    "Eje Y",
    options=list(NUMERIC_LABELS.keys()),
    index=1,  # pressure_kpa
    format_func=lambda c: NUMERIC_LABELS.get(c, c),
)

color_col = st.sidebar.selectbox(
    "Agrupar / Colorear por",
    options=list(CATEGORICAL_LABELS.keys()),
    index=0,  # fuel
    format_func=lambda c: CATEGORICAL_LABELS.get(c, c),
)

st.sidebar.divider()
st.sidebar.header("Filtros de datos")
#===================================================

for col in ["investigation_id", "fuel", "hardware", "fuel_class"]:
    options = sorted(filtered[col].dropna().astype(str).unique())
    options = [opt for opt in options if opt.strip()]
    if options:
        selected = st.sidebar.multiselect(
            CATEGORICAL_LABELS[col],
            options=options,
            default=[],
            placeholder="Todos",
        )
        if selected:
            filtered = filtered[filtered[col].astype(str).isin(selected)]

if filtered["oxygen_fraction"].notna().any():
    o2_range = st.sidebar.slider(
        "Rango de fracción de O₂",
        min_value=0.0,
        max_value=1.0,
        value=(0.0, 1.0),
        step=0.01,
    )
    filtered = filtered[
        filtered["oxygen_fraction"].isna()
        | filtered["oxygen_fraction"].between(o2_range[0], o2_range[1])
    ]

show_lunar_zone = False
if x_col == "oxygen_fraction" and y_col == "pressure_kpa":
    show_lunar_zone = st.sidebar.checkbox(
        "Resaltar zona hábitat lunar (O₂ ≥ 30%, P ≤ 70.3 kPa)",
        value=True,
    )

# Grafica
st.title("NASA PSI — Explorador de Seguridad contra Incendios")

labels = {**NUMERIC_LABELS, **CATEGORICAL_LABELS}
x_label = labels.get(x_col, x_col)
y_label = labels.get(y_col, y_col)
color_label = labels.get(color_col, color_col)

if placeholder_mode == "Placeholder vacío (solo estructura)":
    st.caption("Vista previa de estructura — sin datos cargados todavía.")
    fig = go.Figure()
    fig.add_shape(
        type="rect",
        xref="paper",
        yref="paper",
        x0=0.04,
        y0=0.08,
        x1=0.96,
        y1=0.92,
        line=dict(color="#64748b", width=2, dash="dash"),
        fillcolor="rgba(148, 163, 184, 0.08)",
    )
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.55,
        text="<b>[ PLACEHOLDER DE GRÁFICA ]</b>",
        showarrow=False,
        font=dict(size=24, color="#94a3b8"),
    )
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.45,
        text=(
            f"Tipo: {chart_type} | Eje X: {x_label}<br>"
            f"Eje Y: {y_label} | Color: {color_label}<br>"
            f"Registros que pasarían el filtro actual: {len(filtered)}"
        ),
        showarrow=False,
        font=dict(size=14, color="#cbd5e1"),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(template="plotly_dark", height=650, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

else:
    is_simulated = placeholder_mode == "Placeholder con datos simulados"
    badge = " (MODO PLACEHOLDER — DATOS SIMULADOS)" if is_simulated else ""
    st.caption(
        f"Mostrando **{len(filtered)}** registros de "
        f"**{filtered['investigation_id'].nunique()}** investigaciones{badge}."
    )

    plot_df = filtered.dropna(subset=[x_col, y_col]).copy()
    plot_df[color_col] = plot_df[color_col].fillna("Sin especificar").astype(str)

    hover_cols = [
        c
        for c in ["record_id", "investigation_id", "test_id", "hardware", "material", "focus", "inference_notes"]
        if c in plot_df.columns
    ]

    if plot_df.empty:
        st.warning("No hay registros válidos para combinar los ejes y filtros seleccionados.")
    else:
        if chart_type == "Dispersión (Scatter)":
            fig = px.scatter(
                plot_df,
                x=x_col,
                y=y_col,
                color=color_col,
                hover_data=hover_cols,
                labels=labels,
                height=650,
            )
            fig.update_traces(marker=dict(size=11, opacity=0.85, line=dict(width=0.8, color="white")))

            if show_lunar_zone:
                fig.add_vrect(
                    x0=0.30,
                    x1=max(1.0, float(plot_df[x_col].max())),
                    fillcolor="rgba(255, 165, 0, 0.12)",
                    line_width=1,
                    line_dash="dash",
                    line_color="orange",
                    annotation_text="Régimen O₂ Lunar (≥30%)",
                    annotation_position="top left",
                )
                fig.add_hline(
                    y=70.33,
                    line_dash="dot",
                    line_color="red",
                    annotation_text="Límite presión lunar (~10.2 psi / 70.3 kPa)",
                    annotation_position="bottom right",
                )

        elif chart_type == "Distribución (Box Plot)":
            fig = px.box(
                plot_df,
                x=color_col,
                y=y_col,
                color=color_col,
                points="all",
                hover_data=hover_cols,
                labels=labels,
                height=650,
            )

        else:
            agg_df = (
                plot_df.groupby([color_col], as_index=False)[y_col]
                .mean()
                .sort_values(y_col, ascending=False)
            )
            fig = px.bar(
                agg_df,
                x=color_col,
                y=y_col,
                color=color_col,
                labels={**labels, y_col: f"Media de {y_label}"},
                height=650,
            )

        if is_simulated:
            fig.add_annotation(
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                text="PLACEHOLDER",
                showarrow=False,
                font=dict(size=64, color="rgba(255, 255, 255, 0.08)"),
                textangle=-20,
            )

        fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
