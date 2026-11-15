"""Consistent, provenance-aware Plotly views; all inputs are already filtered."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from flame_data import LABELS, METRICS, coverage, scalar_records

PALETTE = ["#E46A43", "#387F89", "#786DAD", "#D4A34A", "#647894", "#A96E80", "#529B7F", "#A77953",
           "#5187B5", "#AD854A", "#8B8F54", "#AB5F62", "#548E9C", "#8977AB", "#737E89", "#BD845E"]
STUDIES = ["PSI-10", "PSI-20", "PSI-21", "PSI-22", "PSI-23", "PSI-25", "PSI-26", "PSI-39",
           "PSI-68", "PSI-69", "PSI-101", "PSI-102", "PSI-106", "PSI-107", "PSI-142", "PSI-159"]
STUDY_COLORS = dict(zip(STUDIES, PALETTE))
STUDY_COLORS.update({"PSI-10": "#E46A43", "PSI-159": "#387F89", "PSI-39": "#D4A34A", "PSI-69": "#786DAD"})
SCOPE_COLORS = {"Ensayo": "#387F89", "Observación": "#A9C9C7", "Resumen de estudio": "#E6AF87"}
RESULT_COLORS = {"Éxito": "#387F89", "Fallo": "#E46A43", "Sin dato": "#C9CED3"}

def finish(fig, height=440):
    fig.update_layout(template="plotly_white", height=height, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="#FFFFFF", colorway=PALETTE,
                      font=dict(family="Inter, Segoe UI, sans-serif", color="#283A46", size=12),
                      margin=dict(l=16, r=22, t=30, b=20),
                      legend=dict(title_text="", orientation="h", yanchor="top", y=-0.2, x=0),
                      hoverlabel=dict(bgcolor="#172B38", font_color="white"))
    fig.update_xaxes(gridcolor="#EEF0EF", zerolinecolor="#E4E8E7", automargin=True)
    fig.update_yaxes(gridcolor="#EEF0EF", zerolinecolor="#E4E8E7", automargin=True)
    return fig

def empty_figure(message):
    fig = go.Figure()
    fig.add_annotation(text=message, x=.5, y=.5, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=15, color="#6A7982"))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return finish(fig, 320)

def scatter(df, x="oxygen_pct", y="pressure_psi", color="investigation_id", annotations=False, references=False):
    plotted = scalar_records(df, x, y)
    if plotted.empty:
        return empty_figure("No hay pares de valores válidos para esta selección."), plotted
    # Empty category strings get a display label without altering source values.
    plotted[color] = plotted[color].fillna("").replace("", "Sin dato")
    text = "test_id" if annotations else None
    fig = px.scatter(plotted, x=x, y=y, color=color, symbol="scope_label", text=text,
                     color_discrete_map=STUDY_COLORS if color == "investigation_id" else None,
                     color_discrete_sequence=PALETTE, labels=LABELS,
                     hover_name="study_label", hover_data=["record_id", "test_id", "fuel", "material", "quality_label"],
                     symbol_map={"Ensayo": "circle", "Observación": "diamond"}, render_mode="svg")
    fig.update_traces(marker=dict(size=8, opacity=.73, line=dict(width=.6, color="white")), textposition="top center")
    if references and {x, y} == {"oxygen_pct", "pressure_psi"}:
        for name, oxygen, pressure in [("Tierra / ISS · referencia", 21, 14.7), ("Escenario lunar", 30, 10.2),
                                       ("Exploración · referencia", 34, 8.2)]:
            rx, ry = (oxygen, pressure) if x == "oxygen_pct" else (pressure, oxygen)
            fig.add_trace(go.Scatter(x=[rx], y=[ry], mode="markers+text", text=[name], name=name,
                                     textposition="top right", marker=dict(symbol="x", size=10, color="#172B38")))
        if x == "oxygen_pct":
            fig.add_hline(y=10.2, line_dash="dot", line_color="#C58C69")
            fig.add_vline(x=30, line_dash="dot", line_color="#C58C69")
        else:
            fig.add_vline(x=10.2, line_dash="dot", line_color="#C58C69")
            fig.add_hline(y=30, line_dash="dot", line_color="#C58C69")
    return finish(fig, 510), plotted

def coverage_chart(df):
    if df.empty:
        return empty_figure("No hay registros en la selección.")
    fig = px.bar(coverage(df), x="count", y="study_label", color="scope_label", orientation="h",
                 labels=LABELS, color_discrete_map=SCOPE_COLORS, text="count")
    fig.update_traces(textposition="auto")
    fig.update_layout(barmode="stack")
    fig.update_yaxes(categoryorder="total ascending")
    return finish(fig, max(340, df.investigation_id.nunique() * 30 + 120))

def category_chart(df, column, limit=15):
    values = df[column].fillna("").replace("", "Sin dato").value_counts().head(limit)
    if values.empty:
        return empty_figure("No hay categorías disponibles.")
    table = values.rename_axis(column).reset_index(name="count")
    fig = px.bar(table, x="count", y=column, orientation="h", text="count", labels=LABELS,
                 color_discrete_sequence=[PALETTE[1]])
    fig.update_yaxes(categoryorder="total ascending")
    return finish(fig, max(340, len(values) * 28 + 80))

def ignition_chart(df):
    tests = df[df.record_scope == "test"]
    if tests.empty:
        return empty_figure("No hay filas de ensayo en esta selección.")
    counts = tests.groupby(["study_label", "ignition_label"]).size().rename("count").reset_index()
    fig = px.bar(counts, x="study_label", y="count", color="ignition_label", text="count",
                 labels=LABELS, color_discrete_map=RESULT_COLORS,
                 category_orders={"ignition_label": ["Éxito", "Fallo", "Sin dato"]})
    return finish(fig)

def completeness_chart(df):
    if df.empty:
        return empty_figure("No hay registros para calcular la cobertura.")
    cols = list(METRICS)
    matrix = df.groupby("investigation_id")[cols].agg(lambda s: 100 * s.notna().mean())
    matrix.columns = [METRICS[c] for c in cols]
    fig = px.imshow(matrix, zmin=0, zmax=100, color_continuous_scale=["#F1F3F1", "#A9C9C7", "#387F89"],
                    aspect="auto", labels=dict(x="Campo", y="Investigación", color="% con dato"), text_auto=".0f")
    fig.update_layout(coloraxis_colorbar=dict(title="% con dato", thickness=10))
    return finish(fig, max(340, len(matrix) * 27 + 190))

def distribution(df, metric, grouping):
    plotted = scalar_records(df, metric, metric)
    if plotted.empty:
        return empty_figure("No hay valores válidos para esta distribución."), plotted
    plotted[grouping] = plotted[grouping].fillna("").replace("", "Sin dato")
    fig = px.box(plotted, x=grouping, y=metric, color="scope_label", points="all", labels=LABELS,
                 color_discrete_map=SCOPE_COLORS, hover_data=["record_id", "test_id"])
    return finish(fig, 480), plotted
