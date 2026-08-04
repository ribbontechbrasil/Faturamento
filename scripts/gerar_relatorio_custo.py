#!/usr/bin/env python3
"""Gera relatório de custo/lucro a partir de Faturamento_RBT."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

CUSTO_SUBSTRATO_M2 = {
    "Couche": 3.30,
    "Bopp": 4.45,
    "Termico": 4.60,
}

CUSTO_TUBETE = {
    1.0: 0.34,
    1.5: 0.42,
    3.0: 0.96,
}

SITUACOES_EXCLUIDAS = {"Cancelada", "Rejeitada", "Denegada"}
SEGMENTOS_ETIQUETA = {"Etiqueta Branca", "Etiqueta Colorida"}
SEGMENTOS_LOOKUP = {"Ribbon", "Suprimentos"}

STATUS_OK = "ok"
STATUS_INCOMPLETO = "custo incompleto"


def br_to_float(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    text = text.replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def norm_code(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if text.lower() == "nan" or text == "":
        return None
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text.upper()


# Número com milhar BR (1.500) ou inteiro/decimal simples — evita capturar "150" de "1500"
_NUM_INT = r"(?:\d{1,3}(?:\.\d{3})+|\d+)"
_NUM_FLOAT = r"(?:\d{1,3}(?:\.\d{3})+|\d+(?:[.,]\d+)?)"


def parse_int_br(raw: str) -> float:
    """Interpreta quantidade BR: 1.000 -> 1000; 1,5 -> 1.5."""
    raw = raw.strip().replace(" ", "")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
        return float(raw.replace(".", ""))
    return float(raw.replace(",", "."))


def detect_material(text: str) -> str | None:
    u = text.upper()
    if "COUCHE" in u or "COUCHÊ" in u:
        return "Couche"
    if "BOPP" in u:
        return "Bopp"
    if "TÉRMIC" in u or "TERMIC" in u or "THERMAL" in u or "TERMICA" in u:
        return "Termico"
    return None


def detect_tubete(text: str) -> float | None:
    u = text.upper()
    patterns = [
        r'TUB(?:ETE|\.?)\s*([0-9]+(?:[.,][0-9]+)?)\s*(?:["”″]|POLEG(?:ADAS?)?)?',
        r'TUB\.?\s*([0-9]+(?:[.,][0-9]+)?)',
        r'([0-9]+(?:[.,][0-9]+)?)\s*(?:["”″]|POLEG(?:ADAS?)?)',
    ]
    for pat in patterns:
        m = re.search(pat, u)
        if m:
            return float(m.group(1).replace(",", "."))
    m = re.search(r"TUB(?:ETE|\.?)\s*([0-9]+(?:[.,][0-9]+)?)\.", u)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def detect_dimensions_mm(text: str) -> tuple[float | None, float | None]:
    """Retorna (largura_mm, altura_mm). Em AxB, A=largura e B=altura."""
    m = re.search(
        r"DI[AÂ]METRO\s*([0-9]+(?:[.,][0-9]+)?)\s*MM?",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        d = float(m.group(1).replace(",", "."))
        return d, d

    m = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(?:MM)?\s*[xX×]\s*(\d+(?:[.,]\d+)?)",
        text,
    )
    if not m:
        return None, None
    width = float(m.group(1).replace(",", "."))
    height = float(m.group(2).replace(",", "."))
    return width, height


def detect_qtd_rolo(text: str) -> tuple[float | None, str | None]:
    """Retorna (quantidade, unidade) onde unidade é 'un' ou 'm'."""
    u = text.upper()

    # Metragem no rolo (M/MT, sem confundir com MM)
    meter_patterns = [
        rf"(?:ROLO\s*(?:COM|C/?)\s*|RL\s*C/?\s*|C/\s*)({_NUM_FLOAT})\s*(?:MT|MTS|METROS?)\b",
        rf"(?:ROLO\s*(?:COM|C/?)\s*|RL\s*C/?\s*|C/\s*)({_NUM_FLOAT})\s*M(?!M)\b",
        rf"\b({_NUM_FLOAT})\s*(?:MT|MTS|METROS?)\b",
        rf"-\s*({_NUM_FLOAT})\s*M(?!M)\b",
        rf"\b({_NUM_FLOAT})M(?!M)\b",
    ]
    for pat in meter_patterns:
        m = re.search(pat, u)
        if m:
            return parse_int_br(m.group(1)), "m"

    # Quantidade de etiquetas no rolo
    unit_patterns = [
        rf"ROLO\s*(?:COM|C/?)\s*({_NUM_INT})\s*(?:UN(?:IDADES|D)?|ET(?:I)?QUETAS?)?",
        rf"RL\s*C/?\s*({_NUM_INT})\s*(?:UN(?:IDADES|D)?|ET(?:I)?QUETAS?)?",
        rf"({_NUM_INT})\s*ET(?:I)?QUETAS?\s*P/?ROLO",
        rf"ROLO\s*COM\s*({_NUM_INT})\s*ET(?:I)?QUETAS?",
        rf"C/\s*({_NUM_INT})\s*(?:UN(?:IDADES|D)?|ET(?:I)?QUETAS?)\b",
    ]
    for pat in unit_patterns:
        m = re.search(pat, u)
        if m:
            return parse_int_br(m.group(1)), "un"
    return None, None


def parse_etiqueta(descricao: str) -> dict:
    text = "" if descricao is None or (isinstance(descricao, float) and pd.isna(descricao)) else str(descricao)
    material = detect_material(text)
    tubete = detect_tubete(text)
    largura, altura = detect_dimensions_mm(text)
    qtd_raw, qtd_tipo = detect_qtd_rolo(text)

    nr_etiquetas = None
    area_etiqueta_m2 = None
    area_rolo_m2 = None
    custo_substrato = None
    custo_tubete = None
    custo_material = None
    custo_unitario_rolo = None
    pendencias: list[str] = []

    if largura is None or altura is None:
        pendencias.append("dimensao")
    else:
        # Área em m²: ((L+6mm) * (A+6mm)) / 1_000_000
        area_etiqueta_m2 = ((largura + 6.0) * (altura + 6.0)) / 1_000_000.0

    if material is None:
        pendencias.append("material")
    else:
        custo_substrato = CUSTO_SUBSTRATO_M2[material]

    if tubete is None:
        pendencias.append("tubete")
    elif tubete not in CUSTO_TUBETE:
        pendencias.append(f"tubete_sem_preco({tubete})")
    else:
        custo_tubete = CUSTO_TUBETE[tubete]

    if qtd_raw is None or qtd_tipo is None:
        pendencias.append("qtd_rolo")
    elif qtd_tipo == "un":
        nr_etiquetas = qtd_raw
    elif altura is None:
        pendencias.append("qtd_rolo_m_sem_altura")
    else:
        # metragem / (altura + 3 mm), convertendo altura+3 para metros
        passo_m = (altura + 3.0) / 1000.0
        if passo_m <= 0:
            pendencias.append("altura_invalida")
        else:
            nr_etiquetas = qtd_raw / passo_m

    if (
        area_etiqueta_m2 is not None
        and nr_etiquetas is not None
        and custo_substrato is not None
        and custo_tubete is not None
    ):
        area_rolo_m2 = area_etiqueta_m2 * nr_etiquetas
        custo_material = area_rolo_m2 * custo_substrato
        custo_unitario_rolo = custo_material + custo_tubete
    else:
        if not pendencias:
            pendencias.append("calculo")

    return {
        "material": material,
        "tubete_pol": tubete,
        "largura_mm": largura,
        "altura_mm": altura,
        "qtd_rolo_raw": qtd_raw,
        "qtd_rolo_tipo": qtd_tipo,
        "nr_etiquetas_rolo": nr_etiquetas,
        "area_etiqueta_m2": area_etiqueta_m2,
        "area_rolo_m2": area_rolo_m2,
        "custo_substrato_m2": custo_substrato,
        "custo_tubete": custo_tubete,
        "custo_material_rolo": custo_material,
        "custo_rolo": custo_unitario_rolo,
        "pendencias": ";".join(pendencias),
        "completo": custo_unitario_rolo is not None,
    }


def custo_unitario_etiqueta_nf(
    custo_rolo: float,
    nr_etiquetas: float | None,
    unidade_nf: str | None,
    valor_unitario: float | None,
) -> tuple[float, str]:
    """Define se a NF cobra por rolo ou por etiqueta individual.

    Se o preço unitário da NF for < 5% do custo do rolo (ex.: R$ 0,33),
    assume venda por etiqueta e rateia o custo do rolo.
    Caso contrário, assume venda por rolo.
    """
    del unidade_nf  # reservado para regras futuras
    if (
        valor_unitario is not None
        and nr_etiquetas
        and nr_etiquetas > 0
        and custo_rolo > 0
        and valor_unitario < custo_rolo * 0.05
    ):
        return custo_rolo / nr_etiquetas, "etiqueta"
    return custo_rolo, "rolo"


def load_custos_ultimo(path: Path) -> pd.Series:
    cus = pd.read_excel(path, sheet_name="Custos_RS")
    cus["code"] = cus["Item"].map(norm_code)
    cus["custo"] = cus["Custo Unit."].map(br_to_float)
    cus = cus.dropna(subset=["code", "custo"])
    # Última ocorrência na aba
    return cus.groupby("code", sort=False)["custo"].last()


def load_segmento(path: Path) -> pd.DataFrame:
    seg = pd.read_excel(path, sheet_name="Segmento")
    seg["code"] = seg["Código"].map(norm_code)
    seg = seg.dropna(subset=["code"]).drop_duplicates("code", keep="last")
    return seg[["code", "Segmento"]]


def calcular_relatorio(path: Path) -> pd.DataFrame:
    fat = pd.read_excel(path, sheet_name="Faturamento")
    custos = load_custos_ultimo(path)
    segmento = load_segmento(path)

    fat = fat.copy()
    fat["code"] = fat["Código"].map(norm_code)
    fat["quantidade_num"] = fat["Quantidade"].map(br_to_float)
    fat["valor_unitario_num"] = fat["Valor unitário"].map(br_to_float)
    fat["valor_total_num"] = fat["Valor total"].map(br_to_float)
    fat = fat.merge(segmento, on="code", how="left")

    # Excluir canceladas/rejeitadas/denegadas
    fat = fat[~fat["Situação"].isin(SITUACOES_EXCLUIDAS)].copy()

    rows = []
    for _, r in fat.iterrows():
        segmento_nome = r.get("Segmento")
        if pd.isna(segmento_nome):
            # Fallback por descrição
            desc_u = str(r.get("Descrição", "")).upper()
            if "ETIQUETA" in desc_u or "ETIQ" in desc_u:
                segmento_nome = "Etiqueta Branca"
            elif "RIBBON" in desc_u or "FITA" in desc_u:
                segmento_nome = "Ribbon"
            else:
                segmento_nome = "Outro"

        qtd = r["quantidade_num"]
        venda = r["valor_total_num"]
        valor_unit = r["valor_unitario_num"]
        custo_unit = None
        base_custo = None
        pendencias = []
        detalhe = {}

        is_etiqueta = segmento_nome in SEGMENTOS_ETIQUETA or (
            segmento_nome == "Outro"
            and "ETIQUETA" in str(r.get("Descrição", "")).upper()
        )

        if is_etiqueta:
            detalhe = parse_etiqueta(r.get("Descrição"))
            if not detalhe["completo"]:
                pendencias.append(detalhe["pendencias"] or "etiqueta")
            else:
                custo_unit, base_custo = custo_unitario_etiqueta_nf(
                    detalhe["custo_rolo"],
                    detalhe["nr_etiquetas_rolo"],
                    r.get("Unidade"),
                    valor_unit,
                )
        elif segmento_nome in SEGMENTOS_LOOKUP:
            code = r["code"]
            if code is None:
                pendencias.append("codigo")
            elif code not in custos.index:
                pendencias.append("custo_rs")
            else:
                custo_unit = float(custos.loc[code])
                base_custo = "custos_rs"
        else:
            # Ativo/Revenda/Outro: sem regra de custo definida
            code = r["code"]
            if code is not None and code in custos.index:
                custo_unit = float(custos.loc[code])
                base_custo = "custos_rs"
            else:
                pendencias.append("segmento_sem_regra")

        if qtd is None:
            pendencias.append("quantidade_nf")
        if venda is None:
            pendencias.append("valor_venda")

        completo = custo_unit is not None and qtd is not None and venda is not None
        if completo:
            custo_total = custo_unit * qtd
            frete = venda * 0.03
            imposto = venda * 0.092
            venda_liquida = venda - custo_total - frete - imposto
            perc_lucro = (venda_liquida / custo_total) if custo_total else None
            status = STATUS_OK
            pendencia_txt = ""
        else:
            custo_total = None
            frete = venda * 0.03 if venda is not None else None
            imposto = venda * 0.092 if venda is not None else None
            venda_liquida = None
            perc_lucro = None
            status = STATUS_INCOMPLETO
            pendencia_txt = ";".join(pendencias)

        rows.append(
            {
                "Número": r.get("Número"),
                "Nome": r.get("Nome"),
                "Data de emissão": r.get("Data de emissão"),
                "Situação": r.get("Situação"),
                "UF": r.get("UF"),
                "Código": r.get("Código"),
                "Descrição": r.get("Descrição"),
                "Segmento": segmento_nome,
                "Unidade": r.get("Unidade"),
                "Quantidade": qtd,
                "Valor unitário": valor_unit,
                "Valor total venda": venda,
                "Material": detalhe.get("material"),
                "Largura_mm": detalhe.get("largura_mm"),
                "Altura_mm": detalhe.get("altura_mm"),
                "Area_etiqueta_m2": detalhe.get("area_etiqueta_m2"),
                "Qtd_rolo_raw": detalhe.get("qtd_rolo_raw"),
                "Qtd_rolo_tipo": detalhe.get("qtd_rolo_tipo"),
                "Nr_etiquetas_rolo": detalhe.get("nr_etiquetas_rolo"),
                "Area_rolo_m2": detalhe.get("area_rolo_m2"),
                "Custo_substrato_m2": detalhe.get("custo_substrato_m2"),
                "Tubete_pol": detalhe.get("tubete_pol"),
                "Custo_tubete": detalhe.get("custo_tubete"),
                "Custo_material_rolo": detalhe.get("custo_material_rolo"),
                "Custo_rolo": detalhe.get("custo_rolo"),
                "Base custo unitário": base_custo,
                "Custo unitário item": custo_unit,
                "Custo total item": custo_total,
                "Frete (3%)": frete,
                "Imposto (9,2%)": imposto,
                "Venda líquida": venda_liquida,
                "% Lucro": perc_lucro,
                "Status custo": status,
                "Pendências": pendencia_txt,
            }
        )

    return pd.DataFrame(rows)


def resumo(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    ok = (df["Status custo"] == STATUS_OK).sum()
    incompleto = (df["Status custo"] == STATUS_INCOMPLETO).sum()
    by_seg = (
        df.groupby("Segmento", dropna=False)
        .agg(
            itens=("Status custo", "size"),
            ok=("Status custo", lambda s: (s == STATUS_OK).sum()),
            incompleto=("Status custo", lambda s: (s == STATUS_INCOMPLETO).sum()),
            venda_total=("Valor total venda", "sum"),
            custo_total=("Custo total item", "sum"),
            venda_liquida=("Venda líquida", "sum"),
        )
        .reset_index()
    )
    geral = pd.DataFrame(
        [
            {
                "Segmento": "TOTAL",
                "itens": total,
                "ok": ok,
                "incompleto": incompleto,
                "venda_total": df["Valor total venda"].sum(skipna=True),
                "custo_total": df["Custo total item"].sum(skipna=True),
                "venda_liquida": df["Venda líquida"].sum(skipna=True),
            }
        ]
    )
    out = pd.concat([by_seg, geral], ignore_index=True)
    out["cobertura_ok"] = out["ok"] / out["itens"]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera relatório de custo do faturamento RBT")
    parser.add_argument(
        "--input",
        default="Faturamento_RBT (2).xlsx",
        help="Caminho da planilha de origem",
    )
    parser.add_argument(
        "--output",
        default="Relatorio_Custo_Faturamento_RBT.xlsx",
        help="Caminho do relatório gerado",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    df = calcular_relatorio(input_path)
    summary = resumo(df)
    incompletos = df[df["Status custo"] == STATUS_INCOMPLETO].copy()

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Relatorio", index=False)
        summary.to_excel(writer, sheet_name="Resumo", index=False)
        incompletos.to_excel(writer, sheet_name="Custo_Incompleto", index=False)

    print(f"Relatório gerado: {output_path}")
    print(summary.to_string(index=False))
    print(f"\nLinhas no relatório: {len(df)}")
    print(f"OK: {(df['Status custo'] == STATUS_OK).sum()}")
    print(f"Custo incompleto: {(df['Status custo'] == STATUS_INCOMPLETO).sum()}")

    # Gera também o dashboard HTML ao lado do Excel
    try:
        import sys

        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from gerar_dashboard_html import build_rows, render_html

        dts = pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce")
        if dts.notna().any():
            periodo = f"{dts.min().strftime('%d/%m/%Y')} a {dts.max().strftime('%d/%m/%Y')}"
        else:
            periodo = "Período não disponível"
        html_path = output_path.with_name("Dashboard_Custo_Faturamento_RBT.html")
        html_path.write_text(render_html(build_rows(df), periodo), encoding="utf-8")
        print(f"Dashboard HTML gerado: {html_path}")
    except Exception as exc:  # pragma: no cover - best effort
        print(f"Aviso: não foi possível gerar o dashboard HTML ({exc})")


if __name__ == "__main__":
    main()
