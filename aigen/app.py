from __future__ import annotations

import hashlib
from html import escape
import os
from pathlib import Path
import sqlite3
import sys
import tomllib
import zipfile

from openai import APIError
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

st.set_page_config(page_title="Flame in Freefall · AI Evidence Studio", page_icon="◌", layout="wide")
st.markdown(
    "<style>" + SCRIPT_DIR.joinpath("flame_style.css").read_text(encoding="utf-8") + "</style>",
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


def sidebar(df):
    categories, numeric = {}, {}
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Analysis Workspace</div>', unsafe_allow_html=True)
        st.caption("Combine filters to narrow down the dataset sent to the synthesis engine.")
        if st.button("Reset Filters", width="stretch"):
            for key in list(st.session_state):
                if key.startswith("filter_"):
                    del st.session_state[key]
            st.rerun()

        profile = st.selectbox(
            "Perspective",
            ["General Exploration", "Aerospace Safety", "Learning", "CFD Research"],
            key="filter_profile",
        )

        server_key = get_api_key()
        user_api_key = None
        if not server_key:
            user_api_key = st.text_input(
                "Gemini API Key",
                type="password",
                placeholder="AIzaSy...",
                help="GEMINI_API_KEY was not found in .streamlit/secrets.toml. Your key will only be used in this session.",
            )
        api_key = server_key or user_api_key

        search_query = st.text_input("Search records", placeholder="PSI-159, Kapton, ethylene…", key="filter_text")

        study_names = df.groupby("investigation_id").acronym.first().to_dict()
        categories["investigation_id"] = st.multiselect(
            "Investigations",
            sorted(study_names, key=lambda s: int(s.split("-")[1])),
            format_func=lambda s: s + " · " + study_names[s],
            key="filter_studies",
        )
        categories["record_scope"] = st.multiselect(
            "Record scope", list(df.record_scope.unique()), format_func=label, key="filter_scope"
        )

        with st.expander("Matter, Flame & Hardware"):
            for column in [
                "fuel_class",
                "fuel",
                "material_category",
                "material",
                "flame_type",
                "visual_phenomena",
                "hardware",
                "flow_regime",
            ]:
                options = sorted(v for v in df[column].dropna().unique() if v and v != "-")
                categories[column] = st.multiselect(label(column), options, format_func=label, key="filter_" + column)

        with st.expander("Context & Quality"):
            for column in [
                "safety_pillar",
                "gravity_regime",
                "study_environment",
                "quality_label",
                "ignition_label",
                "traffic_light",
            ]:
                categories[column] = st.multiselect(
                    label(column), sorted(df[column].unique()), format_func=label, key="filter_" + column
                )

        with st.expander("Atmospheric Conditions"):
            lunar = st.checkbox(
                "Lunar reference scenario",
                key="filter_lunar",
                help="P ≤ 10.2 psia and O₂ ≥ 30%. Does not represent an actual lunar gravity measurement.",
            )
            range_on = st.checkbox("Filter pressure and oxygen ranges", key="filter_ranges")
            keep_missing = True
            if range_on:
                for column in ["oxygen_pct", "pressure_psi"]:
                    valid = df[column].dropna()
                    low, high = float(valid.min()), float(valid.max())
                    if low < high:
                        numeric[column] = st.slider(label(column), low, high, (low, high), key="filter_" + column)
                keep_missing = st.checkbox("Keep records missing these measurements", value=True, key="filter_missing")

        st.divider()
        st.caption("CURATED SOURCE")
        st.markdown("**Done DATA f_project**")
        st.caption("Original values preserved · linked documentary context · local analysis")

    selected = filter_records(df, categories, search_query, lunar, numeric, keep_missing)
    active_filters = {
        "user_perspective": profile,
        "search_text": search_query.strip() or None,
        "lunar_reference_scenario": lunar,
        "active_categories": {label(k): v for k, v in categories.items() if v},
        "numeric_ranges": {label(k): list(v) for k, v in numeric.items()},
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
                st.warning(f"Requested columns ({', '.join(required_cols)}) are not available in the current dataset.")
            else:
                hover_cols = ["record_id"] if "record_id" in selected.columns else []
                cols_to_extract = list(dict.fromkeys([*required_cols, *hover_cols]))
                plot_df = selected[cols_to_extract].dropna(subset=required_cols)

                if plot_df.empty:
                    st.info("Not enough valid data pairs to render this chart with the active filters.")
                else:
                    english_names = {
                        "oxygen_pct": "Oxygen Concentration (%)",
                        "oxygen_fraction": "Oxygen Mole Fraction",
                        "pressure_psi": "Chamber Pressure (psia)",
                        "pressure_kpa": "Absolute Pressure (kPa)",
                        "investigation_id": "Investigation",
                        "fuel_class": "Fuel Class",
                        "ignition_label": "Ignition Outcome",
                        "gravity_regime": "Gravity Regime",
                    }
                    axis_labels = {
                        col: english_names.get(col, col.replace("_", " ").title())
                        for col in required_cols
                    }
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
                        )
                    else:
                        figure = px.scatter(
                            plot_df,
                            x=brick.x_col,
                            y=brick.y_col,
                            color=brick.color_by,
                            hover_data=hover_cols,
                            labels=axis_labels,
                        )
                    figure.update_layout(
                        template="plotly_white",
                        margin=dict(l=20, r=20, t=50, b=30),
                        height=420,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                    )
                    st.plotly_chart(figure, width="stretch", key=f"ai_graph_{index}")

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

    selected, profile, active_filters, api_key = sidebar(df)

    st.markdown(
        '<div class="masthead"><div class="brand"><span class="brand-mark">◌</span>FLAME IN FREEFALL</div><div class="edition">NASA PSI data / AI Evidence Studio</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero"><div class="eyebrow">Combustion · Microgravity · AI Synthesis</div><h1>Filter the evidence.<br>Generate <em>your report.</em></h1><p>Narrow down experimental conditions in the sidebar and define your research objective to build a dynamic, data-backed dashboard.</p></div>',
        unsafe_allow_html=True,
    )

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
            st.warning("Gemini API key not found. Add GEMINI_API_KEY to .streamlit/secrets.toml or enter it in the sidebar.")
        elif selected.empty:
            st.warning("No records match the current filters. Broaden your selection in the sidebar.")
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
                            st.error("Invalid or unauthorized Gemini API key. Check your key in the sidebar or secrets.toml.")
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
