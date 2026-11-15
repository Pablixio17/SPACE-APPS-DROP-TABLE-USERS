from __future__ import annotations

import json
import sqlite3
from typing import Any

from google import genai
from google.genai import types
import pandas as pd

from response import Response


def _extract_available_columns(selected: pd.DataFrame) -> dict[str, list[str]]:
    """Detect valid numeric and categorical columns in the filtered DataFrame."""
    excluded_redundant = {"oxygen_fraction", "pressure_psi"}  # Deja solo oxygen_pct y pressure_kpa (o viceversa)
    numeric_cols = [
        col
        for col in selected.select_dtypes(include="number").columns
        if col not in excluded_redundant and selected[col].notna().sum() >= 2
    ]
    categorical_cols = [
        col
        for col in selected.select_dtypes(exclude="number").columns
        if 1 < selected[col].nunique(dropna=True) <= 30 and col != "record_id"
    ]
    return {
        "numeric_for_axes": numeric_cols,
        "categorical_for_color": categorical_cols,
    }


def _summarize_numeric(
    df: pd.DataFrame, numeric_cols: list[str]
) -> dict[str, dict[str, float | int]]:
    """Compute compact descriptive statistics for each numeric column."""
    stats: dict[str, dict[str, float | int]] = {}
    for col in numeric_cols:
        valid = df[col].dropna()
        if valid.empty:
            continue
        stats[col] = {
            "count": int(valid.count()),
            "min": round(float(valid.min()), 4),
            "mean": round(float(valid.mean()), 4),
            "median": round(float(valid.median()), 4),
            "max": round(float(valid.max()), 4),
        }
    return stats


def _summarize_categories(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Summarize top value distributions across key experimental dimensions."""
    candidate_cols = [
        "record_scope",
        "fuel_class",
        "fuel",
        "material_category",
        "material",
        "flame_type",
        "visual_phenomena",
        "hardware",
        "flow_regime",
        "safety_pillar",
        "gravity_regime",
        "study_environment",
        "quality_label",
        "ignition_label",
        "traffic_light",
    ]
    distributions: dict[str, dict[str, int]] = {}
    for col in candidate_cols:
        if col not in df.columns:
            continue
        cleaned = df[col].dropna()
        cleaned = cleaned[
            cleaned.astype(str).str.strip().isin(["", "-", "nan", "None"])
            == False
        ]
        if cleaned.empty:
            continue
        counts = cleaned.value_counts().head(8)
        distributions[col] = {str(k): int(v) for k, v in counts.items()}
    return distributions


def _summarize_by_study(
    df: pd.DataFrame, numeric_cols: list[str], max_studies: int = 15
) -> list[dict[str, Any]]:
    """Aggregate record counts and numeric ranges per investigation_id."""
    if "investigation_id" not in df.columns:
        return []

    top_ids = (
        df["investigation_id"].value_counts().head(max_studies).index.tolist()
    )
    study_summaries: list[dict[str, Any]] = []

    for inv_id in top_ids:
        sub = df[df["investigation_id"] == inv_id]
        entry: dict[str, Any] = {
            "investigation_id": str(inv_id),
            "record_count": int(len(sub)),
        }
        if "acronym" in sub.columns and sub["acronym"].notna().any():
            entry["acronym"] = str(sub["acronym"].dropna().iloc[0])
        if "ignition_label" in sub.columns:
            entry["ignition_outcomes"] = {
                str(k): int(v)
                for k, v in (
                    sub["ignition_label"].dropna().value_counts().items()
                )
            }
        entry["metrics"] = _summarize_numeric(sub, numeric_cols)
        study_summaries.append(entry)

    return study_summaries


def _extract_documentary_context(
    selected: pd.DataFrame,
    projects: Any,
    database: sqlite3.Connection | None,
    max_studies: int = 10,
) -> list[dict[str, Any]]:
    """Retrieve linked metadata and documentary excerpts for active studies."""
    if "investigation_id" not in selected.columns:
        return []

    active_ids = set(selected["investigation_id"].dropna().unique().tolist())
    context: list[dict[str, Any]] = []

    if isinstance(projects, dict):
        for inv_id, meta in projects.items():
            if inv_id in active_ids and isinstance(meta, dict):
                context.append({"investigation_id": str(inv_id), **meta})
    elif isinstance(projects, list):
        for item in projects:
            if (
                isinstance(item, dict)
                and item.get("investigation_id") in active_ids
            ):
                context.append(item)

    if database is not None and not context:
        try:
            tables = [
                row[0]
                for row in database.execute(
                    "SELECT name FROM sqlite_master WHERE type='table';"
                ).fetchall()
            ]
            for table in tables:
                cols = [
                    row[1]
                    for row in database.execute(
                        f"PRAGMA table_info({table});"
                    ).fetchall()
                ]
                if "investigation_id" in cols:
                    placeholders = ",".join("?" for _ in active_ids)
                    query = (
                        f"SELECT * FROM {table} WHERE investigation_id IN"
                        f" ({placeholders}) LIMIT 25;"
                    )
                    rows = database.execute(query, list(active_ids)).fetchall()
                    for r in rows:
                        row_dict = {
                            cols[i]: (
                                str(r[i])[:400]
                                if isinstance(r[i], str)
                                else r[i]
                            )
                            for i in range(len(cols))
                            if r[i] is not None
                        }
                        context.append(row_dict)
                    break
        except sqlite3.Error:
            pass

    return context[:max_studies]


def build_prompt_payload(
    selected: pd.DataFrame,
    projects: Any,
    database: sqlite3.Connection | None,
    user_goal: str,
    active_filters: dict[str, Any],
) -> str:
    """Compress filtered records and documentary metadata into a structured JSON prompt."""
    available_columns = _extract_available_columns(selected)
    numeric_cols = available_columns["numeric_for_axes"]

    payload = {
        "user_goal": (
            user_goal.strip()
            or "Provide a comprehensive combustion and spacecraft fire safety synthesis of the filtered experiments."
        ),
        "active_filters": active_filters,
        "dataset_overview": {
            "total_filtered_records": int(len(selected)),
            "unique_investigations": (
                int(selected["investigation_id"].nunique())
                if "investigation_id" in selected.columns
                else 0
            ),
        },
        "available_columns": available_columns,
        "global_numeric_stats": _summarize_numeric(selected, numeric_cols),
        "categorical_distributions": _summarize_categories(selected),
        "study_breakdown": _summarize_by_study(selected, numeric_cols),
        "documentary_context": _extract_documentary_context(
            selected, projects, database
        ),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


class DashboardAIService:
    """Service wrapper around Google Gemini Structured Outputs for dashboard
    block generation."""

    def __init__(
        self, api_key: str, model: str = "gemini-3.5-flash-lite"
    ) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.sys_instruction = (
            "You are a senior NASA microgravity combustion and spacecraft fire"
            " safety research analyst. Your task is to synthesize the provided"
            " experimental dataset summary and documentary context into a"
            " dynamic, modular dashboard matching the Response"
            " schema.\n\nFollow these strict engineering rules:\n1. Ground"
            " every metric, table cell, comparison, and insight strictly in"
            " the JSON evidence provided. Never fabricate numbers, test"
            " conditions, or experimental outcomes.\n2. Tailor the depth,"
            " framing, and block selection to"
            " 'active_filters.user_perspective' and 'user_goal'.\n3. Place"
            " related 'kpi' blocks consecutively at the beginning of 'page' so"
            " the UI renders them in a horizontal metric row.\n4. For 'graph'"
            " blocks, NEVER invent column names or coordinates. Strictly"
            " select 'x_col' and 'y_col' from"
            " 'available_columns.numeric_for_axes', and 'color_by' from"
            " 'available_columns.categorical_for_color'. Use"
            " chart_type='scatter' for experimental test distributions (e.g.,"
            " oxygen vs. pressure) and chart_type='line' only when plotting"
            " ordered parameter progressions. Omit 'graph' blocks if fewer"
            " than 2 numeric columns are available.\n5. Use 'warn' blocks"
            " ('red' for severe flammability/atmospheric hazards, 'yellow' for"
            " data gaps, quality flags, or proxy-environment limitations such"
            " as lunar reference scenarios, 'green' for verified safe"
            " baselines).\n6. Write all user-facing text, titles, labels, and"
            " recommendations in clear, technical English."
        )

    def generate_from_payload(self, payload: str) -> Response:
        """Send the compressed evidence payload to Gemini and validate the
        structured Response."""
        result = self.client.models.generate_content(
            model=self.model,
            contents=payload,
            config=types.GenerateContentConfig(
                system_instruction=self.sys_instruction,
                response_mime_type="application/json",
                response_schema=Response,
                temperature=0.2,
            ),
        )
        if not result.text:
            raise ValueError("Gemini returned an empty response.")
        return Response.model_validate_json(result.text)
