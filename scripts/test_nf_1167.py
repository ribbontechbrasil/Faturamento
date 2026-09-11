#!/usr/bin/env python3
"""NF 1167 item rot.PEAD86x165T3: custo conferido R$ 602,40."""

from pathlib import Path

from gerar_relatorio_custo import (
    calcular_relatorio,
    custo_override,
    load_faturamento_agosto,
)

ROOT = Path(__file__).resolve().parents[1]
NF_1167_CUSTO = 602.40
NF_1167_CUSTO_ANTIGO_P = 500.0
NF_1167_CUSTO_COM_FRETE_IMPOSTO = 659.06  # 500 + 88,94 + 70,12


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def test_override_direto():
    assert custo_override(1167, "rot.PEAD86x165T3") == NF_1167_CUSTO
    assert custo_override("1167", "ro.PEAD86x165T3") == NF_1167_CUSTO
    assert custo_override(1167, "ETBOPP100x80") is None
    assert custo_override(1176, "rot.PEAD86x165T3") is None


def test_planilha_agosto_item():
    ago = load_faturamento_agosto(ROOT)
    row = ago[(ago["Número"] == "1167") & (ago["Código"].astype(str).str.contains("PEAD86x165", case=False))]
    assert len(row) == 1, row
    custo = float(row.iloc[0]["Custo total item"])
    assert approx(custo, NF_1167_CUSTO), custo
    assert not approx(custo, NF_1167_CUSTO_ANTIGO_P, tol=1.0), custo
    assert not approx(custo, NF_1167_CUSTO_COM_FRETE_IMPOSTO, tol=1.0), custo
    assert row.iloc[0]["Base custo unitário"] == "custo_conferido"


def test_relatorio_inclui_override():
    df = calcular_relatorio(ROOT / "Faturamento_RBT (2).xlsx")
    dts = pd_to_month(df)
    ago = df[dts == "2026-08"]
    row = ago[(ago["Número"] == "1167") & (ago["Código"].astype(str).str.contains("PEAD86x165", case=False))]
    assert len(row) == 1, row
    custo = float(row.iloc[0]["Custo total item"])
    assert approx(custo, NF_1167_CUSTO), custo


def pd_to_month(df):
    import pandas as pd

    return pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce").dt.strftime(
        "%Y-%m"
    )


if __name__ == "__main__":
    test_override_direto()
    test_planilha_agosto_item()
    test_relatorio_inclui_override()
    print("OK: NF 1167 rot.PEAD86x165T3 custo R$ 602,40")
