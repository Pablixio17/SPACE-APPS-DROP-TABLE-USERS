# 🚀 Flame in Freefall

## Description

Flame in Freefall is a Streamlit research dashboard for exploring NASA Physical Sciences Informatics (PSI) combustion experiments in microgravity and spaceflight contexts. It helps researchers filter curated experimental records, compare conditions, inspect data quality and provenance, and build an evidence-based synthesis around a research question.

The interface combines a filterable record explorer with an AI-generated dashboard. Depending on the available evidence, that dashboard can include key metrics, charts, comparison tables, safety alerts, research summaries, and engineering recommendations. Charts are rendered from the selected dataset, and the AI is instructed to ground its claims in the supplied evidence.

## Instructions

### Requirements

- Python 3.11 or later.
- A dependency manager of your choice. This README will procede using uv dependency manager (will be installed inside a virtual environment).
- The curated CSV expected at `data/Done DATA f_project/CSV DE LOS DATOS PERFECTAMENTE ORDENADOS.csv`.
- Optional documentary package at `data/Done DATA f_project/PROJECT_MASTER_PACKAGE.zip`. Without it, the dashboard can still load the CSV, but linked documentary context is unavailable.
- A Gemini API key to generate AI dashboards. Record filtering and data inspection can be used without a key.

### Install and run

If using linux to run the app you can use the Makefile in the following way:

```bash
make
```
The Makefile also has the following rules:

- make all -> Rule run when using the command "make", runs make install and make run
- make install -> Installs dependencies for project
- make run -> Runs the program
- make clean -> Deletes compilation and temporal files

If you want to install and run the project manually run these commands from the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install uv
.venv/bin/uv sync
.venv/bin/python3 -m streamlit run src/app.py
```

### On Windows PowerShell:

To run the Makefile commands on Windows (such as `make run`), you need to install **GNU Make** beforehand and ensure you are using a compatible terminal.

#### 1. Install GNU Make

1. Open **PowerShell** or **Windows Terminal** as **Administrator**.
2. Run the following command to install `make` via the official Windows package manager:
   winget install GnuWin32.Make
3. Add the installation path to the system environment variables (`PATH`) by running:
   $oldPath = [Environment]::GetEnvironmentVariable("Path", "Machine"); if ($oldPath -notlike "*GnuWin32\bin*") { [Environment]::SetEnvironmentVariable("Path", "$oldPath;C:\Program Files (x86)\GnuWin32\bin", "Machine") }
4. **Restart your terminal** (and your code editor if open) for the changes to take effect.

#### 2. Verify Installation

Open a new terminal and check that the command is recognized:
   make --version

#### 3. Run the Project

Navigate to the root directory of the project and run the target rule:
   make run

Note for Windows users: If the Makefile uses Unix/Linux-style internal commands (such as `uname`, `rm`, or `/` paths), run `make run` from **Git Bash** (included when installing Git for Windows) instead of PowerShell or CMD to avoid syntax errors.


The `openai` package is included in the install command because the current `app.py` imports its `APIError` class. The dashboard's generative model is Gemini, provided by the `google-genai` project dependency.

### Configure Gemini

Set `GEMINI_API_KEY` as an environment variable, add it to Streamlit secrets in `.streamlit/secrets.toml`, or enter it in the app's sidebar when prompted. For Streamlit secrets, use:

```toml
GEMINI_API_KEY = "your-key-here"
```

Keep API keys private and do not commit them to the repository.

### Use the dashboard

Choose a research perspective and apply filters in the sidebar. Enter a question in the prompt area and select **Generate AI Dashboard**. The generated dashboard is shown below the prompt. Use the audit section to inspect filtered source rows or download the selection as CSV.

## Understanding the data with natural-language questions

The dashboard lets researchers explore the filtered evidence by asking a question in ordinary language instead of writing queries or chart code. First narrow the records with the sidebar filters, then describe the comparison or explanation you need in the prompt. For example:

- “Compare ignition outcomes across oxygen ranges and fuel classes.”
- “Summarize what these studies say about flame behavior in microgravity, and identify evidence gaps.”
- “Which variables can help compare the selected materials, and what limitations should I keep in mind?”

The model uses the prompt together with a compact summary of the active selection to assemble a dashboard with relevant metrics, charts, comparison tables, warnings, and explanatory text. The filters determine which records and summaries are included. Generated charts use available columns and the selected records; the model is instructed not to invent experimental measurements or conditions. Review conclusions against the source records and linked reports, especially when the selection contains study summaries, incomplete measurements, or quality flags.

This version uses Gemini (`gemini-3.5-flash-lite`), configured in `aigen/app.py`; the interface does not currently offer a provider or model selector. A Gemini API key is required to generate a response.

## Resources

### Topic and technical references

- [NASA Physical Sciences Informatics (PSI)](https://psi.nasa.gov/) — research data related to physical sciences in space, including the combustion records explored by this project.
- [NASA Technical Reports Server (NTRS)](https://ntrs.nasa.gov/) — NASA technical publications and research reports.
- [Streamlit documentation](https://docs.streamlit.io/) — app components, configuration, and deployment.
- [pandas documentation](https://pandas.pydata.org/docs/) — tabular data loading, filtering, and analysis.
- [Plotly Express documentation](https://plotly.com/python/plotly-express/) — charts built from the filtered experimental data.
- [Gemini API documentation](https://ai.google.dev/gemini-api/docs) — model access and structured outputs.

### AI use in this project

At runtime, the app uses the `gemini-3.5-flash-lite` model and sends it a compact JSON payload assembled in `aigen/aigen.py`. It contains the user's goal and active filters, record counts, numeric summaries, categorical distributions, study-level summaries, available plotting columns, and linked documentary context when present.

Gemini returns a response validated against the Pydantic schema in `aigen/response.py`. The app renders those blocks in `aigen/app.py` as KPIs, Plotly chart specifications, comparison tables, warnings, explanatory text, and engineering recommendations. Plotly uses the actual filtered records for chart data; Gemini selects valid columns and describes the evidence rather than creating experimental measurements. The model instructions prohibit inventing metrics, conditions, or outcomes, but generated interpretations should still be checked against the source records and reports.

The repository files describe this runtime use of AI; they do not establish whether AI tools were used to author the source code.
