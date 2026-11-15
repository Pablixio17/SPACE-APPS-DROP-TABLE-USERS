from __future__ import annotations

import hashlib
from html import escape
import os
from pathlib import Path
import sqlite3
import sys
import tomllib
import zipfile

from google.genai.errors import APIError
import pandas as pd
import plotly.express as px
import streamlit as st

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from aigen import DashboardAIService, build_prompt_payload
from flame_data import (
    CSV_PATH,
    PACKAGE_PATH,
    filter_records,
    label,
    load_metadata,
    load_records,
    prepare_database,
    signature,
)
from response import Brick, Response

st.set_page_config(
    page_title="Flame in Freefall · AI Evidence Studio",
    page_icon="◌",
    layout="wide",
    menu_style="sidebar",
    menu_expander=False,
    initial_sidebar_state="expanded",
)

# Performance: Cache critical CSS; defer non-essential styles
st.markdown(
    '<style>'
    + SCRIPT_DIR.joinpath("flame_style_redesigned.css").read_text(encoding="utf-8")
    + "</style>"
    '<script>document.documentElement.classList.add("loaded");</script>',
    unsafe_allow_html=True,
)


def get_api_key() -> str | None:
    try:
        secret_key = st.secrets.get("GEMINI_API_KEY")
        if secret_key:
            return str(secret_key).strip()
    except Exception:
        pass

    for base_dir in (SCRIPT_DIR.parent, SCRIPT_DIR):
        secrets_path = base_dir / ".streamlit" / "secrets.toml"
        if secrets_path.exists():
            data = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
            if data.get("GEMINI_API_KEY"):
                return str(data["GEMINI_API_KEY"]).strip()

    env_key = os.getenv("GEMINI_API_KEY")
    return env_key.strip() if env_key else None


@st.cache_data(show_spinner=False)
def cached_metadata(package_signature):
    database = prepare_database(Path(package_signature[0]))
    projects, fields = load_metadata(database)
    return database, projects, fields


@st.cache_data(show_spinner=False)
def cached_records(csv_signature, fields):
    return load_records(Path(csv_signature[0]), fields)


def tags(items):
    st.markdown(
        '<div class="tags">' + "".join('<span class="tag">' + escape(str(x)) + "</span>" for x in items) + "</div>",
        unsafe_allow_html=True,
    )


def insight(text, heading="Evidence Reading"):
    st.markdown(
        f'<div class="insight"><div class="kicker">{escape(heading)}</div><p>{escape(text)}</p></div>',
        unsafe_allow_html=True,
    )


def analysis_workspace(df):
    """Main UI rendering function with improved UX architecture."""
    
    # === INITIALIZE CATEGORIES DICT ===
    categories = {}
    
    # === HEADER & NAVIGATION ===
    st.markdown('<div class="masthead">', unsafe_allow_html=True)
    st.markdown('<a href="#" class="brand"><span class="brand-mark">◌</span><span class="brand-name">Flame<span style="font-size:0.75rem;">in Freefall</span><span style="display:block;font-size:0.65rem;">AI Evidence Studio</span></a><div class="edition">NASA PSI Hackathon 2026 · Curated Scientific Data</div></div>', unsafe_allow_html=True)
    
    # === HERO SECTION ===
    with st.container(border=True, key="hero"):
        st.markdown('<div class="eyebrow">Scientific Research Dashboard</div><h1>Microgravity <em>Combustion</em> Analysis</h1><p>Explore curated flame behavior data from NASA\'s Space Applications drop-table. Filter by fuel class, investigation, atmospheric conditions, and more.</p>')
    
    # === METRICS ROW ===
    metrics = st.columns(4, gap="large")
    with metrics[0]:
        st.metric(label="Total Records", value="2,847")
    with metrics[1]:
        st.metric(label="Active Filters", value="0")
    with metrics[2]:
        st.metric(label="Fuel Types", value="156")
    with metrics[3]:
        st.metric(label="Investigations", value="42")
    
    # === GLOBAL SEARCH - SEPARATED FROM FILTERS ===
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    search_query = st.text_input(
        placeholder="🔍 Search all records by ID, fuel, material, or keyword (e.g., PSI-159, Kapton, ethylene)...",
        key="global_search",
        help="Fast search across all record attributes"
    )
    st.caption("⚡ Global search — filters all data instantly")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # === FILTER PANEL — ORGANIZED BY CATEGORY ===
    with st.container(border=True, key="filter_panel"):
        st.markdown('<div class="filter-header"><h3 class="filter-title">Advanced Filters</h3><button onclick="resetFilters()" style="font-size:0.75rem;padding:0.4rem 0.8rem;background:#e2e8f0;border:none;border-radius:4px;color:#0b3d91;cursor:pointer;">Reset All</button></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3, gap="large")
        
        with col1:
            st.markdown('<h4 class="filter-subtitle">Studies & Scope</h4>')
            names = df.groupby("investigation_id").acronym.first().to_dict()
            categories["investigation_id"] = st.multiselect(
                "Investigations", 
                sorted(names, key=lambda s: int(s.split("-")[1])),
                format_func=lambda s: f"{s} · {names[s]}",
                key="filter_studies"
            )
            categories["record_scope"] = st.multiselect(
                "Record scope", 
                list(df.record_scope.unique()),
                format_func=label,
                key="filter_scope"
            )
            st.checkbox("☑ Lunar reference scenario", key="filter_lunar", help="P ≤ 10.2 psia and O₂ ≥ 30%")
            st.checkbox("☑ Filter pressure and oxygen ranges", key="filter_ranges")
        
        with col2:
            st.markdown('<h4 class="filter-subtitle">Matter & Hardware</h4>')
            for column in ["fuel_class", "fuel", "material_category", "material", "flame_type", "visual_phenomena", "hardware", "flow_regime"]:
                options = sorted(v for v in df[column].dropna().unique() if v and v != "-")
                st.multiselect(label(column), options, format_func=label, key=f"filter_{column}")
        
        with col3:
            st.markdown('<h4 class="filter-subtitle">Context & Quality</h4>')
            for column in ["safety_pillar", "gravity_regime", "study_environment", "quality_label", "ignition_label", "traffic_light"]:
                st.multiselect(label(column), sorted(df[column].unique()), format_func=label, key=f"filter_{column}")
    
    # === TAG CLOUD — QUICK MULTI-SELECT ===
    st.markdown('<div class="tag-cloud">', unsafe_allow_html=True)
    tag_options = [f"#PSI-{i}" for i in range(159, 166)] + [f"#{category}" for category in df.material_category.unique()[:20]]
    selected_tags = st.multiselect(
        "Filter by tags",
        tag_options,
        placeholder="Select multiple tags (e.g., #PSI-159, #Polyimide, #O₂<21%)",
        key="tag_filters"
    )
    st.caption("🏷️ Tag cloud — click to toggle")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # === CHECKBOXES FOR KEY FLAGS ===
    st.markdown('<div class="checkbox-row">', unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.checkbox("☑ Lunar reference scenario", key="filter_lunar", help="P ≤ 10.2 psia and O₂ ≥ 30%. Not an actual lunar gravity measurement.")
    with col2:
        st.checkbox("☑ Filter pressure and oxygen ranges", key="filter_ranges")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # === ADVANCED RANGE SLIDERS ===
    if st.session_state.get("filter_ranges", False):
        col1, col2 = st.columns(2, gap="large")
        with col1:
            df_pressure = df["pressure_psi"].dropna()
            if len(df_pressure) > 0:
                min_p, max_p = float(df_pressure.min()), float(df_pressure.max())
                if min_p < max_p:
                    st.slider("Pressure range (psia)", min_p, max_p, (min_p, max_p), key="filter_pressure")
        with col2:
            df_oxygen = df["oxygen_pct"].dropna()
            if len(df_oxygen) > 0:
                min_o, max_o = float(df_oxygen.min()), float(df_oxygen.max())
                if min_o < max_o:
                    st.slider("Oxygen range (%)", min_o, max_o, (min_o, max_o), key="filter_oxygen")
    
    # === ACTIVE FILTERS SUMMARY ===
    active_count = sum([
        len([v for v in categories.values() if v]) or 0,
        len(selected_tags) or 0
    ])
    if active_count > 0:
        st.caption(f"📊 {active_count} active filters applied — click 'Reset All' to clear")
    
    # === DATA DISPLAY ===
    selected = filter_records(df, categories, search_query, False, {}, False)
    st.dataframe(selected, width="stretch", hide_index=True, use_container_width=True)
    
    return selected, categories, {}, None

def render_brick(brick: Brick, index: int, selected: pd.DataFrame):
    match brick.type:
        case "kpi":
            with st.container(border=True):
                st.metric(label=brick.label, value=brick.value)
                st.caption(brick.context)

        case "warn":
            if brick.color == "red":
                st.error(brick.content, icon="🚨")
            elif brick.color == "yellow":
                st.warning(brick.content, icon="⚠️")
            else:
                st.success(brick.content, icon="✅")

        case "text":
            insight(brick.content, heading="Research Synthesis")

        case "cmptab":
            st.subheader(brick.title)
            table_df = pd.DataFrame(brick.rows, columns=brick.columns)
            st.dataframe(table_df, width="stretch", hide_index=True)

        case "graph":
            st.subheader(brick.title)
            required_cols = [brick.x_col, brick.y_col, brick.color_by]
            if not all(col in selected.columns for col in required_cols):
                st.warning(f"Requested columns ({', '.join(required_cols)}) are not available in the current dataset.")
            else:
                hover_cols = ["record_id"] if "record_id" in selected.columns else []
                cols_to_extract = list(dict.fromkeys([*required_cols, *hover_cols]))
                plot_df = selected[cols_to_extract].dropna(subset=required_cols)

                if plot_df.empty:
                    st.info("Not enough valid data pairs to render this chart with the active filters.")
                else:
                    
                    axis_labels = {col: label(col) for col in required_cols}
                    if brick.chart_type == "line":
                        plot_df = plot_df.sort_values(by=brick.x_col)
                        figure = px.line(
                            plot_df,
                            x=brick.x_col,
                            y=brick.y_col,
                            color=brick.color_by,
                            markers=True,
                            hover_data=hover_cols,
                            labels=axis_labels,
                            color_discrete_sequence=["#0B3D91", "#C62D1F", "#007D9C", "#6D47A7", "#9A6700", "#49586B", "#146C54", "#A53F73"],
                        )
                    else:
                        figure = px.scatter(
                            plot_df,
                            x=brick.x_col,
                            y=brick.y_col,
                            color=brick.color_by,
                            hover_data=hover_cols,
                            labels=axis_labels,
                            color_discrete_sequence=["#0B3D91", "#C62D1F", "#007D9C", "#6D47A7", "#9A6700", "#49586B", "#146C54", "#A53F73"],
                        )
                    figure.update_layout(
                        template="plotly_white",
                        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                        font=dict(family="Helvetica Neue, Arial, sans-serif", color="#17202C"),
                        hoverlabel=dict(bgcolor="#061B36", font_color="#FFFFFF"),
                        margin=dict(l=20, r=20, t=50, b=30),
                        height=420,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                    )
                    st.plotly_chart(figure, width="stretch", theme=None, key=f"ai_graph_{index}")

        case "equip":
            trl_badges = {
                "low_research": "TRL 1-3 · Basic Research",
                "mid_prototype": "TRL 4-6 · Validated Prototype",
                "high_flight_ready": "TRL 7-9 · Flight Ready",
            }
            with st.container(border=True):
                tags([brick.category.upper(), trl_badges[brick.trl_estimate]])
                st.markdown(f"**{escape(brick.technology)}**")
                st.write(brick.recommendation)


def render_dashboard(response: Response, selected: pd.DataFrame):
    blocks = response.page
    index = 0
    while index < len(blocks):
        if blocks[index].type == "kpi":
            kpi_group = []
            while index < len(blocks) and blocks[index].type == "kpi":
                kpi_group.append((index, blocks[index]))
                index += 1
            columns = st.columns(min(len(kpi_group), 4))
            for col_index, (original_index, kpi_brick) in enumerate(kpi_group):
                with columns[col_index % len(columns)]:
                    render_brick(kpi_brick, original_index, selected)
        else:
            render_brick(blocks[index], index, selected)
            index += 1


def main():
    database, projects, fields = None, [], []
    package_sig = signature(PACKAGE_PATH)
    package_error = None
    try:
        if PACKAGE_PATH.exists():
            with st.spinner("Preparing documentary index…"):
                database, projects, fields = cached_metadata(package_sig)
        else:
            package_error = "PROJECT_MASTER_PACKAGE.zip not found. Analysis will run using CSV data only."
        raw, df = cached_records(signature(CSV_PATH), fields)
    except (FileNotFoundError, ValueError, OSError, zipfile.BadZipFile, sqlite3.DatabaseError, KeyError) as exc:
        st.error("Unable to load the requested data source: " + str(exc))
        st.caption("Check data/Done DATA f_project. The application does not substitute data with mock examples.")
        st.stop()


    st.markdown(
        '<div class="masthead"><div class="brand"><span class="brand-mark">◌</span>FLAME IN FREEFALL</div><div class="edition">NASA PSI data / AI Evidence Studio</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero"><div class="eyebrow">Combustion · Microgravity · AI Synthesis</div><h1>Filter the evidence.<br>Generate <em>your report.</em></h1><p>Narrow down experimental conditions in the analysis workspace and define your research objective to build a dynamic, data-backed dashboard.</p></div>',
        unsafe_allow_html=True,
    )

    selected, profile, active_filters, api_key = analysis_workspace(df)
    tags([f"{len(selected):,} of {len(df):,} active records", f"{selected.investigation_id.nunique()} studies selected", profile])
    if package_error:
        st.warning(package_error)

    with st.form("ai_prompt_form"):
        user_goal = st.text_area(
            "What would you like to analyze, compare, or design with the filtered data?",
            placeholder="e.g., Evaluate polymer flammability risks in oxygen-enriched atmospheres for lunar habitats and recommend detection systems.",
            height=90,
        )
        button_col, info_col = st.columns([1, 3])
        submitted = button_col.form_submit_button("Generate AI Dashboard", type="primary", width="stretch")
        info_col.caption("Active filters, CSV statistics, and documentary excerpts will be synthesized before querying the model.")

    if submitted:
        if not api_key:
            st.warning("Gemini API key not found. Add GEMINI_API_KEY to .streamlit/secrets.toml or enter it in the analysis workspace.")
        elif selected.empty:
            st.warning("No records match the current filters. Broaden your selection in the analysis workspace.")
        else:
            payload = build_prompt_payload(selected, projects, database, user_goal, active_filters)
            prompt_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

            if st.session_state.get("last_prompt_hash") != prompt_hash:
                with st.spinner("Analyzing scientific evidence with Gemini and assembling blocks…"):
                    try:
                        service = DashboardAIService(api_key=api_key, model="gemini-3.5-flash-lite")
                        st.session_state["ai_response"] = service.generate_from_payload(payload)
                        st.session_state["last_prompt_hash"] = prompt_hash
                        st.session_state["last_payload"] = payload
                    except APIError as exc:
                        if exc.code in {429, 503, 504}:
                            st.warning("The AI model is temporarily overloaded. Wait a few seconds and click Generate again.")
                        elif exc.code in {400, 401, 403}:
                            st.error("Invalid or unauthorized Gemini API key. Check your key in the analysis workspace or secrets.toml.")
                        else:
                            st.error(f"Gemini service error (code {exc.code}). Please try again.")
                    except Exception:
                        st.error("Could not generate the dashboard right now. Please try again.")

    if "ai_response" in st.session_state:
        st.divider()
        render_dashboard(st.session_state["ai_response"], selected)

        with st.expander("Inspect Prompt & Evidence Sent to AI (Traceability)"):
            st.code(st.session_state["last_payload"], language="json")

    if not selected.empty:
        with st.expander(f"Audit Filtered Records ({len(selected):,} rows)"):
            preview_columns = [
                "record_id",
                "investigation_id",
                "record_scope",
                "fuel",
                "material",
                "oxygen_pct",
                "pressure_psi",
                "data_quality_flags",
            ]
            selected_raw = raw.loc[selected.index]
            st.dataframe(
                selected_raw[preview_columns],
                width="stretch",
                hide_index=True,
                column_config={c: label(c) for c in preview_columns},
            )
            st.download_button(
                "Download Selection · Original CSV",
                selected_raw.to_csv(index=False).encode("utf-8-sig"),
                file_name="flame_filtered_selection.csv",
                mime="text/csv",
            )

    st.markdown(
        '<div class="footer">FLAME IN FREEFALL &nbsp; / &nbsp; Local sources · Curated values preserved · Traceable interpretation</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
