#!/usr/bin/env python3
"""NF 1163: etiquetas adesivas 50x40 mm com custo unitário R$ 18,90 / rolo."""

from pathlib import Path

from gerar_relatorio_custo import (
    detalhe_from_planilha,
    load_planilha_etiquetas,
    match_planilha_etiqueta,
    norm_nf,
)

ROOT = Path(__file__).resolve().parents[1]
PLANILHA = ROOT / "Planilha_calculo_custo_etiquetas_jul26.xlsx"
ALT_PLANILHA = ROOT / "Planilha para cálculo de custo de etiquetas - jul 26.xlsx"

DESC = "ETIQUETAS ADESIVAS 50 x 40mm x 2 COLUNAS – ROLO COM 2.000 – TUBETE 1"
QTD_NF = 270_000.0  # etiquetas na NF
QTD_ROLOS = 135.0
CUSTO_ROLO = 18.90
ETIQUETAS_POR_ROLO = 2000.0


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def _planilha():
    path = PLANILHA if PLANILHA.exists() else ALT_PLANILHA
    assert path.exists(), f"planilha de etiquetas não encontrada: {path}"
    planilha = load_planilha_etiquetas(path)
    assert not planilha.empty
    return planilha


def test_nf_1163_custo_unitario_18_90():
    planilha = _planilha()
    row = match_planilha_etiqueta(planilha, norm_nf("RT001163"), QTD_NF, DESC)
    assert row is not None, "sem match para NF 1163 50x40"
    d = detalhe_from_planilha(row)
    assert d.get("fonte") == "planilha_custo_final"
    assert d.get("custo_inclui_frete_imposto")
    assert approx(float(d["custo_rolo"]), CUSTO_ROLO), (d["custo_rolo"], CUSTO_ROLO)
    assert approx(float(d["qtd_tubetes"]), QTD_ROLOS), d["qtd_tubetes"]
    assert approx(float(d["nr_etiquetas_rolo"]), ETIQUETAS_POR_ROLO, tol=0.51), d[
        "nr_etiquetas_rolo"
    ]
    # Custo antigo (~9,65 / rolo, 930 etiq/rolo) não pode voltar
    assert not approx(float(d["custo_rolo"]), 9.6482, tol=0.05)
    total = float(d["custo_total_planilha"])
    assert approx(total, CUSTO_ROLO * QTD_ROLOS, tol=0.5), total


if __name__ == "__main__":
    test_nf_1163_custo_unitario_18_90()
    print("OK: NF 1163 · 50x40 · custo unitário R$ 18,90 / rolo")
