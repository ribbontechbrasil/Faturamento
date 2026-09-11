#!/usr/bin/env python3
"""NF 1176 item ETBOPP100x80: venda líquida conferida R$ 1.024,56."""

from pathlib import Path

from gerar_relatorio_custo import (
    calcular_relatorio,
    load_faturamento_agosto,
    venda_liquida_override,
)

ROOT = Path(__file__).resolve().parents[1]
NF_1176_LIQ = 1024.56
NF_1176_LIQ_ERRADA_T = -1186.07


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def test_override_direto():
    assert venda_liquida_override(1176, "ETBOPP100x80") == NF_1176_LIQ
    assert venda_liquida_override("1176", "ETBOPP100X80") == NF_1176_LIQ
    assert venda_liquida_override(1176, "ETBOPP80185") is None
    assert venda_liquida_override(1175, "ETBOPP100x80") is None


def test_planilha_agosto_item():
    ago = load_faturamento_agosto(ROOT)
    nf1176 = ago[(ago["Número"] == "1176") & (ago["Código"] == "ETBOPP100x80")]
    assert len(nf1176) == 1, nf1176
    liq = float(nf1176.iloc[0]["Venda líquida"])
    assert approx(liq, NF_1176_LIQ), liq
    assert not approx(liq, NF_1176_LIQ_ERRADA_T, tol=1.0), liq


def test_relatorio_inclui_override():
    df = calcular_relatorio(ROOT / "Faturamento_RBT (2).xlsx")
    dts = pd_to_month(df)
    ago = df[dts == "2026-08"]
    nf1176 = ago[(ago["Número"] == "1176") & (ago["Código"] == "ETBOPP100x80")]
    assert len(nf1176) == 1, nf1176
    liq = float(nf1176.iloc[0]["Venda líquida"])
    assert approx(liq, NF_1176_LIQ), liq
    assert not approx(liq, NF_1176_LIQ_ERRADA_T, tol=1.0), liq


def pd_to_month(df):
    import pandas as pd

    return pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce").dt.strftime(
        "%Y-%m"
    )


if __name__ == "__main__":
    test_override_direto()
    test_planilha_agosto_item()
    test_relatorio_inclui_override()
    print("OK: NF 1176 ETBOPP100x80 venda líquida R$ 1.024,56")
