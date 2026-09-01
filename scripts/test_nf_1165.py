#!/usr/bin/env python3
"""NF 1165 (Vitaminas / Mineira de Rações) e NF 3565 (LONAX).

- Etiqueta branca 2,5x10,4 da NF 1165: R$ 128,29 (não 819,78 da largura 205 mm)
- LONAX: 2 rolos de etiqueta redonda 13 mm azul / 5000 un, custo R$ 63,88, venda R$ 370,00
"""

from pathlib import Path

from gerar_relatorio_custo import (
    NFS_EXCLUIDAS,
    calcular_relatorio,
    detalhe_from_planilha,
    load_planilha_etiquetas,
    match_planilha_etiqueta,
    nf_digits,
    norm_nf,
)

ROOT = Path(__file__).resolve().parents[1]
PLANILHA = ROOT / "Planilha_calculo_custo_etiquetas_jul26.xlsx"
ALT_PLANILHA = ROOT / "Planilha para cálculo de custo de etiquetas - jul 26.xlsx"
FAT = ROOT / "Faturamento_RBT (2).xlsx"

DESC_BRANCA = 'ETIQUETA BRANCA 2,5X10,4 ROLO COM 1000 TUBETE 3"'
DESC_AZUL = "ETIQUETA ADESIVA SPOT 13MM AZUL 5000UN"
QTD_BRANCA = 10.0
QTD_AZUL = 2.0
CUSTO_BRANCA = 128.29
CUSTO_AZUL = 63.88
VENDA_AZUL = 370.00


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def _planilha():
    path = PLANILHA if PLANILHA.exists() else ALT_PLANILHA
    assert path.exists(), f"planilha de etiquetas não encontrada: {path}"
    planilha = load_planilha_etiquetas(path)
    assert not planilha.empty
    return planilha


def test_nf_1165_etiqueta_branca_128_29():
    planilha = _planilha()
    row = match_planilha_etiqueta(planilha, norm_nf("RT001165"), QTD_BRANCA, DESC_BRANCA)
    assert row is not None, "sem match para NF 1165 etiqueta branca 2,5x10,4"
    d = detalhe_from_planilha(row)
    assert d.get("fonte") == "planilha_custo_final"
    assert approx(float(d["largura_mm"]), 25.0), d.get("largura_mm")
    assert approx(float(d["altura_mm"]), 104.0), d.get("altura_mm")
    assert approx(float(d["qtd_tubetes"]), QTD_BRANCA), d.get("qtd_tubetes")
    assert approx(float(d["custo_total_planilha"]), CUSTO_BRANCA), (
        d["custo_total_planilha"],
        CUSTO_BRANCA,
    )
    # Largura 205 mm gerava ~R$ 819,78
    assert not approx(float(d["custo_total_planilha"]), 819.78, tol=1.0)


def test_nf_3565_lonax_nao_excluida():
    assert "3565" not in NFS_EXCLUIDAS
    assert nf_digits(norm_nf("003565")) == "3565"


def test_nf_3565_lonax_etiqueta_azul_63_88():
    planilha = _planilha()
    row = match_planilha_etiqueta(planilha, norm_nf("003565"), QTD_AZUL, DESC_AZUL)
    assert row is not None, "sem match para NF 3565 LONAX 13 mm azul"
    d = detalhe_from_planilha(row)
    assert d.get("fonte") == "planilha_custo_final"
    assert approx(float(d["qtd_tubetes"]), QTD_AZUL), d.get("qtd_tubetes")
    assert approx(float(d["custo_total_planilha"]), CUSTO_AZUL), (
        d["custo_total_planilha"],
        CUSTO_AZUL,
    )


def test_relatorio_1165_e_3565():
    df = calcular_relatorio(FAT)
    n1165 = df[df["Número"] == "1165"]
    branca = n1165[n1165["Descrição"].astype(str).str.contains("2,5X10,4", case=False, na=False)]
    assert len(branca) == 1, branca[["Descrição", "Custo total item"]].to_string()
    assert approx(float(branca.iloc[0]["Custo total item"]), CUSTO_BRANCA), branca.iloc[0][
        "Custo total item"
    ]

    n3565 = df[df["Número"] == "3565"]
    assert len(n3565) >= 1, "NF 3565 LONAX deve entrar no relatório"
    azul = n3565[n3565["Descrição"].astype(str).str.contains("13MM AZUL", case=False, na=False)]
    assert len(azul) == 1, azul[["Descrição", "Custo total item", "Valor total venda"]].to_string()
    assert "LONAX" in str(azul.iloc[0]["Nome"]).upper()
    assert approx(float(azul.iloc[0]["Custo total item"]), CUSTO_AZUL), azul.iloc[0][
        "Custo total item"
    ]
    assert approx(float(azul.iloc[0]["Valor total venda"]), VENDA_AZUL), azul.iloc[0][
        "Valor total venda"
    ]
    assert approx(float(azul.iloc[0]["Quantidade"]), QTD_AZUL)


if __name__ == "__main__":
    test_nf_1165_etiqueta_branca_128_29()
    test_nf_3565_lonax_nao_excluida()
    test_nf_3565_lonax_etiqueta_azul_63_88()
    test_relatorio_1165_e_3565()
    print("OK: NF 1165 branca R$ 128,29 · NF 3565 LONAX 13 mm azul R$ 63,88 / venda R$ 370,00")
