# CSV configurado: Flame in Freefall

Abra experiments_configurado.csv con UTF-8, separador coma y decimal punto. NaN representa dato ausente. El original no se modifica.

## Uso

tests_maestra.csv tiene una fila por ensayo. experiments_configurado.csv es el detalle completo: record_scope=test para registros unicos, test_observation para multiples observaciones del mismo ensayo, study_summary para descripciones y empty_source_row para filas vacias retenidas. Ambas tablas se vinculan por test_uid. Las medias agregadas son aritmeticas, sin ponderacion temporal. Filtrar include_in_safety_ranking=true para ranking de relevancia y ordenar irl_score. Consulte las bases de puntuacion y la granularidad antes de comparar.

## Reglas aplicadas

- Las 2887 filas se conservan. Los valores originales modificados constan en cambios.csv y source_values_json conserva todas las celdas del CSV fuente.
- NaN es el marcador literal de datos ausentes, no aplicables o no deducibles. Rangos y conjuntos no se sustituyen por el primer numero: se guardan limites y numeric_details_json.
- Operadores y errores se conservan en numeric_details_json. El filtro lunar no trata desigualdades ni valores aproximados como mediciones exactas.
- Las 861 filas vacias se retienen y excluyen del ranking; no se les inyectan combustibles ni hardware.
- No se detectaron series temporales en los 21 CSV experimentales inspeccionados: GMT ignition y Flame Off son eventos de inicio/fin, no muestras por segundo.
- Se unieron horizontalmente las dos exportaciones de PSI-108 por Run+Test con validacion uno-a-uno. Las discrepancias quedan en merge_conflicts_json. No se agregan 38 observaciones duplicadas.
- No se unen tablas Normal Flame e Inverse Flame por su pertenencia a una carpeta: son ensayos de configuraciones distintas.
- SPICE se agrupa por dia GMT e instante de ignicion dentro del archivo. Varias filas cambian condiciones dentro de un mismo evento sin tiempos de muestreo: se conservan como test_observation. tests_maestra.csv agrega media aritmetica, minimo y maximo por ensayo, sin ponderacion temporal y sin sumar duraciones. Los duplicados exactos se conservan en el detalle y no se cuentan en las medias.
- ACME usa clase gas y CIR-ACME por contexto; la especie quimica desconocida queda NaN. FLEX/CFI de gotas usan clase liquid. PSI-10 inverso permite inferir ethylene por las columnas XC2H4.
- PSI-23 aporta aproximadamente 1 atm en sus notas; se inyecta como valor aproximado con procedencia. No se rellenan presiones ISS genericas no documentadas.
- PSI-108/181 se excluyen segun instrucciones; PSI-47 se excluye adicionalmente por calibracion con polvo, no combustion.
- IRL es relevancia segun las reglas del usuario, no probabilidad de incendio ni certificacion NASA-STD-6001. No se aplica un aumento universal de inflamabilidad del 40%.
- Sin regla S_seg o S_mat se deja NaN y el IRL incompleto. No se renormalizan los pesos.
- Se usa 10.2 psi como umbral principal en lugar de la aproximacion 0.69 atm. La categoria de cabina estandar admite 14.7 +/-1 psi y 21 +/-1 puntos porcentuales de O2 como decision de clasificacion.
- El contexto gravitacional y las envolventes de estudio no equivalen a mediciones de cada ensayo; no se interpola gravedad sin observaciones emparejadas y modelo.
- Los PDF se indexan por ruta relativa del experimento sin abrir ni extraer contenido. Los DOI se extraen exclusivamente de columnas de referencia de los CSV.
- Las referencias [1]/[2] del documento de instrucciones no estan desarrolladas; las reglas contextuales se identifican como aportadas por el usuario.

## Validacion

- rows: 2887
- columns: 79
- scopes: {"test": 1418, "test_observation": 469, "study_summary": 139, "empty_source_row": 861}
- irl_status: {"incomplete": 1843, "complete": 140, "excluded": 40, "empty_source_row": 861, "invalid_input": 3}
- rankable: 140
- duplicate_rows: 50
- horizontal_merges: 38
- recovered_doi_rows: 8
- source_csvs: 21
- changed_cells_excluding_empty_to_NaN: 16885
- time_series_detected: 0
- pdf_texts_processed: 0
- unique_tests: 1532
- multi_observation_tests: 128

## Campos

| Campo | Uso |
|---|---|
| record_id | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| investigation_id | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| investigation_name | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| experiment_type | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| grain_type | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| source_file | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| source_row | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| test_id | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| test_date | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| flame_type | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| fuel | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| fuel_class | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| material | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| hardware | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| focus | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| oxygen_fraction | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| pressure_kpa | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| fuel_flow_mg_s | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| airflow_cm_s | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| droplet_initial_diameter_mm | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| burn_time_s | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| duration_s | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| ignition_success | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| inference_notes | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| data_history_path | Campo canonico; unidades en el nombre y procedencia en field_provenance_json |
| reference_pdf_path | Rutas relativas separadas por punto y coma; no contiene texto extraido |
| source_encoding | Campo derivado o de clasificacion; reglas en configuracion.json |
| source_values_json | Todas las celdas originales del CSV fuente |
| source_files | Campo derivado o de clasificacion; reglas en configuracion.json |
| merge_status | Campo derivado o de clasificacion; reglas en configuracion.json |
| merge_conflicts_json | Valores discrepantes conservados de ambas exportaciones |
| record_scope | test, test_observation, study_summary o empty_source_row |
| test_uid | Identificador de estudio y ensayo; no usar test_id globalmente |
| duplicate_of_record_id | Registro previo con celdas fuente identicas |
| oxygen_pct | Campo derivado o de clasificacion; reglas en configuracion.json |
| pressure_psi | Campo derivado o de clasificacion; reglas en configuracion.json |
| pressure_atm | Campo derivado o de clasificacion; reglas en configuracion.json |
| oxygen_fraction_min | Limite del rango o conjunto en unidad canonica |
| oxygen_fraction_max | Limite del rango o conjunto en unidad canonica |
| pressure_kpa_min | Limite del rango o conjunto en unidad canonica |
| pressure_kpa_max | Limite del rango o conjunto en unidad canonica |
| droplet_initial_diameter_mm_min | Limite del rango o conjunto en unidad canonica |
| droplet_initial_diameter_mm_max | Limite del rango o conjunto en unidad canonica |
| airflow_cm_s_min | Limite del rango o conjunto en unidad canonica |
| airflow_cm_s_max | Limite del rango o conjunto en unidad canonica |
| is_lunar_atmosphere | Campo derivado o de clasificacion; reglas en configuracion.json |
| is_combustion_core | Campo derivado o de clasificacion; reglas en configuracion.json |
| exclusion_reason | Campo derivado o de clasificacion; reglas en configuracion.json |
| study_environment | Limite de estudio aportado por instrucciones |
| gravity_regime | Campo derivado o de clasificacion; reglas en configuracion.json |
| partial_gravity_emulation | Campo derivado o de clasificacion; reglas en configuracion.json |
| gravity_interpolation_index | NaN hasta disponer de modelo y medidas emparejadas |
| gravity_interpolation_status | Campo derivado o de clasificacion; reglas en configuracion.json |
| safety_pillar | Campo derivado o de clasificacion; reglas en configuracion.json |
| material_category | Campo derivado o de clasificacion; reglas en configuracion.json |
| flow_regime | Campo derivado o de clasificacion; reglas en configuracion.json |
| visual_phenomena | Campo derivado o de clasificacion; reglas en configuracion.json |
| linked_investigation_ids | Campo derivado o de clasificacion; reglas en configuracion.json |
| available_linked_investigation_ids | Campo derivado o de clasificacion; reglas en configuracion.json |
| missing_linked_investigation_ids | Campo derivado o de clasificacion; reglas en configuracion.json |
| doi | DOI extraido del CSV fuente |
| pdf_reference_count | Campo derivado o de clasificacion; reglas en configuracion.json |
| s_atm | Campo derivado o de clasificacion; reglas en configuracion.json |
| s_seg | Campo derivado o de clasificacion; reglas en configuracion.json |
| s_grav | Campo derivado o de clasificacion; reglas en configuracion.json |
| s_mat | Campo derivado o de clasificacion; reglas en configuracion.json |
| irl_score | 0.35 S_atm + 0.30 S_seg + 0.20 S_grav + 0.15 S_mat; NaN si incompleto |
| irl_status | Campo derivado o de clasificacion; reglas en configuracion.json |
| irl_component_coverage | Campo derivado o de clasificacion; reglas en configuracion.json |
| include_in_safety_ranking | Campo derivado o de clasificacion; reglas en configuracion.json |
| scoring_basis_json | Regla usada para cada componente |
| study_pressure_min_atm | Limite de estudio aportado por instrucciones |
| study_pressure_max_atm | Limite de estudio aportado por instrucciones |
| study_oxygen_min_pct | Limite de estudio aportado por instrucciones |
| study_oxygen_max_pct | Limite de estudio aportado por instrucciones |
| data_quality_flags | Campo derivado o de clasificacion; reglas en configuracion.json |
| numeric_details_json | Valor literal, unidad, factor, operador, incertidumbre, limites y estado de cada numero |
| field_provenance_json | Procedencia de los campos canonicos |
| rules_version | Campo derivado o de clasificacion; reglas en configuracion.json |
