#!/usr/bin/env python3
"""NF 1190 item rot.03.001.00039 (INJEX): custo conferido R$ 1.252,32."""

from pathlib import Path

from gerar_relatorio_custo import (
    calcular_relatorio,
    custo_override,
    load_faturamento_agosto,
)

ROOT = Path(__file__).resolve().parents[1]
NF_1190_CUSTO = 1252.32
NF_1190_CUSTO_ANTIGO = 2128.82  # 1800 + 105,32 + 223,50


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def _row_1190(df):
    return df[(df["Número"] == "1190") & (df["Código"].astype(str).str.contains("03.001.00039"))]


def test_override_direto():
    assert custo_override(1190, "rot.03.001.00039") == NF_1190_CUSTO
    assert custo_override("1190", "rot.03.001.00039") == NF_1190_CUSTO
    assert custo_override(1190, "ETBOPP100x80") is None


def test_planilha_agosto_item():
    ago = load_faturamento_agosto(ROOT)
    row = _row_1190(ago)
    assert len(row) == 1, row
    custo = float(row.iloc[0]["Custo total item"])
    assert approx(custo, NF_1190_CUSTO), custo
    assert not approx(custo, NF_1190_CUSTO_ANTIGO, tol=1.0), custo
    assert not approx(custo, 1800.0, tol=1.0), custo
    assert row.iloc[0]["Base custo unitário"] == "custo_conferido"


def test_relatorio_inclui_override():
    df = calcular_relatorio(ROOT / "Faturamento_RBT (2).xlsx")
    dts = pd_to_month(df)
    ago = df[dts == "2026-08"]
    row = _row_1190(ago)
    assert len(row) == 1, row
    assert approx(float(row.iloc[0]["Custo total item"]), NF_1190_CUSTO)


def pd_to_month(df):
    import pandas as pd

    return pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce").dt.strftime(
        "%Y-%m"
    )


if __name__ == "__main__":
    test_override_direto()
    test_planilha_agosto_item()
    test_relatorio_inclui_override()
    print("OK: NF 1190 rot.03.001.00039 custo R$ 1.252,32")
