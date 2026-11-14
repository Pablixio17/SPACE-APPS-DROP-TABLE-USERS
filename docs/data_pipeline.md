# Pipeline de datos de Flame in Freefall

## Preparación

Instala las dependencias y ejecuta el pipeline desde la raíz:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/prepare_data.py
python3 scripts/prepare_data.py --fuel propane
```

El pipeline recorre `data/raw/` y crea `data/processed/experiments.csv`. Con `--fuel` también escribe una vista filtrada. No modifica los CSV de origen. La copia redundante de valores originales en JSON no se guarda: cada fila se puede recuperar con `source_file` y `source_row`.

## Tabla maestra

Cada registro contiene los campos normalizados disponibles, identificador de investigación, fichero y fila de origen, tipo de granularidad, referencias a PDF e inferencias de dominio. Entre los campos comparables están `fuel`, `oxygen_fraction`, `pressure_kpa`, `fuel_flow_mg_s`, `airflow_cm_s`, `droplet_initial_diameter_mm`, `burn_time_s` y `duration_s`. Las columnas que no aplican o no se pueden deducir quedan vacías.

Los campos de oxígeno se normalizan como fracción molar. Los porcentajes se convierten dividiendo entre 100. La presión se convierte a kPa únicamente cuando la unidad está identificada. Los valores originales y cabeceras se recuperan desde el CSV apuntado por `source_file`; `source_row` es el número de registro CSV lógico, contando la cabecera como registro 1.

Las filas de PSI-10 y PSI-159 se apilan con su campo `flame_type`. PSI-108 tiene dos exportaciones con las mismas observaciones: se conserva la primera para evitar duplicar pruebas. No se encontraron series temporales por segundo; el pipeline conserva el nivel de detalle de cada fila y no agrega resúmenes con ensayos.

## Filtrado para el dashboard

```python
from scripts.prepare_data import build_master, filter_for_dashboard

master = build_master()
filtered, chart_columns, pdf_paths = filter_for_dashboard(master, fuel="propane")
```

La función devuelve el dataframe filtrado, las columnas numéricas ordenadas por completitud para ese filtro y las rutas PDF únicas relacionadas con las investigaciones resultantes. Los alias de combustible como `C3H8` y `propano` se reconocen como `propane`.

## Historial de datos y PDFs

`docs/historial_datos/PSI-XXX.md` contiene la documentación de normalización por estudio: fuentes, cabeceras de origen reconocidas, campos canónicos, conversiones y excepciones. El pipeline crea estos documentos si faltan y no sobrescribe ediciones existentes. Los PDF se indexan en `data/processed/pdf_catalog.json` y también se asocian a cada fila de su investigación en `reference_pdf_path`. No se extrae texto de los PDF.
