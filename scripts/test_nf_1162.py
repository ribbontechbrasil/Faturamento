#!/usr/bin/env python3
"""Garante custos da NF 1162 (FRIVASA), com 50x200x2 em R$ 2.868,85."""

from pathlib import Path

from gerar_relatorio_custo import (
    detalhe_from_planilha,
    load_planilha_etiquetas,
    match_planilha_etiqueta,
    nf_digits,
    norm_nf,
)

ROOT = Path(__file__).resolve().parents[1]
PLANILHA = ROOT / "Planilha_calculo_custo_etiquetas_jul26.xlsx"
ALT_PLANILHA = ROOT / "Planilha para cálculo de custo de etiquetas - jul 26.xlsx"

# Itens da NF RT001162 no faturamento × Custo Final (coluna X)
# 50x200x2: custo total informado R$ 2.868,85 (não o Custo Final 4.749,05)
ITENS_1162 = [
    (
        152.0,
        'ETIQUETA ESPECIAL COM CÓDIGO DE BARRA 102X197 ROLO COM 500 TUBETE 3"',
        36.3142,
        None,
    ),
    (
        60.0,
        "ETIQUETA BOPP FOSCO 50X235X1 ROLO C/ 500 TUBETE 3'",
        30.8740,
        None,
    ),
    (
        60.0,
        'ETIQUETA BOPP FOSCO 50X200X2 ROLO C/ 1000 TUBETE 3"',
        47.8141666667,
        2868.85,
    ),
    (
        8.0,
        'ROTULO BOPP ADESIVO 86x165 mm 3" C/1000 - FRIVASA',
        23.0258,
        None,
    ),
]


def approx(a, b, tol=0.02):
    return abs(a - b) <= tol


def test_norm_nf_rt_1162():
    assert norm_nf("RT001162") == "RT1162"
    assert norm_nf(1162) == "1162"
    assert nf_digits("RT1162") == "1162"


def test_nf_1162_casa_custo_final():
    path = PLANILHA if PLANILHA.exists() else ALT_PLANILHA
    assert path.exists(), f"planilha de etiquetas não encontrada: {path}"
    planilha = load_planilha_etiquetas(path)
    assert not planilha.empty
    nf_key = norm_nf("RT001162")
    matched = []
    for qtd, desc, custo, custo_total in ITENS_1162:
        row = match_planilha_etiqueta(planilha, nf_key, qtd, desc)
        assert row is not None, f"sem match para NF 1162: {desc}"
        detalhe = detalhe_from_planilha(row)
        assert detalhe.get("custo_inclui_frete_imposto"), desc
        assert detalhe.get("fonte") == "planilha_custo_final", desc
        assert detalhe.get("custo_rolo") is not None, desc
        assert approx(float(detalhe["custo_rolo"]), custo), (
            desc,
            detalhe["custo_rolo"],
            custo,
        )
        if custo_total is not None:
            assert detalhe.get("custo_total_planilha") is not None, desc
            assert approx(float(detalhe["custo_total_planilha"]), custo_total, tol=0.02), (
                desc,
                detalhe["custo_total_planilha"],
                custo_total,
            )
            # Garante que NÃO ficou o valor antigo (4.749,05)
            assert not approx(float(detalhe["custo_total_planilha"]), 4749.05, tol=0.05), desc
        matched.append(desc)
    assert len(matched) == 4


if __name__ == "__main__":
    test_norm_nf_rt_1162()
    test_nf_1162_casa_custo_final()
    print("OK: NF 1162 casa Custo Final; 50x200x2 = R$ 2.868,85")
