#!/usr/bin/env python3
"""Agosto/2026: custo já inclui frete/imposto; frete informativo; investimento separado."""

from pathlib import Path

from gerar_relatorio_custo import calcular_relatorio, load_faturamento_agosto
from processar_despesas import competencia_from_filename, processar

ROOT = Path(__file__).resolve().parents[1]
FAT = ROOT / "Faturamento_RBT (2).xlsx"
FRETE_AGO = 9102.03
VENDA_AGO = 303982.14
CUSTO_AGO = 181491.61
INV_FLEXOMETAL = 1774.84


def approx(a, b, tol=0.05):
    return abs(float(a) - float(b)) <= tol


def test_competencia_arquivo_agosto():
    assert competencia_from_filename(Path("Despesas Ago 2026.xlsx")) == "2026-08"


def test_faturamento_agosto_totais():
    ago = load_faturamento_agosto(ROOT)
    assert not ago.empty
    assert len(ago) >= 120
    venda = float(ago["Valor total venda"].sum())
    custo = float(ago["Custo total item"].sum())
    frete = float(ago["Frete"].sum())
    liq = float(ago["Venda líquida"].sum())
    assert approx(venda, VENDA_AGO, tol=1.0), venda
    assert approx(custo, CUSTO_AGO, tol=1.0), custo
    assert approx(frete, FRETE_AGO, tol=0.05), frete
    # Venda líquida = venda − custo (frete/imposto já no custo)
    assert approx(liq, venda - custo, tol=0.5), (liq, venda - custo)
    assert not approx(liq, venda - custo - frete, tol=50)
    assert (ago["Base frete"] == "incluso_custo_informativo").all()
    pct_frete = frete / venda
    assert 0.029 < pct_frete < 0.031, pct_frete


def test_relatorio_inclui_agosto():
    df = calcular_relatorio(FAT)
    dts = pd_to_month(df)
    ago = df[dts == "2026-08"]
    assert len(ago) >= 120
    assert approx(ago["Frete"].sum(), FRETE_AGO, tol=0.05)
    assert approx(ago["Valor total venda"].sum(), VENDA_AGO, tol=1.0)


def pd_to_month(df):
    import pandas as pd

    return pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce").dt.strftime(
        "%Y-%m"
    )


def test_despesas_agosto_separa_investimento():
    path = ROOT / "Despesas Ago 2026.xlsx"
    assert path.exists()
    df = processar(path, competencia_padrao="2026-08")
    assert (df["Competência"] == "2026-08").all()
    inv = df[df["Tipo"] == "investimento"]
    assert len(inv) == 1, inv
    assert "Flexometal" in str(inv.iloc[0]["Fornecedor"])
    assert approx(inv.iloc[0]["Valor"], INV_FLEXOMETAL)
    opex = df[df["Tipo"] != "investimento"]["Valor"].sum()
    total = df["Valor"].sum()
    assert approx(total, opex + INV_FLEXOMETAL, tol=0.05)
    assert opex > 50000
    # Comissão de vendas entra como despesa ADM
    com = df[df["Categoria"] == "Comissão de vendas"]
    assert not com.empty


if __name__ == "__main__":
    test_competencia_arquivo_agosto()
    test_faturamento_agosto_totais()
    test_relatorio_inclui_agosto()
    test_despesas_agosto_separa_investimento()
    print("OK: agosto/2026 · frete R$ 9.102,03 informativo · Flexometal investimento")
