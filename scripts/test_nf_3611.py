#!/usr/bin/env python3
"""NF 3611 item ETBOPP80185 (FRANCAP): custo conferido R$ 5.166,90."""

from pathlib import Path

from gerar_relatorio_custo import (
    calcular_relatorio,
    custo_override,
    load_faturamento_agosto,
)

ROOT = Path(__file__).resolve().parents[1]
NF_3611_CUSTO = 5166.90
NF_3611_CUSTO_ANTIGO = 3818.40  # 3163,50 + 70 + 584,90
NF_3611_VENDA = 6364.50


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def _row_3611(df):
    return df[(df["Número"] == "3611") & (df["Código"].astype(str).str.contains("ETBOPP80185"))]


def test_override_direto():
    assert custo_override(3611, "ETBOPP80185") == NF_3611_CUSTO
    assert custo_override("3611", "ETBOPP80185") == NF_3611_CUSTO


def test_planilha_agosto_item():
    ago = load_faturamento_agosto(ROOT)
    row = _row_3611(ago)
    assert len(row) == 1, row
    r = row.iloc[0]
    assert approx(r["Valor total venda"], NF_3611_VENDA, tol=0.05)
    assert approx(r["Custo total item"], NF_3611_CUSTO), r["Custo total item"]
    assert not approx(r["Custo total item"], NF_3611_CUSTO_ANTIGO, tol=1.0)
    assert not approx(r["Custo total item"], 3163.50, tol=1.0)
    assert r["Base custo unitário"] == "custo_conferido"


def test_relatorio_inclui_override():
    df = calcular_relatorio(ROOT / "Faturamento_RBT (2).xlsx")
    dts = pd_to_month(df)
    ago = df[dts == "2026-08"]
    row = _row_3611(ago)
    assert len(row) == 1, row
    assert approx(float(row.iloc[0]["Custo total item"]), NF_3611_CUSTO)


def pd_to_month(df):
    import pandas as pd

    return pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce").dt.strftime(
        "%Y-%m"
    )


if __name__ == "__main__":
    test_override_direto()
    test_planilha_agosto_item()
    test_relatorio_inclui_override()
    print("OK: NF 3611 ETBOPP80185 custo R$ 5.166,90")
