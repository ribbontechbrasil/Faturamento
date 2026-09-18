#!/usr/bin/env python3
"""Testes da relação planilha modelo × planilha nova de despesas."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

import relacionar_despesas as rd


class TestNormaEChave(unittest.TestCase):
    def test_ignora_acento_e_espaco(self):
        self.assertEqual(
            rd.chave("Augusto Vianna da Costa Torres", "Salário   "),
            rd.chave("augusto vianna da costa torres", "Salario"),
        )

    def test_formula_simples(self):
        self.assertEqual(rd._eval_simples("=75+197.85"), 272.85)
        self.assertEqual(rd._eval_simples(120), 120.0)
        self.assertIsNone(rd._eval_simples("=SUM(C1:C42)"))


class TestRelacao(unittest.TestCase):
    def test_preenche_valor_do_modelo_nas_linhas_casadas(self):
        modelo = [
            {"linha_origem": 3, "Fornecedor": "BDMG", "Histórico": "Empréstimo ", "Valor": 5920.08},
            {"linha_origem": 9, "Fornecedor": "Camila Barbosa Tannure", "Histórico": "Cesta básica", "Valor": 120.0},
        ]
        nova = [
            {"linha_origem": 6, "Fornecedor": "BDMG", "Histórico": "Empréstimo ", "Valor": 5933.24},
            {"linha_origem": 1, "Fornecedor": "Assiste/Ocupacional", "Histórico": "Medicina Trabalho", "Valor": 272.85},
        ]
        relacionadas, so_modelo = rd.relacionar(nova, modelo)
        self.assertEqual(relacionadas[0]["Relação"], "Encontrado no modelo")
        self.assertEqual(relacionadas[0]["Valor no modelo"], 5920.08)
        self.assertEqual(relacionadas[0]["Valor"], 5933.24)
        self.assertEqual(relacionadas[1]["Relação"], "Novo (não está no modelo)")
        self.assertIsNone(relacionadas[1]["Valor no modelo"])
        self.assertEqual(len(so_modelo), 1)
        self.assertEqual(so_modelo[0]["Fornecedor"], "Camila Barbosa Tannure")

    def test_soma_linhas_duplicadas_do_modelo(self):
        modelo = [
            {"linha_origem": 30, "Fornecedor": "Receita Federal", "Histórico": "FGTS  ", "Valor": 951.39},
            {"linha_origem": 31, "Fornecedor": "Receita Federal", "Histórico": "FGTS  ", "Valor": 707.20},
        ]
        nova = [
            {"linha_origem": 31, "Fornecedor": "Receita Federal", "Histórico": "FGTS  ", "Valor": 804.54},
        ]
        relacionadas, so_modelo = rd.relacionar(nova, modelo)
        self.assertEqual(relacionadas[0]["Valor no modelo"], 1658.59)
        self.assertEqual(so_modelo, [])
        self.assertIn("2 linhas", relacionadas[0]["Observação"])

    def test_categoria_do_modelo_em_linha_casada(self):
        modelo = [{"linha_origem": 20, "Fornecedor": "Henrique Vilarino - Corretor", "Histórico": "Aluguel Galpão", "Valor": 3454.47}]
        nova = [{"linha_origem": 26, "Fornecedor": "Henrique Vilarino - Corretor", "Histórico": "Aluguel Galpão", "Valor": 3454.47}]
        relacionadas, _ = rd.relacionar(nova, modelo)
        self.assertEqual(relacionadas[0]["Categoria"], "Aluguel")


class TestLeitura(unittest.TestCase):
    def test_le_modelo_com_cabecalho_e_nova_sem_cabecalho(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            modelo = tmp / "modelo.xlsx"
            nova = tmp / "nova.xlsx"

            wb = Workbook()
            ws = wb.active
            ws.append([None, None, None])
            ws.append(["Fornecedor", "Histórico", "Valor"])
            ws.append(["BDMG", "Empréstimo ", 5920.08])
            ws.append(["Maria Maira", "Salário", 1730])
            wb.save(modelo)

            wb2 = Workbook()
            ws2 = wb2.active
            ws2.append(["BDMG", "Empréstimo ", 5933.24])
            ws2.append(["Assiste/Ocupacional", "Medicina Trabalho", "=75+197.85"])
            ws2.append([None, None, "=SUM(C1:C2)"])
            wb2.save(nova)

            m = rd.ler_linhas(modelo)
            n = rd.ler_linhas(nova)
            self.assertEqual(len(m), 2)
            self.assertEqual(len(n), 2)
            self.assertEqual(n[1]["Valor"], 272.85)

            relacionadas, so_modelo = rd.relacionar(n, m)
            self.assertEqual(relacionadas[0]["Valor no modelo"], 5920.08)
            self.assertEqual(len(so_modelo), 1)


if __name__ == "__main__":
    unittest.main()
