#!/usr/bin/env python3
"""Impressão do relatório mensal no dashboard HTML."""

from pathlib import Path

from gerar_dashboard_html import render_html


def test_print_button_and_css_in_template():
    html = render_html([], "01/07/2026 a 31/08/2026", [])
    assert 'id="btnImprimir"' in html
    assert 'id="btnImprimirFiltros"' in html
    assert "@media print" in html
    assert "function printRelatorio()" in html
    assert "function beginPrintMode()" in html
    assert "snapshotChartsForPrint" in html
    assert "window.print()" in html
    assert "state.printing" in html
    assert "A4 portrait" in html
    assert "chart-print-img" in html
    assert 'id="printMeta"' in html
    assert "Imprimir relatório do mês" in html
    assert "Imprimir relatório completo" not in html
    assert "function monthForPrint()" in html
    assert "Um mês por vez" in html
    assert "A impressão é mês a mês" in html
    assert "applyQueryParams" in html
    assert 'printQ ===' in html or "printQ === '1'" in html
    assert "body.is-printing .chart-print-img" in html


def test_print_expands_tables():
    src = (Path(__file__).resolve().parent / "gerar_dashboard_html.py").read_text(
        encoding="utf-8"
    )
    assert "state.printing ? Math.max(sorted.length, 1) : filters.pageSize" in src
    assert "state.printing ? 0 : Number(filters.topN || 0)" in src
    assert "state.printing ? detalhe.length : 250" in src
    assert "!state.printing && (r.st === 'inc' || r.st === 'manual')" in src
    assert "function monthForPrint()" in src
    assert "i.checked = i.value === mes" in src
    assert "updatePrintButtonLabel" in src


if __name__ == "__main__":
    test_print_button_and_css_in_template()
    test_print_expands_tables()
    print("OK: testes de impressão passaram")
