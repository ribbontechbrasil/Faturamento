#!/usr/bin/env python3
"""NF 3597 item 100200006 deve usar custo total R$ 143,06."""

from pathlib import Path

import pandas as pd

from gerar_relatorio_custo import (
    codes_compatible,
    load_planilha_custo_itens,
    load_planilha_frete_ribbon,
    match_custo_item,
    match_frete_ribbon,
    norm_nf,
)

ROOT = Path(__file__).resolve().parents[1]
TOTAL_ESPERADO = 143.06
QTD = 45.0


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def test_codes_100200006():
    assert codes_compatible("100200006", "10020006")
    assert codes_compatible("10020006", "100200006")


def test_custo_3597_100200006():
    rib = load_planilha_frete_ribbon(ROOT / "Ribbon_com_frete_real.xlsx")
    custo = load_planilha_custo_itens(ROOT / "Custo_itens_exceto_etiquetas_jul26.xlsx")
    assert not rib.empty
    nf = norm_nf(3597)
    m = match_frete_ribbon(rib, nf, "10020006", QTD, 184.5)
    assert m is not None, "ribbon match NF 3597 / 10020006"
    assert m.get("custo_total") is not None
    assert approx(m["custo_total"], TOTAL_ESPERADO), (m["custo_total"], TOTAL_ESPERADO)

    # Planilha de custo unitário (exceto etiquetas)
    cu = match_custo_item(custo, nf, "100200006", QTD, 184.5)
    assert cu is not None
    assert approx(cu * QTD, TOTAL_ESPERADO), (cu, cu * QTD)


if __name__ == "__main__":
    test_codes_100200006()
    test_custo_3597_100200006()
    print("OK: NF 3597 item 100200006 custo R$ 143,06")
