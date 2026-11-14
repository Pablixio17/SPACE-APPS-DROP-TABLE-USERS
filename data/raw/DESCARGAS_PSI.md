# Descargas NASA PSI

Fecha: 14 de noviembre de 2026.

Descargados 410 archivos con extensión PDF y 21 tablas experimentales CSV originales, organizados por investigación y categoría en data/raw. Los CSV cubren los 18 PSI solicitados. Se descargaron todos los PDF públicos del inventario vigente de los nueve PSI solicitados, incluidos informes, documentos técnicos, presentaciones y PDF de datos.

| PSI | PDF | CSV experimentales |
|---|---:|---:|
| PSI-115 | 2 | 0 |
| PSI-159 | 93 | 2 |
| PSI-39 | 48 | 1 |
| PSI-26 | 30 | 1 |
| PSI-20 | 59 | 1 |
| PSI-22 | 57 | 1 |
| PSI-23 | 38 | 1 |
| PSI-47 | 7 | 1 |
| PSI-10 | 76 | 2 |
| PSI-108 | 0 | 2 |
| PSI-142 | 0 | 1 |
| PSI-107 | 0 | 1 |
| PSI-102 | 0 | 1 |
| PSI-101 | 0 | 1 |
| PSI-106 | 0 | 1 |
| PSI-21 | 0 | 1 |
| PSI-25 | 0 | 1 |
| PSI-68 | 0 | 1 |
| PSI-69 | 0 | 1 |

## Advertencias de los archivos originales

- PSI-39 — PSI-39_Analyzed Data_FLEX-1248_Summary.pdf: el original descargado no contiene una cabecera PDF válida. Se ha conservado sin modificar.
  Ruta: data\raw\PSI-39\Analyzed Data\PSI-39_Analyzed Data_FLEX-1248_Summary.pdf
- PSI-20 — PSI-20_Engineering Documents_ACME_engineering_20210328.pdf: el catálogo anuncia 5794678 bytes, pero NASA entrega 6843254 bytes. La transferencia coincide con el tamaño de la respuesta y el archivo tiene cabecera PDF válida.
  Ruta: data\raw\PSI-20\Engineering Documents\PSI-20_Engineering Documents_ACME_engineering_20210328.pdf
- PSI-22 — PSI-22_Presentations_Chien et al 2018 Electric-Field Effects on Flames in Microgravity.pdf: el original descargado no contiene una cabecera PDF válida. Se ha conservado sin modificar.
  Ruta: data\raw\PSI-22\Presentations\PSI-22_Presentations_Chien et al 2018 Electric-Field Effects on Flames in Microgravity.pdf

## Verificación y reanudación

Todos los archivos se han guardado y se ha comprobado su tamaño local. El inventario psi_download_manifest.csv incluye versiones, tamaño anunciado y descargado, estado, ruta local, URL de origen y SHA-256. psi_requested_manifest.json conserva la misma selección para reanudar mediante el script download_psi_requested.mjs con Node.js. El script original download_psi.py y manifest.csv se han conservado.
