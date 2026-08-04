#!/usr/bin/env python3
"""Testes rápidos do parser de descrição de etiqueta."""

from gerar_relatorio_custo import parse_etiqueta, custo_unitario_etiqueta_nf


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
    assert approx(p["area_etiqueta_m2"], area)
    assert approx(p["custo_rolo"], area * 1500 * 4.45 + 0.96)


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


def test_base_custo_etiqueta_vs_rolo():
    custo_rolo = 207.8583
    c, base = custo_unitario_etiqueta_nf(custo_rolo, 1500, "UN", 0.33)
    assert base == "etiqueta"
    assert approx(c, custo_rolo / 1500)
    c2, base2 = custo_unitario_etiqueta_nf(custo_rolo, 1500, "RL", 38.0)
    assert base2 == "rolo"
    assert approx(c2, custo_rolo)


if __name__ == "__main__":
    test_rolo_1500_und()
    test_metros_para_etiquetas()
    test_nao_confundir_colunas()
    test_base_custo_etiqueta_vs_rolo()
    print("OK: todos os testes passaram")
