#!/usr/bin/env python3
"""Relaciona a planilha nova de despesas com a planilha modelo.

Assunto separado do faturamento: só lê Despesas_RBT.xlsx (modelo) e
Despesas Ago 2026.xlsx (nova) e preenche colunas da nova com o que
existir no modelo (valor de referência, se a linha já existia, categoria).
"""

from __future__ import annotations

import argparse
import html
import re
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

FUNCIONARIOS = [
    "augusto",
    "diego",
    "camila",
    "maira",
    "maria maira",
    "juscinei",
    "carlos roberto",
]

MOEDA = r'_-* #,##0.00_-;\-* #,##0.00_-;_-* "-"??_-;_-@_-'

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
CELL_FONT = Font(name="Calibri", size=10)
MATCH_FILL = PatternFill("solid", fgColor="E2EFDA")
NOVO_FILL = PatternFill("solid", fgColor="FFF2CC")
TOTAL_FILL = PatternFill("solid", fgColor="D6DCE4")
THIN = Border(
    left=Side(style="thin", color="BDD7EE"),
    right=Side(style="thin", color="BDD7EE"),
    top=Side(style="thin", color="BDD7EE"),
    bottom=Side(style="thin", color="BDD7EE"),
)


def _norm(text) -> str:
    if text is None:
        return ""
    t = str(text).strip().lower()
    trans = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüç",
        "aaaaaeeeeiiiiooooouuuuc",
    )
    t = t.translate(trans)
    t = re.sub(r"\s+", " ", t)
    return t


def chave(fornecedor: str, historico: str) -> tuple[str, str]:
    return (_norm(fornecedor), _norm(historico))


def is_funcionario(fornecedor: str) -> bool:
    f = _norm(fornecedor)
    return any(nome in f for nome in FUNCIONARIOS)


def categorizar(fornecedor: str, historico: str) -> tuple[str, str]:
    """Mesma lógica da planilha modelo (despesas, não faturamento)."""
    f = _norm(fornecedor)
    h = _norm(historico)

    if "invest" in h:
        return "Investimento", "Investimento"
    if "pro-labore" in h or "pro labore" in h or "prolabore" in h:
        return "Pró-labore", "Pró-labore"
    if "visita cliente" in h or "despesas comerciais" in h or "despesa comercial" in h:
        return "Visita cliente", "Despesas comerciais"
    if "comiss" in h and "vend" in h:
        return "Comissão de vendas", "Comissão de vendas"
    if h.strip() in {"comissao", "comissão"} or h.startswith("comissao") or h.startswith("comissão"):
        return "Comissão de vendas", "Comissão de vendas"
    if "bdmg" in f:
        return "BDMG – Empréstimo", "Empréstimo"
    if "rosa" in f and "emprest" in h:
        return "Empréstimo Rosa Amasiles", "Empréstimo"
    if "aluguel" in h:
        return "Aluguel", "Aluguel"
    if "copasa" in f or h in {"agua", "água"} or h.startswith("agua"):
        return "Água", "Copasa"
    if "cemig" in f or "energia" in h or h == "luz":
        return "Luz", "Cemig"
    if "bionexo" in f or "portal de compra" in h:
        return "Portal de compra", "Portal de compra"
    if "bling" in f:
        return "Internet/Sistemas", "Software/ERP"
    if h.strip() == "portal":
        return "Internet/Sistemas", "Portal/Sistemas"
    if "internet" in h or "enx" in f:
        return "Internet/Sistemas", "Internet"
    if "contab" in h or "om assessoria" in f:
        return "Contabilidade", "Honorários"
    if "difal negoci" in h:
        return "Difal Negociação", "SEF/MG"
    if "difal antecip" in h or "dival antecip" in h:
        return "Difal Antecipação", "SEF/MG"
    if "simples nacional" in h:
        return "", "EXCLUIR"
    if "medicina" in h or "ocupacional" in f or "assiste" in f:
        return "Pessoal", "Medicina do trabalho"
    if "designer" in h:
        return "Serviços", "Designer"
    if "certificado" in h:
        return "Outros", "Certificado"
    if "cliche" in h:
        return "Produção", "Clichê"
    if "seguro" in h:
        return "Pessoal", "Seguro de vida"
    if h.strip() == "tinta" or h.startswith("tinta"):
        return "Produção", "Tinta"
    if h.strip() == "epi":
        return "Pessoal", "EPI"
    if "diferenca salarial" in h:
        return "Pessoal", "Salário"
    if "fgts" in h or "inss" in h or "dctfweb" in h:
        return "Pessoal", "Encargos sociais (INSS/FGTS)"
    if "manutenc" in h or "reparo" in h or "limpeza" in h or "desinfet" in h:
        return "Manutenção e reparos", "Manutenção/Limpeza"
    if "frete" in h or "correios" in h:
        return "Outros", "Frete/Diversos"
    if is_funcionario(fornecedor):
        if "cesta" in h:
            return "Pessoal", "Cesta básica"
        if "vale transporte" in h or "vale-transporte" in h:
            return "Pessoal", "Vale transporte"
        if "ferias" in h:
            return "Pessoal", "Salário/Férias"
        if "rescis" in h:
            return "Pessoal", "Salário/Rescisão"
        if "salario" in h:
            return "Pessoal", "Salário"
        return "Pessoal", "Salário"
    return "Outros", "Outros"


def _eval_simples(value):
    """Avalia fórmula aritmética simples (=75+197.85); senão devolve o valor."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, str):
        return None
    s = value.strip()
    if s.startswith("="):
        expr = s[1:].replace(" ", "")
        if re.fullmatch(r"[\d.+\-*/()]+", expr) and not re.search(r"[A-Za-z]", expr):
            try:
                return float(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307
            except Exception:
                return None
        return None
    try:
        return float(s.replace(".", "").replace(",", ".")) if s.count(",") == 1 and s.count(".") >= 1 else float(s.replace(",", "."))
    except ValueError:
        return None


def _parece_cabecalho(a, b, c) -> bool:
    return "fornecedor" in _norm(a) and "historico" in _norm(b)


def _parece_total(a, b, c) -> bool:
    if a or b:
        return False
    if isinstance(c, str) and c.strip().upper().startswith("=SUM"):
        return True
    return False


def ler_linhas(path: Path) -> list[dict]:
    wb = load_workbook(path, data_only=False)
    ws = wb.active
    linhas = []
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=3, values_only=True), 1):
        a, b, c = (row + (None, None, None))[:3]
        if a is None and b is None and c is None:
            continue
        if _parece_cabecalho(a, b, c):
            continue
        if _parece_total(a, b, c):
            continue
        valor = _eval_simples(c)
        if valor is None:
            continue
        forn = "" if a is None else str(a).strip()
        hist = "" if b is None else str(b).strip()
        if not forn and not hist:
            continue
        linhas.append(
            {
                "linha_origem": i,
                "Fornecedor": forn,
                "Histórico": hist,
                "Valor": round(float(valor), 2),
            }
        )
    return linhas


def indice_modelo(linhas: list[dict]) -> dict[tuple[str, str], list[dict]]:
    idx: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in linhas:
        idx[chave(r["Fornecedor"], r["Histórico"])].append(r)
    return idx


def relacionar(nova: list[dict], modelo: list[dict]) -> list[dict]:
    idx = indice_modelo(modelo)
    usados: set[int] = set()
    saida = []
    for r in nova:
        k = chave(r["Fornecedor"], r["Histórico"])
        hits = idx.get(k, [])
        cat, sub = categorizar(r["Fornecedor"], r["Histórico"])
        if hits:
            valor_modelo = round(sum(h["Valor"] for h in hits), 2)
            for h in hits:
                usados.add(id(h))
            relacao = "Encontrado no modelo"
            if len(hits) > 1:
                obs = f"{len(hits)} linhas no modelo somadas"
            else:
                obs = f"Modelo linha {hits[0]['linha_origem']}"
        else:
            valor_modelo = None
            relacao = "Novo (não está no modelo)"
            obs = "Preencher só com a planilha nova"
        saida.append(
            {
                **r,
                "Valor no modelo": valor_modelo,
                "Relação": relacao,
                "Categoria": cat,
                "Subcategoria": sub,
                "Observação": obs,
            }
        )
    so_modelo = []
    for r in modelo:
        if id(r) in usados:
            continue
        k = chave(r["Fornecedor"], r["Histórico"])
        # se a chave foi usada, a linha já entrou na soma
        if any(chave(x["Fornecedor"], x["Histórico"]) == k for x in nova):
            continue
        cat, sub = categorizar(r["Fornecedor"], r["Histórico"])
        if sub == "EXCLUIR":
            cat = "Fora do caixa (já no imposto)"
        so_modelo.append(
            {
                **r,
                "Categoria": cat,
                "Subcategoria": sub,
                "Relação": "Só no modelo (não veio em ago/2026)",
            }
        )
    return saida, so_modelo


def _style_header(ws, ncols: int) -> None:
    for col in range(1, ncols + 1):
        cell = ws.cell(1, col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN
    ws.row_dimensions[1].height = 28
    ws.auto_filter.ref = f"A1:{get_column_letter(ncols)}{ws.max_row}"
    ws.freeze_panes = "A2"


def _style_cell(cell, fill=None, money=False) -> None:
    cell.font = CELL_FONT
    cell.border = THIN
    cell.alignment = Alignment(vertical="center")
    if fill is not None:
        cell.fill = fill
    if money:
        cell.number_format = MOEDA
        cell.alignment = Alignment(horizontal="right", vertical="center")


def escrever_xlsx(relacionadas: list[dict], so_modelo: list[dict], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    headers = [
        "Fornecedor",
        "Histórico",
        "Valor ago/2026",
        "Valor no modelo",
        "Relação",
        "Categoria",
        "Subcategoria",
        "Observação",
    ]
    ws = wb.active
    ws.title = "Planilha nova preenchida"
    ws.append(headers)
    for r in relacionadas:
        ws.append(
            [
                r["Fornecedor"],
                r["Histórico"],
                r["Valor"],
                r["Valor no modelo"],
                r["Relação"],
                r["Categoria"],
                r["Subcategoria"],
                r["Observação"],
            ]
        )
    total_row = ws.max_row + 1
    ws.cell(total_row, 1, "TOTAL")
    ws.cell(total_row, 3, f"=SUM(C2:C{total_row-1})")
    ws.cell(total_row, 4, f"=SUM(D2:D{total_row-1})")
    for r_i in range(2, total_row):
        fill = MATCH_FILL if ws.cell(r_i, 5).value == "Encontrado no modelo" else NOVO_FILL
        for c in range(1, 9):
            _style_cell(ws.cell(r_i, c), fill=fill, money=c in (3, 4))
    for c in range(1, 9):
        _style_cell(ws.cell(total_row, c), fill=TOTAL_FILL, money=c in (3, 4))
        ws.cell(total_row, c).font = Font(name="Calibri", bold=True, size=10)
    _style_header(ws, 8)
    widths = [42, 36, 16, 16, 28, 26, 26, 32]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws2 = wb.create_sheet("Só no modelo")
    h2 = ["Fornecedor", "Histórico", "Valor no modelo", "Relação", "Categoria", "Subcategoria"]
    ws2.append(h2)
    for r in so_modelo:
        ws2.append(
            [
                r["Fornecedor"],
                r["Histórico"],
                r["Valor"],
                r["Relação"],
                r["Categoria"],
                r["Subcategoria"],
            ]
        )
    if so_modelo:
        last = ws2.max_row
        for r_i in range(2, last + 1):
            for c in range(1, 7):
                _style_cell(ws2.cell(r_i, c), fill=NOVO_FILL, money=c == 3)
    _style_header(ws2, 6)
    for i, w in enumerate([42, 36, 16, 36, 26, 26], 1):
        ws2.column_dimensions[get_column_letter(i)].width = w

    n_match = sum(1 for r in relacionadas if r["Relação"] == "Encontrado no modelo")
    n_novo = len(relacionadas) - n_match
    ws3 = wb.create_sheet("Resumo")
    ws3.append(["Indicador", "Quantidade / Valor"])
    resumo = [
        ("Linhas na planilha nova", len(relacionadas)),
        ("Encontradas no modelo (células preenchidas)", n_match),
        ("Novas em ago/2026 (sem par no modelo)", n_novo),
        ("Só no modelo (não vieram em ago/2026)", len(so_modelo)),
        ("Total ago/2026", round(sum(r["Valor"] for r in relacionadas), 2)),
        (
            "Total do modelo nas linhas casadas",
            round(sum(r["Valor no modelo"] or 0 for r in relacionadas), 2),
        ),
    ]
    for k, v in resumo:
        ws3.append([k, v])
    for r_i in range(2, ws3.max_row + 1):
        money = r_i >= 6
        for c in range(1, 3):
            _style_cell(ws3.cell(r_i, c), money=money and c == 2)
    _style_header(ws3, 2)
    ws3.column_dimensions["A"].width = 52
    ws3.column_dimensions["B"].width = 22

    wb.save(dest)


def _fmt_brl(valor) -> str:
    if valor is None:
        return "—"
    s = f"{valor:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def escrever_html(relacionadas: list[dict], so_modelo: list[dict], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    n_match = sum(1 for r in relacionadas if r["Relação"] == "Encontrado no modelo")
    n_novo = len(relacionadas) - n_match
    total_ago = sum(r["Valor"] for r in relacionadas)
    total_mod = sum(r["Valor no modelo"] or 0 for r in relacionadas)

    def rows(items, cols):
        out = []
        for r in items:
            cls = "match" if r.get("Relação") == "Encontrado no modelo" else "novo"
            tds = []
            for c in cols:
                v = r.get(c)
                if c in {"Valor", "Valor no modelo"} or "Valor" in c:
                    tds.append(f'<td class="num">{html.escape(_fmt_brl(v))}</td>')
                else:
                    tds.append(f"<td>{html.escape(str(v or ''))}</td>")
            out.append(f'<tr class="{cls}">' + "".join(tds) + "</tr>")
        return "\n".join(out)

    cols_nova = [
        "Fornecedor",
        "Histórico",
        "Valor",
        "Valor no modelo",
        "Relação",
        "Categoria",
        "Subcategoria",
    ]
    page = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Relação de despesas (fora do faturamento)</title>
<style>
:root {{ --ink:#1b2a4a; --muted:#5b6b86; --line:#d7e0ee; --bg:#f4f7fb; }}
* {{ box-sizing:border-box; }}
body {{ font-family: Calibri, Segoe UI, sans-serif; margin:0; background:var(--bg); color:var(--ink); }}
header {{ background:#1F4E79; color:#fff; padding:20px 28px; }}
header h1 {{ margin:0 0 6px; font-size:22px; }}
header p {{ margin:0; opacity:.92; }}
.aviso {{ background:#fff3cd; color:#7a5b00; padding:10px 28px; border-bottom:1px solid #f0e0a0; }}
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; padding:18px 28px; }}
.kpi {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:14px; }}
.kpi b {{ display:block; font-size:22px; }}
.kpi span {{ color:var(--muted); font-size:13px; }}
section {{ padding:0 28px 28px; }}
h2 {{ font-size:18px; margin:8px 0 10px; }}
.legenda {{ margin:0 0 10px; font-size:13px; color:var(--muted); }}
.dot {{ display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:4px; vertical-align:middle; }}
table {{ width:100%; border-collapse:collapse; background:#fff; font-size:13px; }}
th {{ background:#1F4E79; color:#fff; text-align:left; padding:8px; position:sticky; top:0; }}
td {{ padding:7px 8px; border-bottom:1px solid var(--line); }}
td.num {{ text-align:right; white-space:nowrap; }}
tr.match td {{ background:#e2efda; }}
tr.novo td {{ background:#fff2cc; }}
</style>
</head>
<body>
<header>
  <h1>Relação entre a planilha modelo e a planilha nova</h1>
  <p>Despesas administrativas — assunto separado do faturamento da Ribbon Tech</p>
</header>
<div class="aviso">Pasta <b>Despesas/</b>. Não mistura notas, custos de etiqueta nem o dashboard de faturamento.</div>
<div class="kpis">
  <div class="kpi"><b>{len(relacionadas)}</b><span>Linhas na planilha nova</span></div>
  <div class="kpi"><b>{n_match}</b><span>Células preenchidas com o modelo</span></div>
  <div class="kpi"><b>{n_novo}</b><span>Linhas novas (só em ago/2026)</span></div>
  <div class="kpi"><b>{len(so_modelo)}</b><span>Só no modelo (não vieram em agosto)</span></div>
  <div class="kpi"><b>{html.escape(_fmt_brl(total_ago))}</b><span>Total ago/2026</span></div>
  <div class="kpi"><b>{html.escape(_fmt_brl(total_mod))}</b><span>Soma do modelo nas linhas casadas</span></div>
</div>
<section>
  <h2>Planilha nova preenchida</h2>
  <p class="legenda">
    <span class="dot" style="background:#e2efda"></span> Encontrado no modelo — coluna <b>Valor no modelo</b> preenchida
    &nbsp;&nbsp;
    <span class="dot" style="background:#fff2cc"></span> Novo em ago/2026 — sem par no modelo
  </p>
  <table>
    <thead><tr>
      <th>Fornecedor</th><th>Histórico</th><th>Valor ago/2026</th>
      <th>Valor no modelo</th><th>Relação</th><th>Categoria</th><th>Subcategoria</th>
    </tr></thead>
    <tbody>
      {rows(relacionadas, cols_nova)}
    </tbody>
  </table>
</section>
<section>
  <h2>Só no modelo (não vieram em ago/2026)</h2>
  <table>
    <thead><tr>
      <th>Fornecedor</th><th>Histórico</th><th>Valor no modelo</th>
      <th>Relação</th><th>Categoria</th><th>Subcategoria</th>
    </tr></thead>
    <tbody>
      {rows(so_modelo, ["Fornecedor","Histórico","Valor","Relação","Categoria","Subcategoria"])}
    </tbody>
  </table>
</section>
</body>
</html>
"""
    dest.write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Relaciona despesas nova x modelo (fora do faturamento)")
    parser.add_argument("--modelo", default="Despesas_RBT.xlsx")
    parser.add_argument("--nova", default="Despesas Ago 2026.xlsx")
    parser.add_argument("--xlsx", default="Despesas/Despesas_Ago_2026_Relacionada.xlsx")
    parser.add_argument("--html", default="Despesas/relacao_despesas.html")
    args = parser.parse_args()

    modelo = ler_linhas(Path(args.modelo))
    nova = ler_linhas(Path(args.nova))
    relacionadas, so_modelo = relacionar(nova, modelo)
    escrever_xlsx(relacionadas, so_modelo, Path(args.xlsx))
    escrever_html(relacionadas, so_modelo, Path(args.html))
    n_match = sum(1 for r in relacionadas if r["Relação"] == "Encontrado no modelo")
    print(f"Nova: {len(nova)} linhas | Modelo: {len(modelo)} linhas")
    print(f"Preenchidas com o modelo: {n_match}")
    print(f"Novas (sem par): {len(relacionadas) - n_match}")
    print(f"Só no modelo: {len(so_modelo)}")
    print(f"Excel: {args.xlsx}")
    print(f"HTML: {args.html}")


if __name__ == "__main__":
    main()
