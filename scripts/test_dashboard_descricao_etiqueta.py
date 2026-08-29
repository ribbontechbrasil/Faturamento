#!/usr/bin/env python3
"""Garante que o detalhe por cliente/NF mostra a descrição da NF (Etiqueta...), não o material."""

from pathlib import Path

from gerar_dashboard_html import build_rows, render_html


def test_template_uses_descricao_not_material():
    src = (Path(__file__).resolve().parent / "gerar_dashboard_html.py").read_text(
        encoding="utf-8"
    )
    assert "Material / descrição" not in src
    assert "<th>Descrição</th>" in src
    assert "const matDesc" not in src
    assert "const desc = r.desc || '—';" in src
    assert "class=\"desc-etiqueta\"" in src


def test_build_rows_keeps_etiqueta_description():
    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "Data de emissão": "01/07/2026",
                "Número": "3572",
                "Nome": "Cliente Teste",
                "UF": "MG",
                "Código": "X",
                "Descrição": "ETIQUETA BOPP 100X50 ROLO COM 1500 TUBETE 3\"",
                "Segmento": "Etiqueta",
                "Material": "BOPP PROTACK 212 X 1000 AP718",
                "Tubete": "3 x 106",
                "Custo_rolo": 10.0,
                "Valor total venda": 100.0,
                "Custo total item": 20.0,
                "Frete": 0.0,
                "Base frete": "incluso_custo_final",
                "Imposto (9,2%)": 0.0,
                "Venda líquida": 80.0,
                "% Lucro": 4.0,
                "Status custo": "ok",
                "Custo unitário item": 10.0,
                "Base custo unitário": "planilha_jul26",
            }
        ]
    )
    rows = build_rows(df)
    assert len(rows) == 1
    assert rows[0]["desc"].startswith("ETIQUETA")
    assert "BOPP PROTACK" not in rows[0]["desc"]
    assert rows[0]["mat"] == "BOPP PROTACK 212 X 1000 AP718"


def test_html_detalhe_column_is_descricao():
    html = render_html([], "01/01/2026 a 31/01/2026", [])
    assert ">Detalhe por cliente e NF<" in html
    assert "Material / descrição" not in html
    # Coluna do detalhe (não a de Lucro por item, que também tem Descrição)
    idx = html.find("Detalhe por cliente e NF")
    snippet = html[idx : idx + 800]
    assert "<th>Descrição</th>" in snippet
    assert "const desc = r.desc || '—';" in html
    assert "${desc}" in html or "${{desc}}" in html or ">${desc}<" in html or ">${desc}</td>" in html


if __name__ == "__main__":
    test_template_uses_descricao_not_material()
    test_build_rows_keeps_etiqueta_description()
    test_html_detalhe_column_is_descricao()
    print("OK: detalhe por cliente/NF usa descrição da NF")
