#!/usr/bin/env python3
"""Agosto/2026: coluna T = venda líquida; NF 1176 ETBOPP100x80 = R$ 1.024,56."""

from pathlib import Path

from gerar_relatorio_custo import (
    _agosto_custo_e_liquida,
    calcular_relatorio,
    load_faturamento_agosto,
    venda_liquida_override,
)
from processar_despesas import competencia_from_filename, processar

ROOT = Path(__file__).resolve().parents[1]
FAT = ROOT / "Faturamento_RBT (2).xlsx"
FRETE_AGO = 9102.03
VENDA_AGO = 303982.14
IMPOSTO_AGO = 27867.48
# Coluna P = só produto (Camila)
CUSTO_P_CAMILA = 181491.61
# Custo total = P + frete + imposto
CUSTO_AGO = 218461.13
# Coluna T = venda líquida (NF 1176 ETBOPP100x80 conferida em R$ 1.024,56)
LIQ_AGO = 84993.31
INV_FLEXOMETAL = 1774.84
# NF 1176 BASE ETBOPP100x80
NF_1176_CUSTO_P = 3112.80
NF_1176_VENDA = 5494.50
NF_1176_FRETE = 200.00
NF_1176_IMPOSTO = 504.94
NF_1176_LIQ = 1024.56  # conferida (coluna T teórica era −1.186,07)
NF_1176_CUSTO = 3817.74  # 3112,80 + 200,00 + 504,94


def approx(a, b, tol=0.05):
    return abs(float(a) - float(b)) <= tol


def test_custo_total_e_produto_mais_frete_mais_imposto():
    custo, liq = _agosto_custo_e_liquida(
        NF_1176_CUSTO_P,
        NF_1176_FRETE,
        NF_1176_IMPOSTO,
        NF_1176_LIQ,
        NF_1176_VENDA,
    )
    assert approx(liq, NF_1176_LIQ, tol=0.02)
    assert approx(custo, NF_1176_CUSTO, tol=0.02)
    assert approx(custo, NF_1176_CUSTO_P + NF_1176_FRETE + NF_1176_IMPOSTO, tol=0.02)
    assert not approx(custo, NF_1176_CUSTO_P, tol=1.0)
    assert not approx(custo, NF_1176_LIQ, tol=1.0)


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
    assert approx(custo, CUSTO_P_CAMILA + FRETE_AGO + IMPOSTO_AGO, tol=1.0), custo
    assert not approx(custo, CUSTO_P_CAMILA, tol=1.0), custo
    assert approx(liq, LIQ_AGO, tol=1.0), liq
    assert approx(frete, FRETE_AGO, tol=0.05), frete
    assert (ago["Base frete"] == "incluso_custo_informativo").all()
    assert (ago["Base custo unitário"] == "planilha_agosto_custo_frete_imposto").all()
    pct_frete = frete / venda
    assert 0.029 < pct_frete < 0.031, pct_frete

    nf1176 = ago[(ago["Número"] == "1176") & (ago["Código"] == "ETBOPP100x80")]
    assert len(nf1176) == 1, nf1176
    assert approx(nf1176.iloc[0]["Valor total venda"], NF_1176_VENDA, tol=0.05)
    assert approx(nf1176.iloc[0]["Venda líquida"], NF_1176_LIQ, tol=0.05)
    assert approx(nf1176.iloc[0]["Custo total item"], NF_1176_CUSTO, tol=0.05)
    assert venda_liquida_override(1176, "ETBOPP100x80") == NF_1176_LIQ
    assert not approx(nf1176.iloc[0]["Custo total item"], NF_1176_CUSTO_P, tol=1.0)


def test_relatorio_inclui_agosto():
    df = calcular_relatorio(FAT)
    dts = pd_to_month(df)
    ago = df[dts == "2026-08"]
    assert len(ago) >= 120
    assert approx(ago["Frete"].sum(), FRETE_AGO, tol=0.05)
    assert approx(ago["Valor total venda"].sum(), VENDA_AGO, tol=1.0)
    assert approx(ago["Custo total item"].sum(), CUSTO_AGO, tol=1.0)
    assert not approx(ago["Custo total item"].sum(), CUSTO_P_CAMILA, tol=1.0)
    assert approx(ago["Venda líquida"].sum(), LIQ_AGO, tol=1.0)


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
    test_custo_total_e_produto_mais_frete_mais_imposto()
    test_competencia_arquivo_agosto()
    test_faturamento_agosto_totais()
    test_relatorio_inclui_agosto()
    test_despesas_agosto_separa_investimento()
    print("OK: agosto/2026 · T = venda líquida · custo = produto+frete+imposto")
