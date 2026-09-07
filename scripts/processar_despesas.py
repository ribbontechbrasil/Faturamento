#!/usr/bin/env python3
"""Normaliza e categoriza a planilha Despesas_RBT."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

import pandas as pd

FUNCIONARIOS = [
    "augusto",
    "diego",
    "camila",
    "maira",
    "maria maira",
    "juscinei",
    "carlos roberto",
]


def _norm(text) -> str:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    t = str(text).strip().lower()
    t = (
        t.replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return t


def is_funcionario(fornecedor: str) -> bool:
    f = _norm(fornecedor)
    return any(nome in f for nome in FUNCIONARIOS)


def categorizar(fornecedor: str, historico: str) -> tuple[str, str]:
    """Retorna (categoria, subcategoria)."""
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

    if "bdmg" in f or ("emprest" in h and "bdmg" in f):
        return "BDMG – Empréstimo", "Empréstimo"

    if "bdmg" in f or (f.strip() == "bdmg"):
        return "BDMG – Empréstimo", "Empréstimo"

    if "rosa" in f and "emprest" in h:
        return "Empréstimo Rosa Amasiles", "Empréstimo"

    if "aluguel" in h:
        return "Aluguel", "Aluguel"

    if "copasa" in f or h in {"agua", "água"} or h.startswith("agua"):
        return "Água", "Copasa"

    if "cemig" in f or "energia" in h or "luz" == h:
        return "Luz", "Cemig"

    if "bionexo" in f or "portal de compra" in h:
        return "Portal de compra", "Portal de compra"

    if "bling" in f:
        return "Internet/Sistemas", "Software/ERP"

    if h.strip() == "portal":
        if "bionexo" in f:
            return "Portal de compra", "Portal de compra"
        return "Internet/Sistemas", "Portal/Sistemas"

    if "internet" in h or "telecom" in f or "vivo" in f or "claro" in f or "oi " in f:
        return "Internet/Sistemas", "Internet"

    if "contab" in h or "om assessoria" in f:
        return "Contabilidade", "Honorários"

    if "difal negoci" in h:
        return "Difal Negociação", "SEF/MG"

    if "difal antecip" in h or "dival antecip" in h:
        return "Difal Antecipação", "SEF/MG"

    # Simples Nacional já entra no dashboard via imposto sobre a venda (9,2%)
    if "simples nacional" in h:
        return "", "EXCLUIR"

    if "medicina" in h or "ocupacional" in h:
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

    if h.strip() == "epi" or "epi" == h:
        return "Pessoal", "EPI"

    if "diferenca salarial" in h:
        return "Pessoal", "Salário"

    if "fgts" in h or "inss" in h or "dctfweb" in h:
        return "Pessoal", "Encargos sociais (INSS/FGTS)"

    if "manutenc" in h or "reparo" in h or "limpeza" in h or "desinfet" in h:
        return "Manutenção e reparos", "Manutenção/Limpeza"

    if "frete" in h or "correios" in h or "celular" in h:
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
        if "salario" in h or "venc" in h or "dias trabalhados" in h or re.search(r"\bjun\b|\bjul\b", h):
            return "Pessoal", "Salário"
        return "Pessoal", "Salário"

    return "Outros", "Outros"


def competencia_mes(liquidacao, historico: str) -> str | None:
    if pd.notna(liquidacao):
        dt = pd.to_datetime(liquidacao, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m")

    h = _norm(historico)
    # Ex.: "Pro-labore Jun 26", "Salário Jun/26", "FGTS - 06/2026"
    m = re.search(r"\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*\s*/?\s*(\d{2,4})", h)
    meses = {
        "jan": 1,
        "fev": 2,
        "mar": 3,
        "abr": 4,
        "mai": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "set": 9,
        "out": 10,
        "nov": 11,
        "dez": 12,
    }
    if m:
        mes = meses[m.group(1)[:3]]
        ano = int(m.group(2))
        if ano < 100:
            ano += 2000
        return f"{ano:04d}-{mes:02d}"

    m2 = re.search(r"\b(\d{2})/(\d{4})\b", h)
    if m2:
        return f"{int(m2.group(2)):04d}-{int(m2.group(1)):02d}"

    return None


def competencia_from_filename(path: Path) -> str:
    """Infere o mês-caixa pelo nome do arquivo (Ago 2026 → 2026-08)."""
    name = _norm(path.name)
    meses = {
        "jan": 1,
        "fev": 2,
        "mar": 3,
        "abr": 4,
        "mai": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "set": 9,
        "out": 10,
        "nov": 11,
        "dez": 12,
    }
    m = re.search(
        r"\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*\s*/?-?\s*(\d{2,4})",
        name,
    )
    if m:
        mes = meses[m.group(1)[:3]]
        ano = int(m.group(2))
        if ano < 100:
            ano += 2000
        return f"{ano:04d}-{mes:02d}"
    return "2026-07"


def _ler_despesas_raw(path: Path) -> pd.DataFrame:
    """Aceita planilha com cabeçalho (julho) ou 3 colunas sem cabeçalho (agosto)."""
    raw0 = pd.read_excel(path, header=None)
    if raw0.empty:
        return raw0

    def row_text(idx: int) -> str:
        if idx >= len(raw0):
            return ""
        return " ".join(_norm(v) for v in raw0.iloc[idx].tolist())

    if "fornecedor" in row_text(0):
        raw = pd.read_excel(path, header=0)
    elif "fornecedor" in row_text(1):
        raw = pd.read_excel(path, header=1)
    else:
        raw = raw0.copy()
        cols = list(raw.columns)
        rename = {cols[0]: "Fornecedor"}
        if len(cols) > 1:
            rename[cols[1]] = "Histórico"
        if len(cols) > 2:
            rename[cols[2]] = "Pago"
        raw = raw.rename(columns=rename)
    raw.columns = [str(c).strip() for c in raw.columns]
    return raw


def processar(path: Path, competencia_padrao: str | None = None) -> pd.DataFrame:
    raw = _ler_despesas_raw(path)
    raw.columns = [str(c).strip() for c in raw.columns]
    padrao = competencia_padrao or competencia_from_filename(path)
    # Aceita variações de cabeçalho
    colmap = {}
    for c in raw.columns:
        cl = _norm(c)
        if "fornecedor" in cl:
            colmap[c] = "Fornecedor"
        elif "historico" in cl:
            colmap[c] = "Histórico"
        elif "liquid" in cl:
            colmap[c] = "Liquidação"
        elif "situacao" in cl:
            colmap[c] = "Situação"
        elif cl in {"pago", "valor"}:
            colmap[c] = "Pago"
    raw = raw.rename(columns=colmap)
    required = ["Fornecedor", "Histórico", "Pago"]
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise ValueError(f"Colunas ausentes na planilha de despesas: {missing}")
    if "Liquidação" not in raw.columns:
        raw["Liquidação"] = pd.NaT
    if "Situação" not in raw.columns:
        raw["Situação"] = ""

    rows = []
    for i, r in raw.iterrows():
        valor = r.get("Pago")
        if pd.isna(valor):
            continue
        try:
            valor_f = float(valor)
        except (TypeError, ValueError):
            continue
        forn = "" if pd.isna(r.get("Fornecedor")) else str(r.get("Fornecedor")).strip()
        hist = "" if pd.isna(r.get("Histórico")) else str(r.get("Histórico")).strip()
        if not forn and not hist:
            continue
        # Histórico às vezes vem como data (Cemig/Copasa)
        if isinstance(r.get("Histórico"), (pd.Timestamp,)) or (
            hist and re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", hist)
        ):
            if "cemig" in _norm(forn):
                hist = "Energia elétrica"
            elif "copasa" in _norm(forn):
                hist = "Água/esgoto"
        cat, sub = categorizar(forn, hist)
        if sub == "EXCLUIR" or not cat:
            continue
        liq = pd.to_datetime(r.get("Liquidação"), errors="coerce")
        comp_ref = competencia_mes(liq, str(r.get("Histórico")))
        # Mês do caixa/dashboard: data de liquidação; sem data entra no mês da planilha
        if pd.notna(liq):
            mes_caixa = liq.strftime("%Y-%m")
        else:
            mes_caixa = padrao
        tipo = "investimento" if cat == "Investimento" else "despesa"
        rows.append(
            {
                "id": int(i),
                "Fornecedor": forn,
                "Histórico": hist,
                "Liquidação": None if pd.isna(liq) else liq.strftime("%Y-%m-%d"),
                "Competência": mes_caixa,
                "Competência ref.": comp_ref or mes_caixa,
                "Situação": "" if pd.isna(r.get("Situação")) else str(r.get("Situação")).strip(),
                "Valor": round(valor_f, 2),
                "Categoria": cat,
                "Subcategoria": sub,
                "Tipo": tipo,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Processa Despesas_RBT")
    parser.add_argument(
        "--input",
        default="Despesas_RBT.xlsx",
        help="Planilha de despesas original",
    )
    parser.add_argument(
        "--output",
        default="Despesas_RBT_Normalizadas.xlsx",
        help="Saída normalizada",
    )
    parser.add_argument(
        "--competencia",
        default=None,
        help="Mês-caixa padrão (YYYY-MM) quando a linha não tem data",
    )
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        # tenta upload path comum
        upload = Path("/home/ubuntu/.cursor/projects/workspace/uploads/Despesas_RBT_e025.xlsx")
        if upload.exists():
            shutil.copy2(upload, src)
        else:
            raise SystemExit(f"Arquivo não encontrado: {src}")

    df = processar(src, competencia_padrao=args.competencia)
    out = Path(args.output)
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Despesas", index=False)
        resumo = (
            df.groupby(["Competência", "Categoria"], dropna=False)["Valor"]
            .sum()
            .reset_index()
            .sort_values(["Competência", "Categoria"])
        )
        resumo.to_excel(writer, sheet_name="Resumo", index=False)

    print(f"Despesas processadas: {len(df)} | total R$ {df['Valor'].sum():,.2f}")
    print(df.groupby("Categoria")["Valor"].sum().sort_values(ascending=False).to_string())
    print(f"Salvo em: {out}")


if __name__ == "__main__":
    main()
