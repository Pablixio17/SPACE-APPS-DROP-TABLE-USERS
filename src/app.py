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
    initial_sidebar_state="collapsed",
)

css_path = SCRIPT_DIR / "flame_style.css"
if css_path.exists():
    st.markdown(
        f"<style>{css_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )

PROFILES = [
    "Spacecraft Fire Safety Engineer",
    "Microgravity Combustion Researcher",
    "Lunar Habitat Materials Analyst",
    "Mission Payload & Diagnostics Lead",
]

MATTER_COLUMNS = [
    "fuel_class",
    "fuel",
    "material_category",
    "material",
    "flame_type",
    "visual_phenomena",
    "hardware",
    "flow_regime",
]

CONTEXT_COLUMNS = [
    "safety_pillar",
    "gravity_regime",
    "study_environment",
    "quality_label",
    "ignition_label",
    "traffic_light",
]


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
        '<div class="tags">'
        + "".join('<span class="tag">' + escape(str(x)) + "</span>" for x in items)
        + "</div>",
        unsafe_allow_html=True,
    )


def insight(text, heading="Evidence Reading"):
    st.markdown(
        f'<div class="insight"><div class="kicker">{escape(heading)}</div><p>{escape(text)}</p></div>',
        unsafe_allow_html=True,
    )


def reset_filters():
    for key in list(st.session_state.keys()):
        if key.startswith("filter_") or key in {"global_search", "tag_filters"}:
            del st.session_state[key]


def analysis_workspace(df: pd.DataFrame):
    """Main filtering and configuration workspace."""
    categories: dict[str, list[str]] = {}
    api_key = get_api_key()

    # === TOP CONFIGURATION & GLOBAL SEARCH ===
    top_cols = st.columns([2.2, 1.3, 1.2] if not api_key else [2.5, 1.5], gap="medium")
    with top_cols[0]:
        search_query = st.text_input(
            "Global search",
            placeholder="Search all records by ID, fuel, material, or keyword (e.g., PSI-159, Kapton, ethylene)...",
            key="global_search",
            label_visibility="collapsed",
        )
    with top_cols[1]:
        profile = st.selectbox(
            "Research perspective",
            PROFILES,
            key="research_profile",
            label_visibility="collapsed",
        )
    if not api_key:
        with top_cols[2]:
            entered_key = st.text_input(
                "Gemini API Key",
                type="password",
                placeholder="Paste GEMINI_API_KEY...",
                key="manual_api_key",
                label_visibility="collapsed",
            )
            if entered_key.strip():
                api_key = entered_key.strip()

    # === FILTER PANEL ===
    with st.container(border=True, key="filter_panel"):
        header_col, reset_col = st.columns([5, 1])
        header_col.markdown('<h3 class="filter-title">Advanced Filters</h3>', unsafe_allow_html=True)
        reset_col.button("Reset All", on_click=reset_filters, width="stretch")

        col1, col2, col3 = st.columns(3, gap="large")

        with col1:
            st.markdown('<h4 class="filter-subtitle">Studies & Scope</h4>', unsafe_allow_html=True)
            names = df.groupby("investigation_id")["acronym"].first().to_dict() if "acronym" in df.columns else {}
            study_ids = sorted(
                df["investigation_id"].dropna().unique(),
                key=lambda s: int(s.split("-")[1]) if "-" in s and s.split("-")[1].isdigit() else s,
            )
            categories["investigation_id"] = st.multiselect(
                "Investigations",
                study_ids,
                format_func=lambda s: f"{s} · {names[s]}" if names.get(s) else s,
                key="filter_studies",
            )
            if "record_scope" in df.columns:
                categories["record_scope"] = st.multiselect(
                    "Record scope",
                    sorted(df["record_scope"].dropna().unique()),
                    format_func=label,
                    key="filter_scope",
                )
            lunar_only = st.checkbox(
                "Lunar reference scenario",
                key="filter_lunar",
                help="P ≤ 10.2 psia and O₂ ≥ 30%. Not an actual lunar gravity measurement.",
            )
            use_ranges = st.checkbox(
                "Filter pressure and oxygen ranges",
                key="filter_ranges",
            )

        with col2:
            st.markdown('<h4 class="filter-subtitle">Matter & Hardware</h4>', unsafe_allow_html=True)
            for column in MATTER_COLUMNS:
                if column in df.columns:
                    options = sorted(v for v in df[column].dropna().unique() if v and v != "-")
                    categories[column] = st.multiselect(
                        label(column),
                        options,
                        format_func=label,
                        key=f"filter_{column}",
                    )

        with col3:
            st.markdown('<h4 class="filter-subtitle">Context & Quality</h4>', unsafe_allow_html=True)
            for column in CONTEXT_COLUMNS:
                if column in df.columns:
                    options = sorted(v for v in df[column].dropna().unique() if v and v != "-")
                    categories[column] = st.multiselect(
                        label(column),
                        options,
                        format_func=label,
                        key=f"filter_{column}",
                    )

        # === TAG CLOUD ===
        study_tags = [f"#{sid}" for sid in study_ids]
        category_tags = (
            [f"#{cat}" for cat in sorted(df["material_category"].dropna().unique()) if cat and cat != "-"][:20]
            if "material_category" in df.columns
            else []
        )
        selected_tags = st.multiselect(
            "Quick tags",
            study_tags + category_tags,
            placeholder="Quick-select tags (e.g., #PSI-159, #Polyimide)...",
            key="tag_filters",
        )

        # === OPTIONAL RANGE SLIDERS ===
        ranges: dict[str, tuple[float, float]] = {}
        if use_ranges:
            r_col1, r_col2 = st.columns(2, gap="large")
            with r_col1:
                if "pressure_psi" in df.columns:
                    df_pressure = df["pressure_psi"].dropna()
                    if not df_pressure.empty:
                        min_p, max_p = float(df_pressure.min()), float(df_pressure.max())
                        if min_p < max_p:
                            ranges["pressure_psi"] = st.slider(
                                "Pressure range (psia)",
                                min_p,
                                max_p,
                                (min_p, max_p),
                                key="filter_pressure",
                            )
            with r_col2:
                if "oxygen_pct" in df.columns:
                    df_oxygen = df["oxygen_pct"].dropna()
                    if not df_oxygen.empty:
                        min_o, max_o = float(df_oxygen.min()), float(df_oxygen.max())
                        if min_o < max_o:
                            ranges["oxygen_pct"] = st.slider(
                                "Oxygen range (%)",
                                min_o,
                                max_o,
                                (min_o, max_o),
                                key="filter_oxygen",
                            )

    # Merge quick tags into effective category filters
    effective_categories = {k: list(v) for k, v in categories.items() if v}
    for tag in selected_tags:
        clean_tag = tag.lstrip("#")
        if clean_tag in study_ids:
            effective_categories.setdefault("investigation_id", [])
            if clean_tag not in effective_categories["investigation_id"]:
                effective_categories["investigation_id"].append(clean_tag)
        else:
            effective_categories.setdefault("material_category", [])
            if clean_tag not in effective_categories["material_category"]:
                effective_categories["material_category"].append(clean_tag)

    selected = filter_records(df, effective_categories, search_query, lunar_only, ranges, use_ranges)

    # === LIVE METRICS ROW ===
    active_filter_count = (
        sum(len(v) for v in effective_categories.values())
        + (1 if search_query.strip() else 0)
        + (1 if lunar_only else 0)
        + len(ranges)
    )
    unique_fuels = selected["fuel"].nunique() if "fuel" in selected.columns else 0
    unique_studies = selected["investigation_id"].nunique() if "investigation_id" in selected.columns else 0

    metrics = st.columns(4, gap="medium")
    metrics[0].metric(label="Filtered Records", value=f"{len(selected):,}", delta=f"of {len(df):,} total")
    metrics[1].metric(label="Active Filters", value=str(active_filter_count))
    metrics[2].metric(label="Unique Fuels", value=f"{unique_fuels:,}")
    metrics[3].metric(label="Investigations", value=f"{unique_studies:,}")

    active_filters = {
        "categories": effective_categories,
        "search_query": search_query.strip(),
        "lunar_reference_scenario": lunar_only,
        "ranges": {k: list(v) for k, v in ranges.items()},
    }
    return selected, profile, active_filters, api_key


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
                st.warning(
                    f"Requested columns ({', '.join(required_cols)}) are not available in the current dataset."
                )
            else:
                hover_cols = ["record_id"] if "record_id" in selected.columns else []
                cols_to_extract = list(dict.fromkeys([*required_cols, *hover_cols]))
                plot_df = selected[cols_to_extract].dropna(subset=required_cols)

                if plot_df.empty:
                    st.info("Not enough valid data pairs to render this chart with the active filters.")
                else:
                    axis_labels = {col: label(col) for col in required_cols}
                    palette = [
                        "#0B3D91",
                        "#C62D1F",
                        "#007D9C",
                        "#6D47A7",
                        "#9A6700",
                        "#49586B",
                        "#146C54",
                        "#A53F73",
                    ]
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
                            color_discrete_sequence=palette,
                        )
                    else:
                        figure = px.scatter(
                            plot_df,
                            x=brick.x_col,
                            y=brick.y_col,
                            color=brick.color_by,
                            hover_data=hover_cols,
                            labels=axis_labels,
                            color_discrete_sequence=palette,
                        )
                    figure.update_layout(
                        template="plotly_white",
                        paper_bgcolor="#FFFFFF",
                        plot_bgcolor="#FFFFFF",
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
        st.caption("Check data/processed/. The application does not substitute data with mock examples.")
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
            st.warning("Gemini API key not found. Add GEMINI_API_KEY to .streamlit/secrets.toml or enter it above.")
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
                            st.error("Invalid or unauthorized Gemini API key. Check your key in secrets.toml or the input above.")
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
            candidate_columns = [
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
            preview_columns = [c for c in candidate_columns if c in selected_raw.columns]
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