#!/usr/bin/env python3
"""NF 1202 item SC0548 (venda R$ 156,00): custo conferido R$ 122,34."""

from pathlib import Path

from gerar_relatorio_custo import (
    calcular_relatorio,
    custo_override,
    load_faturamento_agosto,
)

ROOT = Path(__file__).resolve().parents[1]
NF_1202_CUSTO = 122.34
NF_1202_VENDA = 156.00
NF_1202_CUSTO_ANTIGO = 162.34  # 108 + 40 + 14,34


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def _row_1202(df):
    m = df[(df["Número"] == "1202") & (df["Código"].astype(str).str.contains("SC0548"))]
    return m


def test_override_direto():
    assert custo_override(1202, "SC0548") == NF_1202_CUSTO
    assert custo_override(1202, "525100-004-S75") is None


def test_planilha_agosto_item():
    ago = load_faturamento_agosto(ROOT)
    row = _row_1202(ago)
    assert len(row) == 1, row
    r = row.iloc[0]
    assert approx(r["Valor total venda"], NF_1202_VENDA, tol=0.05)
    assert approx(r["Custo total item"], NF_1202_CUSTO), r["Custo total item"]
    assert not approx(r["Custo total item"], NF_1202_CUSTO_ANTIGO, tol=1.0)
    assert r["Base custo unitário"] == "custo_conferido"
    # o outro item da NF 1202 não muda
    outro = ago[(ago["Número"] == "1202") & (ago["Código"].astype(str).str.contains("525100"))]
    assert len(outro) == 1
    assert not approx(float(outro.iloc[0]["Custo total item"]), NF_1202_CUSTO, tol=1.0)


def test_relatorio_inclui_override():
    df = calcular_relatorio(ROOT / "Faturamento_RBT (2).xlsx")
    dts = pd_to_month(df)
    ago = df[dts == "2026-08"]
    row = _row_1202(ago)
    assert len(row) == 1, row
    assert approx(float(row.iloc[0]["Custo total item"]), NF_1202_CUSTO)
    assert approx(float(row.iloc[0]["Valor total venda"]), NF_1202_VENDA, tol=0.05)


def pd_to_month(df):
    import pandas as pd

    return pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce").dt.strftime(
        "%Y-%m"
    )


if __name__ == "__main__":
    test_override_direto()
    test_planilha_agosto_item()
    test_relatorio_inclui_override()
    print("OK: NF 1202 SC0548 custo R$ 122,34")
