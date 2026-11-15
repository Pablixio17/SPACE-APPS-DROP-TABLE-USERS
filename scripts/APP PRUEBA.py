"""Flame in Freefall. Run: python -m streamlit run "scripts/APP PRUEBA.py"."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
import re
from pathlib import Path
import sqlite3
import sys
import zipfile

import pandas as pd
import streamlit as st

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from flame_data import (
    CSV_PATH, PACKAGE_PATH, INSIGHTS, METRICS, archive_records, evidence_page,
    filter_records, interpret_request, label, load_metadata, load_records,
    prepare_database, record_differences, search_evidence, signature,
)
from flame_charts import category_chart, completeness_chart, coverage_chart, distribution, ignition_chart, scatter

st.set_page_config(page_title="Flame in Freefall · Evidence Studio", page_icon="◌", layout="wide")
st.markdown("<style>" + SCRIPT_DIR.joinpath("flame_style.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def cached_metadata(package_signature):
    database = prepare_database(Path(package_signature[0]))
    projects, fields = load_metadata(database)
    return database, projects, fields


@st.cache_data(show_spinner=False)
def cached_records(csv_signature, fields):
    return load_records(Path(csv_signature[0]), fields)


@st.cache_data(show_spinner=False)
def cached_search(database, package_signature, query, project):
    return search_evidence(database, query, project)


def tags(items):
    st.markdown('<div class="tags">' + "".join('<span class="tag">' + escape(str(x)) + '</span>' for x in items) + '</div>', unsafe_allow_html=True)


def insight(text, heading="Lectura de la evidencia"):
    st.markdown(f'<div class="insight"><div class="kicker">{escape(heading)}</div><p>{escape(text)}</p></div>', unsafe_allow_html=True)


def chart(fig, key):
    st.plotly_chart(fig, width="stretch", theme=None, key=key,
                    config={"displaylogo": False, "toImageButtonOptions": {"format": "png", "scale": 2}})


def table(df, **kwargs):
    st.dataframe(df, width="stretch", hide_index=True, column_config={c: label(c) for c in df.columns}, **kwargs)


def sidebar(df):
    categories, numeric = {}, {}
    with st.sidebar:
        st.markdown('<div class="sidebar-title">Tu espacio de análisis</div>', unsafe_allow_html=True)
        st.caption("Combina filtros. Las vistas y exportaciones siguen tu selección.")
        if st.button("Restablecer filtros", width="stretch"):
            for key in list(st.session_state):
                if key.startswith("filter_"):
                    del st.session_state[key]
            st.rerun()
        profile = st.selectbox("Perspectiva", ["Exploración general", "Seguridad aeroespacial", "Aprendizaje", "Investigación CFD"], key="filter_profile")
        text = st.text_input("Buscar en los registros", placeholder="PSI-159, Kapton, ethylene…", key="filter_text")
        names = df.groupby("investigation_id").acronym.first().to_dict()
        categories["investigation_id"] = st.multiselect("Investigaciones", sorted(names, key=lambda s: int(s.split('-')[1])), format_func=lambda s: s + " · " + names[s], key="filter_studies")
        categories["record_scope"] = st.multiselect("Tipo de registro", list(df.record_scope.unique()), format_func=label, key="filter_scope")
        with st.expander("Materia, llama y equipo"):
            for column in ["fuel_class", "fuel", "material_category", "material", "flame_type", "visual_phenomena", "hardware", "flow_regime"]:
                options = sorted(v for v in df[column].dropna().unique() if v and v != "-")
                categories[column] = st.multiselect(label(column), options, format_func=label, key="filter_" + column)
        with st.expander("Contexto y calidad"):
            for column in ["safety_pillar", "gravity_regime", "study_environment", "quality_label", "ignition_label", "traffic_light"]:
                categories[column] = st.multiselect(label(column), sorted(df[column].unique()), format_func=label, key="filter_" + column)
        with st.expander("Condiciones atmosféricas"):
            lunar = st.checkbox("Escenario lunar de referencia", key="filter_lunar", help="P ≤ 10,2 psia y O₂ ≥ 30 %. No representa una medición de gravedad lunar.")
            range_on = st.checkbox("Acotar presión y oxígeno", key="filter_ranges")
            keep_missing = True
            if range_on:
                for column in ["oxygen_pct", "pressure_psi"]:
                    valid = df[column].dropna()
                    low, high = float(valid.min()), float(valid.max())
                    if low < high:
                        numeric[column] = st.slider(label(column), low, high, (low, high), key="filter_" + column)
                keep_missing = st.checkbox("Conservar registros sin estas medidas", value=True, key="filter_missing")
        st.divider()
        st.caption("FUENTE CURADA")
        st.markdown("**Done DATA f_project**")
        st.caption("Valores originales conservados · contexto documental enlazado · análisis local")
    return filter_records(df, categories, text, lunar, numeric, keep_missing), profile


def panorama(df, projects):
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        st.subheader("Un mapa de la evidencia")
        st.caption("Volumen por estudio: ensayos, observaciones y resúmenes separados.")
        chart(coverage_chart(df), "overview_coverage")
    with right:
        st.subheader("Preguntas que puedes explorar")
        insight("Relaciona oxígeno y presión; compara materiales y ventilación; consulta resultados de ignición y vuelve a la página que sustenta cada conclusión.", "De la pregunta al registro")
        chart(category_chart(df, "pillar_label", 8), "overview_pillars")
    st.subheader("Lecturas para tu selección")
    relevant = [p for p in projects if p["investigation_id"] in set(df.investigation_id)]
    for p in relevant[:3]:
        insight(INSIGHTS.get(p["investigation_id"], p["conclusion"]), p["investigation_id"] + " · " + p["name"])
    if len(relevant) > 3:
        st.caption(f"Hay {len(relevant)} estudios en la selección. Abre Estudios para consultar todas sus conclusiones, límites y citas.")


def laboratory(df, profile):
    st.subheader("Diseña tu propia lectura")
    st.caption("Consultas guiadas locales: reconoce estudios, familias, combustibles y temas. Revisa los criterios interpretados.")
    query = st.text_input("¿Qué quieres explorar?", placeholder="Compara BASS · Ignición de PSI-159 · Presión y oxígeno lunar", key="analysis_query")
    local, suggested, notes = interpret_request(query, df) if query.strip() else (df, "Atmósfera", [])
    if query.strip():
        tags(notes)
        st.caption(f"Consulta dentro de tus filtros: {len(local):,} registros.")
    mode = st.selectbox("Vista", ["Automática", "Atmósfera", "Comparación", "Materiales", "Ignición", "Calidad", "Distribución"], key="analysis_view")
    mode = suggested if mode == "Automática" else mode
    if mode == "Atmósfera":
        c1, c2, c3 = st.columns(3)
        x = c1.selectbox("Eje horizontal", list(METRICS), format_func=label, key="axis_x")
        y = c2.selectbox("Eje vertical", list(METRICS), index=1, format_func=label, key="axis_y")
        color = c3.selectbox("Color por", ["investigation_id", "fuel_class", "fuel", "flame_type", "quality_label", "ignition_label"], format_func=label)
        a, b = st.columns(2)
        annotations = a.checkbox("Etiquetar puntos con el ID del ensayo")
        references = b.checkbox("Mostrar referencias atmosféricas", value=True)
        fig, plotted = scatter(local, x, y, color, annotations, references)
        chart(fig, "custom_scatter")
        st.caption(f"{len(plotted):,} puntos con valores válidos de {len(local):,} registros. Se omiten resúmenes y pares incompletos; los rangos no se convierten en puntos.")
        if x == "irl_score" or y == "irl_score":
            st.info("El IRL es una puntuación heredada, no una probabilidad de incendio ni una certificación de seguridad.")
        if profile == "Aprendizaje":
            insight("Cada punto es una fila con dos valores escalares. El símbolo distingue ensayos de observaciones. Un punto ausente puede indicar que falta una medida.", "Cómo leer el gráfico")
        elif profile == "Investigación CFD":
            insight("Inspecciona la procedencia por campo antes de usar una condición de contorno. Las medidas corregidas o inferidas mantienen sus etiquetas en Calidad y en el detalle del registro.", "Para comparar modelos")
        elif profile == "Seguridad aeroespacial":
            insight("Comprueba material, ventilación y alcance del estudio antes de trasladar un resultado a un hábitat. Los escenarios atmosféricos de referencia no certifican seguridad ni gravedad parcial.", "Alcance operacional")
    elif mode == "Comparación": chart(coverage_chart(local), "custom_coverage")
    elif mode == "Materiales":
        chart(category_chart(local[local.fuel_class == "solid"], "material"), "custom_materials")
        st.caption("Hasta 15 descripciones de probeta. Frecuencia de registros, no clasificación de riesgo.")
    elif mode == "Ignición":
        chart(ignition_chart(local), "custom_ignition")
        st.caption("Solo filas de ensayo. Éxito de ignición no equivale a presencia de llama fría.")
    elif mode == "Calidad": chart(completeness_chart(local), "custom_completeness")
    else:
        a, b = st.columns(2)
        metric = a.selectbox("Variable", list(METRICS), format_func=label)
        grouping = b.selectbox("Agrupar por", ["investigation_id", "fuel", "fuel_class", "flame_type"], format_func=label)
        fig, plotted = distribution(local, metric, grouping)
        chart(fig, "custom_distribution")
        st.caption(f"{len(plotted)} registros válidos. Las observaciones se muestran separadas; no se presupone independencia estadística.")


def materials(df):
    st.subheader("Materiales, flujo y comportamiento")
    solids = df[df.fuel_class == "solid"]
    tags([f"{len(solids)} registros de sólidos", f"{solids.investigation_id.nunique()} estudios", "Descripciones de probeta preservadas"])
    a, b = st.columns([1.1, 1])
    with a:
        chart(category_chart(solids, "material"), "materials_counts")
        st.caption("Las 15 descripciones más frecuentes. El CSV conserva todas las probetas.")
    with b:
        insight("Las descripciones incluyen geometría y dimensiones. La frecuencia de un material no mide su inflamabilidad. Consulta BASS para interpretar la dirección del flujo.")
        chart(category_chart(solids, "visual_phenomena"), "materials_phenomena")
    table(solids[["investigation_id", "record_scope", "material", "airflow_cm_s", "burn_time_s", "visual_phenomena", "data_quality_flags"]], height=280)


def ignition(df):
    st.subheader("Qué registra realmente la ignición")
    tests = df[df.record_scope == "test"]
    counts = tests.ignition_label.value_counts()
    for col, name in zip(st.columns(3), ["Éxito", "Fallo", "Sin dato"]):
        col.metric(name, f"{counts.get(name, 0):,}")
    chart(ignition_chart(df), "ignition_results")
    insight("Un dato ausente no se contabiliza como fallo y un encendido exitoso no demuestra una llama fría. Los resultados proceden del campo de ignición de las filas de ensayo.", "Interpretación")
    known = tests[tests.ignition_label != "Sin dato"]
    if not known.empty:
        table(known.groupby(["investigation_id", "fuel", "ignition_label"]).size().rename("count").reset_index())


def study_library(df, projects, database, raw):
    st.subheader("Estudios interpretados, fuentes a un clic")
    if not projects:
        st.info("Añade PROJECT_MASTER_PACKAGE.zip para consultar la biblioteca documental.")
        return
    st.caption("Biblioteca completa del paquete. Las conclusiones describen el estudio completo; el contador de selección refleja tus filtros.")
    by_id = {p["investigation_id"]: p for p in projects}
    pid = st.selectbox("Ficha de investigación", list(by_id), format_func=lambda v: v + " · " + by_id[v]["name"], key="study_detail")
    p = by_id[pid]
    a, b, c = st.columns(3)
    a.metric("Registros curados del estudio", p["curated_records"])
    b.metric("Dentro de tus filtros", int(df.investigation_id.eq(pid).sum()))
    c.metric("Documentos directos", p["direct_documents"])
    tags([label(p["conclusion_type"])] + [f"{label(k)}: {v}" for k, v in p["curated_scope_counts"].items()])
    insight(INSIGHTS.get(pid, p["conclusion"]), "Síntesis en español · alcance del paquete")
    with st.expander("Conclusión y límites originales"):
        st.write(p["conclusion"])
        st.write(p["limitations"])
    if p["citations"]:
        st.markdown("**Páginas que sustentan esta lectura**")
        for citation in p["citations"]:
            for url in citation["source_urls"][:1]:
                st.markdown(f'[{citation["doc_id"]} · página {citation["page"]}]({url})')
        cite = st.selectbox("Leer página citada", p["citations"], format_func=lambda v: f'{v["doc_id"]} · p. {v["page"]}')
        with st.expander("Texto extraído de la página"):
            page = evidence_page(database, cite["page_id"])
            st.text(page.get("text", "Texto no disponible."))
            st.caption("La extracción puede omitir información de figuras o manuscritos. El PDF conserva la referencia visual.")
    else:
        st.info("Esta lectura se basa en las filas del dataset. El paquete no aporta páginas directas para afirmar un resultado científico general de este estudio.")
    with st.expander("Citar la investigación · APA, IEEE o BibTeX"):
        style = st.selectbox("Formato de referencia", ["APA", "IEEE", "BibTeX"])
        url = "https://psi.nasa.gov/physci/repo/data/investigations/" + pid
        title = pid + ": " + p["name"]
        if style == "APA":
            citation_text = f"NASA Physical Sciences Informatics. (s. f.). {title} [Investigación y datos]. {url}"
        elif style == "IEEE":
            citation_text = f'NASA Physical Sciences Informatics, "{title}," [En línea]. Disponible: {url}'
        else:
            citation_text = f"@misc{{nasa_{pid.lower().replace('-', '_')},\n  author = {{NASA Physical Sciences Informatics}},\n  title = {{{title}}},\n  url = {{{url}}}\n}}"
        st.code(citation_text, language="bibtex" if style == "BibTeX" else "text")
        st.caption("Referencia a la ficha PSI sin inventar fecha ni DOI del dataset. Los DOI de publicaciones se conservan separados.")
        dois = sorted(set(re.findall(r"10\.\d{4,9}/[^\s|;]+", " ".join(raw.loc[raw.investigation_id == pid, "doi"]))))
        for doi in dois:
            st.markdown(f"[DOI de publicación conservado: {doi}](https://doi.org/{doi})")
    exported = {**p, "sintesis_es": INSIGHTS.get(pid, p["conclusion"])}
    st.download_button("Descargar ficha y citas · JSON", json.dumps(exported, ensure_ascii=False, indent=2).encode("utf-8"), file_name=f"{pid}_evidencia.json", mime="application/json")
    if p["archive_only_records"]:
        with st.expander(f'Archivo histórico separado · {p["archive_only_records"]} registros adicionales'):
            st.caption("No intervienen en los indicadores ni en las gráficas del CSV curado.")
            records = archive_records(database, pid)
            table(pd.DataFrame(records)[["record_id", "investigation_id", "record_scope"]])
            st.download_button("Descargar archivo histórico · JSON", json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8"), file_name=f"{pid}_historico.json", mime="application/json")


def evidence(projects, database, package_sig):
    st.subheader("Busca en la documentación")
    st.caption("Busca términos originales, normalmente en inglés. Los resultados son contexto documental, no emparejamientos validados con cada ensayo.")
    if database is None:
        st.info("La búsqueda documental requiere PROJECT_MASTER_PACKAGE.zip.")
        return
    with st.form("evidence_search"):
        a, b = st.columns([2, 1])
        query = a.text_input("Palabras en el documento", value="cool flames")
        project_id = b.selectbox("Ámbito documental", ["Todos"] + [p["investigation_id"] for p in projects])
        submitted = st.form_submit_button("Buscar evidencia", type="primary")
    if submitted:
        project = next((p for p in projects if p["investigation_id"] == project_id), None)
        st.session_state["evidence_results"] = cached_search(database, package_sig, query, project)
        st.session_state["evidence_search_label"] = f"{query} · {project_id}"
    results = st.session_state.get("evidence_results")
    if results is None:
        insight("Prueba “radiative extinction”, “cool flames” o “smoke”. Cada fragmento conserva documento, página física y enlace a la fuente.", "Búsqueda en el paquete documental")
    else:
        st.caption(f'Búsqueda: {st.session_state.get("evidence_search_label", "")} · {len(results)} fragmentos (máximo 8).')
        if not results:
            st.info("No hay coincidencias. Prueba menos palabras o un estudio con documentos disponibles.")
        for index, result in enumerate(results):
            citation = json.loads(result["citation_json"])
            with st.expander(f'{result["doc_id"]} · página {result["page_number"]} · fragmento {index + 1}', expanded=index == 0):
                st.text(result["text"])
                for url in citation.get("source_urls", [])[:1]:
                    st.markdown(f"[Abrir PDF en la página citada]({url})")
                st.caption("Extracción: " + result["method"] + " · Incidencias: " + result["quality_flags_json"])


def html_report(raw, df, profile, projects):
    sections = []
    for p in projects:
        if p["investigation_id"] not in set(df.investigation_id):
            continue
        links = " ".join(f'<a href="{escape(c["source_urls"][0], quote=True)}">{escape(c["doc_id"])} · p. {c["page"]}</a>' for c in p["citations"] if c["source_urls"])
        sections.append(f'<h2>{escape(p["investigation_id"] + " · " + p["name"])}</h2><p>{escape(INSIGHTS.get(p["investigation_id"], p["conclusion"]))}</p><p>{escape(p["limitations"])}</p>{links}')
    counts = df.record_scope.value_counts().rename_axis("Tipo").reset_index(name="Filas")
    return ('<!doctype html><html lang="es"><meta charset="utf-8"><title>Flame in Freefall · Informe</title>'
            '<style>body{font:16px system-ui;color:#203743;max-width:1000px;margin:50px auto;padding:20px}h1{font-size:38px}h2{margin-top:32px}td,th{padding:8px;text-align:left}a{color:#387f89}</style><body>'
            + f'<h1>Flame in Freefall</h1><p>{escape(profile)} · {datetime.now(timezone.utc).isoformat()}</p><p>Fuente: {escape(CSV_PATH.name)}. Selección: {len(df)} registros. Tipos de fila, no experimentos independientes.</p>'
            + counts.to_html(index=False, escape=True)
            + '<p>IRL y semáforos son clasificaciones heredadas. El escenario atmosférico lunar no valida seguridad ni gravedad lunar. Las conclusiones siguientes se refieren a estudios completos.</p>'
            + ''.join(sections) + '<h2>Registros de la selección</h2>'
            + raw.loc[df.index, ["record_id", "investigation_id", "record_scope", "test_id", "fuel", "material", "oxygen_pct", "pressure_psi"]].to_html(index=False, escape=True) + '</body></html>')


def data_quality(raw, df, fields, projects, database, profile):
    st.subheader("Calidad visible. Datos trazables.")
    chart(completeness_chart(df), "quality_matrix")
    st.caption("Porcentaje de filas con un valor escalar presente. Presencia no implica medición directa ni validación científica.")
    flags = df.data_quality_flags.str.split(";").explode()
    flags = flags[flags.ne("")].value_counts().rename_axis("Incidencia").reset_index(name="Registros")
    if not flags.empty: table(flags)
    defaults = ["investigation_id", "record_scope", "test_id", "fuel", "material", "oxygen_pct", "pressure_psi", "data_quality_flags"]
    columns = st.multiselect("Columnas visibles · todos los campos originales disponibles", list(raw.columns), default=defaults, format_func=label)
    selected_raw = raw.loc[df.index]
    if columns: table(selected_raw[columns], height=370)
    if not df.empty:
        record_id = st.selectbox("Inspeccionar un registro", df.record_id.tolist())
        row = selected_raw[selected_raw.record_id == record_id].iloc[0]
        with st.expander("Valores completos y procedencia por campo"):
            st.json(row.to_dict(), expanded=False)
            if database is not None:
                st.markdown("**Diferencias con el archivo anterior**")
                differences = record_differences(database, record_id)
                if differences: table(pd.DataFrame(differences))
                else: st.caption("Sin diferencias registradas para este identificador.")
    c1, c2 = st.columns(2)
    c1.download_button("Descargar selección · CSV original", selected_raw.to_csv(index=False).encode("utf-8-sig"), file_name="flame_seleccion_curada.csv", mime="text/csv", width="stretch")
    c2.download_button("Descargar informe con fuentes · HTML", html_report(raw, df, profile, projects).encode("utf-8"), file_name="flame_informe.html", mime="text/html", width="stretch")
    with st.expander(f"Diccionario de etiquetas · {len(raw.columns)} campos originales"):
        dictionary = pd.DataFrame(fields) if fields else pd.DataFrame({"field": raw.columns})
        dictionary.insert(1, "Etiqueta", dictionary.field.map(label))
        table(dictionary)
    st.caption("El CSV exporta los valores originales y todas las columnas, independientemente de las columnas visibles. El archivo histórico se mantiene separado.")


def main():
    database, projects, fields = None, [], []
    package_sig = signature(PACKAGE_PATH)
    package_error = None
    try:
        if PACKAGE_PATH.exists():
            with st.spinner("Preparando el índice documental…"):
                database, projects, fields = cached_metadata(package_sig)
        else:
            package_error = "No se encuentra PROJECT_MASTER_PACKAGE.zip. Las vistas del CSV siguen disponibles."
        raw, df = cached_records(signature(CSV_PATH), fields)
    except (FileNotFoundError, ValueError, OSError, zipfile.BadZipFile, sqlite3.DatabaseError, KeyError) as exc:
        st.error("No se puede cargar la fuente solicitada: " + str(exc))
        st.caption("Revisa data/Done DATA f_project. La aplicación no sustituye los datos por ejemplos.")
        st.stop()
    selected, profile = sidebar(df)
    st.markdown('<div class="masthead"><div class="brand"><span class="brand-mark">◌</span>FLAME IN FREEFALL</div><div class="edition">NASA PSI data / Evidence Studio</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="hero"><div class="eyebrow">Combustión · Microgravedad · Evidencia</div><h1>Explora el fuego.<br>Entiende <em>la evidencia.</em></h1><p>Un espacio para conectar condiciones experimentales, materiales y conocimiento. De cada gráfica a su registro. De cada conclusión a su fuente.</p></div>', unsafe_allow_html=True)
    tags([f"{len(df):,} registros curados", f"{df.investigation_id.nunique()} estudios con datos", f"{len(projects)} proyectos documentados", f"{len(raw.columns)} campos", profile])
    if package_error: st.warning(package_error)
    cols = st.columns(4)
    cols[0].metric("Registros en tu selección", f"{len(selected):,}")
    cols[1].metric("Filas de ensayo", f"{selected.record_scope.eq('test').sum():,}")
    cols[2].metric("Observaciones", f"{selected.record_scope.eq('test_observation').sum():,}")
    cols[3].metric("Resúmenes de estudio", f"{selected.record_scope.eq('study_summary').sum():,}")
    if selected.empty: st.info("No hay registros con estos filtros. Puedes restablecerlos o consultar la biblioteca documental.")
    st.markdown('<div class="note">Las condiciones atmosféricas, los rangos de estudio y los contextos gravitatorios son evidencias distintas. IRL y semáforos son etiquetas de origen, no certificaciones de seguridad.</div>', unsafe_allow_html=True)
    tabs = st.tabs(["Panorama", "Laboratorio", "Materiales", "Ignición", "Estudios", "Evidencia", "Datos y calidad"])
    with tabs[0]: panorama(selected, projects)
    with tabs[1]: laboratory(selected, profile)
    with tabs[2]: materials(selected)
    with tabs[3]: ignition(selected)
    with tabs[4]: study_library(selected, projects, database, raw)
    with tabs[5]: evidence(projects, database, package_sig)
    with tabs[6]: data_quality(raw, selected, fields, projects, database, profile)
    st.markdown('<div class="footer">FLAME IN FREEFALL &nbsp; / &nbsp; Fuentes locales · Valores curados preservados · Interpretación con trazabilidad</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
