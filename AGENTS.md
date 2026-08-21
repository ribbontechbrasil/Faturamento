# Faturamento (RibbonTech)

Python data-processing project that turns the exported Excel spreadsheets in the
repo root into a cost/profit report (`Relatorio_Custo_Faturamento_RBT.xlsx`) and a
self-contained interactive HTML dashboard (`Dashboard_Custo_Faturamento_RBT.html`).
There is no long-running service — everything runs as one-shot CLI scripts in
`scripts/`.

## Cursor Cloud specific instructions

- Dependencies are just `pandas`, `openpyxl`, `xlrd` (see `requirements.txt`). The
  startup update script installs them at user level with
  `pip3 install --user --break-system-packages -r requirements.txt`, so plain
  `python3` works with no virtualenv to activate. (The `--break-system-packages`
  flag is required because the base image is Ubuntu with a PEP 668
  externally-managed Python.)
- Run the scripts from the repository root, not from `scripts/`. Their CLI
  defaults point at the input spreadsheets by bare filename (e.g.
  `Faturamento_RBT (2).xlsx`), which are only resolved relative to the current
  working directory.
- Pipeline order: `python3 scripts/processar_despesas.py` (writes
  `Despesas_RBT_Normalizadas.xlsx`), then `python3 scripts/gerar_relatorio_custo.py`
  (writes the report **and** the dashboard HTML in one step).
  `python3 scripts/gerar_dashboard_html.py` regenerates only the dashboard from an
  existing report.
- Tests: `test_parser_etiqueta.py` does a bare `import gerar_relatorio_custo`, so
  it must be run from inside `scripts/`: `cd scripts && python3 test_parser_etiqueta.py`.
  It prints `OK: todos os testes passaram` on success.
- The generated outputs (`Relatorio_Custo_Faturamento_RBT.xlsx`,
  `Despesas_RBT_Normalizadas.xlsx`, `Dashboard_Custo_Faturamento_RBT.html`) are
  committed to git. Re-running the pipeline rewrites the `.xlsx` files with new
  internal metadata even when the data is unchanged, so they show up as modified;
  `git checkout --` them unless you intentionally mean to refresh the outputs.
- To view the dashboard, open `file:///workspace/Dashboard_Custo_Faturamento_RBT.html`
  in a browser — it is fully self-contained (data + JS embedded), no server needed.
