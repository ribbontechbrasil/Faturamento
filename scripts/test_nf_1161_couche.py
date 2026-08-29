#!/usr/bin/env python3
"""NF 1161: couche 100x70 rolo com 554 / tubete 1" usa Custo Final R$ 795,13."""

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

DESC_554 = 'ETIQUETA COUCHE 100X70 ROLO COM 554 TUBETE 1" COM SERRILHA'
DESC_1285 = 'ETIQUETA COUCHE 100X70 ROLO COM 1285 TUBETE 3" COM SERRILHA'
QTD = 50.0
CUSTO_ROLO_554 = 15.902574
CUSTO_TOTAL_554 = 795.13
CUSTO_ROLO_1285 = 39.476603
CUSTO_TOTAL_1285 = 1973.83


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def _planilha():
    path = PLANILHA if PLANILHA.exists() else ALT_PLANILHA
    assert path.exists(), f"planilha de etiquetas não encontrada: {path}"
    planilha = load_planilha_etiquetas(path)
    assert not planilha.empty
    return planilha


def test_nf_1161_554_nao_pega_linha_tubete_3():
    """Processa 1285 primeiro (ordem do faturamento) e mesmo assim 554 fica com 795,13."""
    planilha = _planilha()
    nf_key = norm_nf("RT001161")

    row_1285 = match_planilha_etiqueta(planilha, nf_key, QTD, DESC_1285)
    assert row_1285 is not None, "sem match para 1285 / tubete 3"
    d1285 = detalhe_from_planilha(row_1285)
    assert approx(d1285["custo_rolo"], CUSTO_ROLO_1285), d1285["custo_rolo"]
    assert approx(d1285["custo_total_planilha"], CUSTO_TOTAL_1285), d1285[
        "custo_total_planilha"
    ]

    row_554 = match_planilha_etiqueta(planilha, nf_key, QTD, DESC_554)
    assert row_554 is not None, "sem match para 554 / tubete 1"
    d554 = detalhe_from_planilha(row_554)
    assert approx(d554["custo_rolo"], CUSTO_ROLO_554), d554["custo_rolo"]
    assert approx(d554["custo_total_planilha"], CUSTO_TOTAL_554), (
        d554["custo_total_planilha"],
        CUSTO_TOTAL_554,
    )
    assert not approx(d554["custo_total_planilha"], CUSTO_TOTAL_1285)


def test_nf_1161_554_sozinho():
    planilha = _planilha()
    row = match_planilha_etiqueta(planilha, norm_nf("RT001161"), QTD, DESC_554)
    assert row is not None
    d = detalhe_from_planilha(row)
    assert approx(d["custo_total_planilha"], CUSTO_TOTAL_554), d["custo_total_planilha"]


if __name__ == "__main__":
    test_nf_1161_554_nao_pega_linha_tubete_3()
    test_nf_1161_554_sozinho()
    print("OK: NF 1161 couche 100x70 / 554 / tubete 1\" custo R$ 795,13")
