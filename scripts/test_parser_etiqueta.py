#!/usr/bin/env python3
"""Testes rápidos do parser de descrição de etiqueta."""

from gerar_relatorio_custo import (
    parse_etiqueta,
    custo_unitario_etiqueta_nf,
    calc_custo_etiqueta,
    parse_tipo_tubete,
    lookup_custo_tubete,
    parse_dimensoes_planilha,
)


def approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


def test_rolo_1500_und():
    p = parse_etiqueta(
        'ETIQUETA BOPP FOSCA 240 X 120 MM TUBETE 3" ROLO COM 1500 UND'
    )
    assert p["completo"]
    assert p["nr_etiquetas_rolo"] == 1500
    assert p["material"] == "Bopp"
    assert p["tubete_pol"] == 3.0
    area = ((240 + 6) * (120 + 6)) / 1_000_000
    # Bopp 4.45 + tubete 106x3 = 1.3945
    assert approx(p["custo_rolo"], area * 1500 * 4.45 + 1.3945)


def test_metros_para_etiquetas():
    p = parse_etiqueta("ETIQUETA COUCHE AUTOMACAO 100X160 ROLO COM 82m TUBETE 3\"")
    assert p["completo"]
    assert p["qtd_rolo_tipo"] == "m"
    esperado = 82 / ((160 + 3) / 1000)
    assert approx(p["nr_etiquetas_rolo"], esperado)


def test_nao_confundir_colunas():
    p = parse_etiqueta(
        'ETIQUETA ADESIVA BOPP ALS 50MM X 50MM  C/ 02 COLUNAS - C/ SERRILHA - TUBETE 1"'
    )
    assert not p["completo"]
    assert "qtd_rolo" in p["pendencias"]


def test_base_custo_etiqueta_vs_rolo_fallback():
    """Fallback histórico ainda rateia por etiqueta se o preço unitário for << custo do rolo."""
    custo_rolo = 207.8583
    c, base = custo_unitario_etiqueta_nf(custo_rolo, 1500, "UN", 0.33)
    assert base == "etiqueta"
    assert approx(c, custo_rolo / 1500)
    c2, base2 = custo_unitario_etiqueta_nf(custo_rolo, 1500, "RL", 38.0)
    assert base2 == "rolo"
    assert approx(c2, custo_rolo)


def test_tubete_planilha():
    diam, pol = parse_tipo_tubete("3 x 106")
    assert diam == 106
    assert pol == 3.0
    custo, label = lookup_custo_tubete(diam, pol)
    assert approx(custo, 1.3945)
    diam2, pol2 = parse_tipo_tubete("1 x 96")
    custo2, _ = lookup_custo_tubete(diam2, pol2)
    assert approx(custo2, 0.3228)  # alias 96 → 95


def test_dimensoes_cm():
    L, A, cols = parse_dimensoes_planilha("2,5 x 10,4")
    assert approx(L, 25.0)
    assert approx(A, 104.0)
    assert cols == 1
    L2, A2, cols2 = parse_dimensoes_planilha("50 X 40 X 2")
    assert approx(L2, 50.0)
    assert approx(A2, 40.0)
    assert cols2 == 2


def test_calc_com_tubetes():
    d = calc_custo_etiqueta(
        largura_mm=100,
        altura_mm=50,
        metragem_total_m=250,
        qtd_tubetes=10,
        nr_etiquetas_informado=500,
        custo_substrato_m2=3.26,
        custo_tubete=0.3594,
        custo_embalagem_rolo=0.1575,
    )
    assert d["completo"]
    area = ((100 + 6) * (50 + 6)) / 1_000_000
    mat = area * 500 * 3.26
    assert approx(d["custo_rolo"], mat + 0.3594 + 0.1575)
    assert approx(d["custo_total_planilha"], d["custo_rolo"] * 10)


if __name__ == "__main__":
    test_rolo_1500_und()
    test_metros_para_etiquetas()
    test_nao_confundir_colunas()
    test_base_custo_etiqueta_vs_rolo_fallback()
    test_tubete_planilha()
    test_dimensoes_cm()
    test_calc_com_tubetes()
    print("OK: todos os testes passaram")
