from typing import Literal, Union
from pydantic import BaseModel, Field


class Graphic(BaseModel):
    """Specification for a 2D scientific chart rendered directly from the
    filtered dataset."""

    type: Literal["graph"]
    title: str = Field(
        description="Clear, descriptive title of the scientific chart."
    )
    chart_type: Literal["scatter", "line"] = Field(
        description=(
            "Use 'scatter' for experimental distributions and 'line' for"
            " ordered trends."
        )
    )
    x_col: str = Field(
        description=(
            "Exact numeric column name from available_columns for the X axis."
        )
    )
    y_col: str = Field(
        description=(
            "Exact numeric column name from available_columns for the Y axis."
        )
    )
    color_by: str = Field(
        description=(
            "Exact categorical column name from available_columns used to"
            " group and color data points."
        )
    )


class KPIMetric(BaseModel):
    """A high-impact numerical metric or threshold value to highlight at a
    glance (e.g., critical flammability limits or ignition temperatures)."""

    type: Literal["kpi"]
    label: str = Field(
        description=(
            "Name of the physical parameter or metric being highlighted."
        )
    )
    value: str = Field(
        description=(
            "Numerical value followed by its unit (e.g., '23.5 % O2' or '55"
            " kPa')."
        )
    )
    context: str = Field(
        description=(
            "Brief contextual note explaining the test conditions or"
            " relevance."
        )
    )


class ComparisonTable(BaseModel):
    """Structured table comparing multiple materials, experimental conditions,
    gravity regimes, or fire safety parameters side by side."""

    type: Literal["cmptab"]
    title: str = Field(
        description="Title or caption summarizing what the table compares."
    )
    columns: list[str] = Field(description="List of column headers.")
    rows: list[list[str]] = Field(
        description=(
            "List of data rows. Every inner list must have the exact same"
            " number of elements as the columns list."
        )
    )


class WarningText(BaseModel):
    """A callout banner highlighting critical fire safety hazards, operational
    risks, or key takeaways based on severity."""

    type: Literal["warn"]
    content: str = Field(
        description=(
            "Concise safety alert, hazard warning, or critical operational"
            " note."
        )
    )
    color: Literal["red", "yellow", "green"] = Field(
        description=(
            "Severity indicator: 'red' for critical fire hazards, 'yellow' for"
            " cautions/limitations,'green' for verified safe conditions."
        )
    )


class EquipmentInsight(BaseModel):
    """Actionable engineering guidance regarding next-generation fire
    detection, suppression, ventilation, or material selection."""

    type: Literal["equip"]
    category: Literal[
        "detection", "suppression", "ventilation", "material_selection"
    ] = Field(
        description=(
            "Functional fire safety subsystem addressed by this insight."
        )
    )
    technology: str = Field(
        description=(
            "Name or description of the fire safety system, sensor, or"
            " material."
        )
    )
    recommendation: str = Field(
        description=(
            "Actionable engineering recommendation on how to apply or adapt"
            " this technology for space environments."
        )
    )
    trl_estimate: Literal[
        "low_research", "mid_prototype", "high_flight_ready"
    ] = Field(
        description=(
            "Estimated Technology Readiness Level: 'low_research' (TRL 1-3"
            " basic science), 'mid_prototype' (TRL 4-6 ground/parabolic"
            " testing), or 'high_flight_ready' (TRL 7-9 space-proven)."
        )
    )


class Text(BaseModel):
    """Standard narrative prose for executive summaries, scientific
    explanations, methodology context, or connecting insights between blocks.
    """

    type: Literal["text"]
    content: str = Field(
        description="Clear, well-structured explanatory text."
    )


Brick = Union[
    Graphic, KPIMetric, ComparisonTable, WarningText, EquipmentInsight, Text
]


class Response(BaseModel):
    page: list[Brick] = Field(
        description=(
            "Ordered, dynamic sequence of dashboard blocks. Combine, order,"
            " and repeat block types as needed to best present the scientific"
            " findings, quantitative data, and safety recommendations."
        )
    )
