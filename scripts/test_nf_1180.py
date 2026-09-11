#!/usr/bin/env python3
"""NF 1180 item 300445/110 (SAUDALI): custo R$ 22.593,63 e venda líquida R$ 6.684,45."""

from pathlib import Path

from gerar_relatorio_custo import (
    calcular_relatorio,
    custo_override,
    load_faturamento_agosto,
    venda_liquida_override,
)

ROOT = Path(__file__).resolve().parents[1]
NF_1180_CUSTO = 22593.63
NF_1180_LIQ = 6684.45
NF_1180_VENDA = 29278.08
NF_1180_CUSTO_ANTIGO = 10359.39  # 7119,36 + 605 + 2635,03
NF_1180_LIQ_ANTIGA = 18918.69


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def _row_1180(df):
    return df[(df["Número"] == "1180") & (df["Código"].astype(str).str.contains("300445/110"))]


def test_override_direto():
    assert custo_override(1180, "300445/110") == NF_1180_CUSTO
    assert venda_liquida_override(1180, "300445/110") == NF_1180_LIQ
    assert custo_override(1178, "300445/110") is None


def test_planilha_agosto_item():
    ago = load_faturamento_agosto(ROOT)
    row = _row_1180(ago)
    assert len(row) == 1, row
    r = row.iloc[0]
    assert approx(r["Valor total venda"], NF_1180_VENDA, tol=0.05)
    assert approx(r["Custo total item"], NF_1180_CUSTO), r["Custo total item"]
    assert approx(r["Venda líquida"], NF_1180_LIQ), r["Venda líquida"]
    assert not approx(r["Custo total item"], NF_1180_CUSTO_ANTIGO, tol=1.0)
    assert not approx(r["Venda líquida"], NF_1180_LIQ_ANTIGA, tol=1.0)


def test_relatorio_inclui_override():
    df = calcular_relatorio(ROOT / "Faturamento_RBT (2).xlsx")
    dts = pd_to_month(df)
    ago = df[dts == "2026-08"]
    row = _row_1180(ago)
    assert len(row) == 1, row
    r = row.iloc[0]
    assert approx(r["Custo total item"], NF_1180_CUSTO), r["Custo total item"]
    assert approx(r["Venda líquida"], NF_1180_LIQ), r["Venda líquida"]


def pd_to_month(df):
    import pandas as pd

    return pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce").dt.strftime(
        "%Y-%m"
    )


if __name__ == "__main__":
    test_override_direto()
    test_planilha_agosto_item()
    test_relatorio_inclui_override()
    print("OK: NF 1180 300445/110 custo R$ 22.593,63 · venda líquida R$ 6.684,45")
