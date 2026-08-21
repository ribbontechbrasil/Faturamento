#!/usr/bin/env python3
"""Gera relatório de custo/lucro a partir de Faturamento_RBT."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

# Preços de substrato (R$/m²) — julho/2026
CUSTO_SUBSTRATO_M2 = {
    "Couche": 3.26,  # padrão Colacril ADC5240
    "Bopp": 4.45,  # padrão Protack AP725
    "Termico": 3.60,  # TERMICO 110 X 1000 HM2520
}

CUSTO_SUBSTRATO_PRODUTO = {
    "BOPP PROTACK 120 X 1000 AP725": 4.45,
    "BOPP PROTACK 212 X 1000 AP718": 4.27,
    "BOPP COLACRIL 172 X 2000 ADC3000": 4.57,
    "COUCHE COLACRIL 212 X 1500 ADC5240": 3.26,
    "COUCHE FASSON 212 X 1000 S2045": 3.25,
    "TERMICO 110 X 1000 HM2520": 3.60,
}

# Tubete: (diâmetro_mm, polegadas) → R$
CUSTO_TUBETE = {
    (56, 1.0): 0.1958,
    (95, 1.0): 0.3228,
    (106, 1.0): 0.3594,
    (56, 1.5): 0.2561,
    (106, 1.5): 0.4162,
    (56, 3.0): 0.7231,
    (86, 3.0): 1.1277,
    (106, 3.0): 1.3945,
}
# Aliases de diâmetro próximos (planilha)
CUSTO_TUBETE_ALIAS = {
    (96, 1.0): (95, 1.0),
    (110, 1.0): (106, 1.0),
}

# Fallback quando só há polegadas na descrição (usa série 106 mm)
CUSTO_TUBETE_POR_POL = {
    1.0: CUSTO_TUBETE[(106, 1.0)],
    1.5: CUSTO_TUBETE[(106, 1.5)],
    3.0: CUSTO_TUBETE[(106, 3.0)],
}

SITUACOES_EXCLUIDAS = {"Cancelada", "Rejeitada", "Denegada"}
SEGMENTOS_ETIQUETA = {"Etiqueta Branca", "Etiqueta Colorida"}
SEGMENTOS_LOOKUP = {"Ribbon", "Suprimentos"}

STATUS_OK = "ok"
STATUS_INCOMPLETO = "custo incompleto"

DEFAULT_ETIQUETA_COST_SHEET = "Planilha_calculo_custo_etiquetas_jul26.xlsx"
DEFAULT_FRETE_RIBBON_SHEET = "Ribbon_com_frete_real.xlsx"


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
    text = str(value).strip().replace("\t", "")
    if text.lower() == "nan" or text == "":
        return None
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text.upper()


def code_key(value) -> str | None:
    """Chave de código para matching (ignora pontos/espaços)."""
    c = norm_code(value)
    if c is None:
        return None
    return re.sub(r"[^A-Z0-9/]", "", c)


def norm_nf(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().upper()
    if not text or text == "NAN":
        return None
    text = re.sub(r"^RT", "", text)
    text = text.lstrip("0")
    return text or "0"


def format_nf_4digitos(value) -> str | None:
    """Exibe NF só com 4 dígitos (remove prefixos 00 / RT00)."""
    key = norm_nf(value)
    if key is None:
        return None
    digits = re.sub(r"\D", "", str(key))
    if not digits:
        return None
    # Mantém no máximo o valor numérico; preenche à esquerda até 4 dígitos
    if len(digits) > 4:
        digits = digits[-4:]
    return digits.zfill(4)


def norm_material_key(text: str) -> str:
    t = re.sub(r"\s+", " ", str(text).strip().upper().replace(",", "."))
    t = t.replace("×", "X")
    return t


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


def parse_dimensoes_planilha(text) -> tuple[float | None, float | None, int]:
    """Lê dimensões da planilha: '100 X 70', '2,5 x 10,4', '50 X 40 X 2'."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None, None, 1
    raw = str(text).strip().upper().replace(",", ".")
    m = re.match(
        r"^\s*(\d+(?:\.\d+)?)\s*[X×]\s*(\d+(?:\.\d+)?)\s*[X×]\s*(\d+)\s*$",
        raw,
    )
    if m:
        largura, altura, colunas = float(m.group(1)), float(m.group(2)), int(m.group(3))
    else:
        m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*[X×]\s*(\d+(?:\.\d+)?)\s*$", raw)
        if not m:
            return None, None, 1
        largura, altura, colunas = float(m.group(1)), float(m.group(2)), 1

    # Valores tipicamente em cm na planilha (ex.: 2,5 x 10,4)
    if max(largura, altura) <= 20:
        largura *= 10.0
        altura *= 10.0
    return largura, altura, colunas


def parse_tipo_tubete(text) -> tuple[float | None, float | None]:
    """Planilha usa '3 x 56' (polegada x diâmetro) ou '56 x 3'."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None, None
    raw = str(text).strip().lower().replace(",", ".")
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*$", raw)
    if not m:
        return None, None
    a, b = float(m.group(1)), float(m.group(2))
    # Se o primeiro número é 1/1.5/3 e o segundo é diâmetro grande → pol x diam
    if a in (1.0, 1.5, 3.0) and b >= 20:
        return b, a
    # diam x pol
    if b in (1.0, 1.5, 3.0) and a >= 20:
        return a, b
    # fallback: maior = diâmetro
    if a > b:
        return a, b
    return b, a


def lookup_custo_tubete(diam: float | None, pol: float | None) -> tuple[float | None, str | None]:
    if diam is None or pol is None:
        return None, None
    key = (int(round(diam)), float(pol))
    # normaliza 1.5
    for cand_pol in (pol, float(pol)):
        key = (int(round(diam)), float(cand_pol))
        if key in CUSTO_TUBETE:
            return CUSTO_TUBETE[key], f"{key[0]} x {key[1]:g}"
        if key in CUSTO_TUBETE_ALIAS:
            real = CUSTO_TUBETE_ALIAS[key]
            return CUSTO_TUBETE[real], f"{real[0]} x {real[1]:g}"
    # tenta polegadas exatamente 1, 1.5, 3
    for p in (1.0, 1.5, 3.0):
        if abs(pol - p) < 1e-6:
            key = (int(round(diam)), p)
            if key in CUSTO_TUBETE:
                return CUSTO_TUBETE[key], f"{key[0]} x {key[1]:g}"
            if key in CUSTO_TUBETE_ALIAS:
                real = CUSTO_TUBETE_ALIAS[key]
                return CUSTO_TUBETE[real], f"{real[0]} x {real[1]:g}"
    return None, None


def resolve_custo_substrato(material_nome: str | None, custo_planilha=None) -> tuple[float | None, str | None]:
    if custo_planilha is not None and not (isinstance(custo_planilha, float) and pd.isna(custo_planilha)):
        v = br_to_float(custo_planilha)
        if v is not None:
            return v, (material_nome or "planilha")
    if not material_nome:
        return None, None
    key = norm_material_key(material_nome)
    if key in CUSTO_SUBSTRATO_PRODUTO:
        return CUSTO_SUBSTRATO_PRODUTO[key], key
    # match parcial por código do produto
    for prod, preco in CUSTO_SUBSTRATO_PRODUTO.items():
        token = prod.split()[-1]
        if token in key:
            return preco, prod
    familia = detect_material(material_nome)
    if familia:
        return CUSTO_SUBSTRATO_M2[familia], familia
    return None, None


def calc_custo_etiqueta(
    *,
    largura_mm: float | None,
    altura_mm: float | None,
    colunas: int = 1,
    metragem_total_m: float | None = None,
    qtd_tubetes: float | None = None,
    nr_etiquetas_informado: float | None = None,
    custo_substrato_m2: float | None = None,
    custo_tubete: float | None = None,
    custo_embalagem_rolo: float | None = None,
    material_label: str | None = None,
    tubete_label: str | None = None,
) -> dict:
    """Custo por rolo e total.

    - Área etiqueta: ((L+6)*(A+6))/1e6  (mantida)
    - Metragem em metros; nº etiquetas = metros_por_rolo / ((A+3)/1000)
      (se a planilha informar nº de etiquetas, usa o informado)
    - Nº de rolos = nº de tubetes
    - Sem regra dos 5% (venda por etiqueta vs rolo)
    """
    pendencias: list[str] = []
    area_etiqueta_m2 = None
    nr_etiquetas = None
    metros_por_rolo = None
    area_rolo_m2 = None
    custo_material = None
    custo_rolo = None
    custo_total = None

    if largura_mm is None or altura_mm is None:
        pendencias.append("dimensao")
    else:
        area_etiqueta_m2 = ((largura_mm + 6.0) * (altura_mm + 6.0)) / 1_000_000.0
        if colunas > 1:
            area_etiqueta_m2 *= colunas

    if nr_etiquetas_informado is not None and nr_etiquetas_informado > 0:
        nr_etiquetas = float(nr_etiquetas_informado)
    elif metragem_total_m is not None and qtd_tubetes and qtd_tubetes > 0 and altura_mm is not None:
        metros_por_rolo = float(metragem_total_m) / float(qtd_tubetes)
        passo_m = (altura_mm + 3.0) / 1000.0
        if passo_m <= 0:
            pendencias.append("altura_invalida")
        else:
            nr_etiquetas = metros_por_rolo / passo_m
    elif metragem_total_m is not None and altura_mm is not None:
        # metragem já por rolo
        metros_por_rolo = float(metragem_total_m)
        passo_m = (altura_mm + 3.0) / 1000.0
        if passo_m > 0:
            nr_etiquetas = metros_por_rolo / passo_m
        else:
            pendencias.append("altura_invalida")
    else:
        pendencias.append("qtd_rolo")

    if custo_substrato_m2 is None:
        pendencias.append("material")
    if custo_tubete is None:
        pendencias.append("tubete")
    if qtd_tubetes is None or qtd_tubetes <= 0:
        pendencias.append("qtd_tubetes")

    if (
        area_etiqueta_m2 is not None
        and nr_etiquetas is not None
        and custo_substrato_m2 is not None
        and custo_tubete is not None
    ):
        area_rolo_m2 = area_etiqueta_m2 * nr_etiquetas
        custo_material = area_rolo_m2 * float(custo_substrato_m2)
        emb = float(custo_embalagem_rolo or 0.0)
        custo_rolo = custo_material + float(custo_tubete) + emb
        if qtd_tubetes and qtd_tubetes > 0:
            custo_total = custo_rolo * float(qtd_tubetes)
    elif not pendencias:
        pendencias.append("calculo")

    return {
        "material": material_label,
        "tubete_pol": None,
        "tubete_label": tubete_label,
        "largura_mm": largura_mm,
        "altura_mm": altura_mm,
        "colunas": colunas,
        "qtd_rolo_raw": metragem_total_m,
        "qtd_rolo_tipo": "m" if metragem_total_m is not None else None,
        "metros_por_rolo": metros_por_rolo,
        "nr_etiquetas_rolo": nr_etiquetas,
        "area_etiqueta_m2": area_etiqueta_m2,
        "area_rolo_m2": area_rolo_m2,
        "custo_substrato_m2": custo_substrato_m2,
        "custo_tubete": custo_tubete,
        "custo_embalagem_rolo": float(custo_embalagem_rolo or 0.0) if custo_embalagem_rolo is not None else None,
        "custo_material_rolo": custo_material,
        "custo_rolo": custo_rolo,
        "qtd_tubetes": qtd_tubetes,
        "custo_total_planilha": custo_total,
        "pendencias": ";".join(pendencias),
        "completo": custo_rolo is not None and qtd_tubetes is not None and qtd_tubetes > 0,
    }


def parse_etiqueta(descricao: str) -> dict:
    """Fallback por descrição (itens sem linha na planilha de cálculo)."""
    text = "" if descricao is None or (isinstance(descricao, float) and pd.isna(descricao)) else str(descricao)
    material = detect_material(text)
    tubete_pol = detect_tubete(text)
    largura, altura = detect_dimensions_mm(text)
    qtd_raw, qtd_tipo = detect_qtd_rolo(text)

    custo_substrato = CUSTO_SUBSTRATO_M2.get(material) if material else None
    custo_tubete = CUSTO_TUBETE_POR_POL.get(tubete_pol) if tubete_pol is not None else None
    tubete_label = f"106 x {tubete_pol:g}" if tubete_pol is not None and custo_tubete is not None else None

    nr_informado = qtd_raw if qtd_tipo == "un" else None
    metragem = qtd_raw if qtd_tipo == "m" else None

    # Sem quantidade de tubetes na descrição: calcula só custo do rolo (qtd=1) e deixa NF aplicar qtd
    detalhe = calc_custo_etiqueta(
        largura_mm=largura,
        altura_mm=altura,
        colunas=1,
        metragem_total_m=metragem,
        qtd_tubetes=1.0,  # unitário por rolo; total virá da NF
        nr_etiquetas_informado=nr_informado,
        custo_substrato_m2=custo_substrato,
        custo_tubete=custo_tubete,
        custo_embalagem_rolo=0.0,
        material_label=material,
        tubete_label=tubete_label,
    )
    detalhe["tubete_pol"] = tubete_pol
    detalhe["qtd_rolo_raw"] = qtd_raw
    detalhe["qtd_rolo_tipo"] = qtd_tipo
    # Para fallback, completo = custo do rolo ok (qtd NF multiplica depois)
    if detalhe["custo_rolo"] is not None:
        detalhe["completo"] = True
        detalhe["pendencias"] = ""
        detalhe["qtd_tubetes"] = None  # usar quantidade da NF
        detalhe["custo_total_planilha"] = None
    return detalhe


def custo_unitario_etiqueta_nf(
    custo_rolo: float,
    nr_etiquetas: float | None = None,
    unidade_nf: str | None = None,
    valor_unitario: float | None = None,
) -> tuple[float, str]:
    """Define o custo unitário na NF para itens sem planilha de cálculo.

    Na planilha jul/26 a regra dos 5% foi cancelada (nº de rolos = nº de tubetes).
    No fallback por descrição, ainda detectamos NF vendida por etiqueta quando o
    preço unitário é < 5% do custo do rolo — evita multiplicar custo de rolo por
    milhares de etiquetas em dados históricos.
    """
    del unidade_nf
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


def load_planilha_etiquetas(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    df = pd.read_excel(path)
    df = df.copy()
    df["_nf_key"] = df["NF"].map(norm_nf)
    df["_qtd_tubetes"] = df["Quantidade tubetes"].map(br_to_float)
    df["_metragem"] = df["metragem do rolo - m"].map(br_to_float)
    df["_nr_etiquetas"] = df["quantidade etiquetas por rolo"].map(br_to_float)
    df["_custo_mat"] = df["Custo do material"].map(br_to_float)
    df["_custo_emb_rolo"] = df["custo embalagem por rolo"].map(br_to_float)
    # Frete real por item (coluna "frete" da planilha jul/26)
    frete_col = next((c for c in df.columns if str(c).strip().lower() == "frete"), None)
    if frete_col is not None:
        df["_frete"] = df[frete_col].map(br_to_float)
    else:
        df["_frete"] = None
    dims = df["dimensões"].map(parse_dimensoes_planilha)
    df["_largura"] = [d[0] for d in dims]
    df["_altura"] = [d[1] for d in dims]
    df["_colunas"] = [d[2] for d in dims]
    tubs = df["tipo tubete"].map(parse_tipo_tubete)
    df["_tub_diam"] = [t[0] for t in tubs]
    df["_tub_pol"] = [t[1] for t in tubs]
    return df


def match_planilha_etiqueta(planilha: pd.DataFrame, nf_key: str | None, qtd_nf: float | None, descricao: str) -> pd.Series | None:
    if planilha is None or planilha.empty or not nf_key:
        return None
    cands = planilha[planilha["_nf_key"] == nf_key]
    if cands.empty:
        return None

    desc = str(descricao or "").upper().replace(",", ".")
    best_idx = None
    best_score = -1
    for idx, row in cands.iterrows():
        if planilha.at[idx, "_used"]:
            continue
        score = 0
        qtub = row["_qtd_tubetes"]
        if qtd_nf is not None and qtub is not None and abs(qtd_nf - qtub) < 0.01:
            score += 5
        L, A = row["_largura"], row["_altura"]
        if L is not None and A is not None:
            # tenta mm e cm na descrição
            variants = [
                (L, A),
                (L / 10.0, A / 10.0) if max(L, A) >= 20 else (L, A),
            ]
            for lw, ah in variants:
                lw_s = f"{lw:g}"
                ah_s = f"{ah:g}"
                if re.search(rf"{re.escape(lw_s)}\s*[X×]\s*{re.escape(ah_s)}", desc):
                    score += 3
                    break
        if score > best_score:
            best_score = score
            best_idx = idx
    if best_idx is None or best_score <= 0:
        # se só há uma candidata não usada na NF, aceita
        livres = cands[~cands.index.map(lambda i: bool(planilha.at[i, "_used"]))]
        if len(livres) == 1:
            best_idx = livres.index[0]
            best_score = 1
        else:
            return None
    planilha.at[best_idx, "_used"] = True
    return planilha.loc[best_idx]


def detalhe_from_planilha(row: pd.Series) -> dict:
    custo_sub, mat_label = resolve_custo_substrato(row.get("Material"), row.get("_custo_mat"))
    if mat_label is None:
        mat_label = None if pd.isna(row.get("Material")) else str(row.get("Material"))
    custo_tub, tub_label = lookup_custo_tubete(row.get("_tub_diam"), row.get("_tub_pol"))
    if tub_label is None and not pd.isna(row.get("tipo tubete")):
        tub_label = str(row.get("tipo tubete"))

    # Preferir metragem (regra do usuário); se o nº de etiquetas da planilha
    # divergir pouco, ainda usamos o informado quando a metragem não fechar.
    detalhe = calc_custo_etiqueta(
        largura_mm=row.get("_largura"),
        altura_mm=row.get("_altura"),
        colunas=int(row.get("_colunas") or 1),
        metragem_total_m=row.get("_metragem"),
        qtd_tubetes=row.get("_qtd_tubetes"),
        nr_etiquetas_informado=row.get("_nr_etiquetas"),
        custo_substrato_m2=custo_sub,
        custo_tubete=custo_tub,
        custo_embalagem_rolo=row.get("_custo_emb_rolo"),
        material_label=mat_label,
        tubete_label=tub_label,
    )
    detalhe["tubete_pol"] = row.get("_tub_pol")
    detalhe["fonte"] = "planilha_jul26"
    frete_real = row.get("_frete")
    if frete_real is not None and not (isinstance(frete_real, float) and pd.isna(frete_real)):
        detalhe["frete_real"] = float(frete_real)
    else:
        detalhe["frete_real"] = None
    return detalhe


def load_planilha_frete_ribbon(path: Path | None) -> pd.DataFrame:
    """Planilha de frete real para ribbons e demais itens (exceto etiquetas)."""
    if path is None or not path.exists():
        return pd.DataFrame()
    df = pd.read_excel(path)
    df = df.copy()
    # Aceita variações de cabeçalho
    colmap = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in {"nota", "nf", "número", "numero"}:
            colmap[c] = "Nota"
        elif cl in {"item", "código", "codigo"}:
            colmap[c] = "Item"
        elif cl.startswith("qtde") or cl in {"qtd", "quantidade"}:
            colmap[c] = "Qtde."
        elif "custo unit" in cl:
            colmap[c] = "Custo Unit."
        elif "custo total" in cl:
            colmap[c] = "Custo Total"
        elif cl in {"venda", "valor"}:
            colmap[c] = "Venda"
        elif cl == "frete":
            colmap[c] = "Frete"
    df = df.rename(columns=colmap)
    if "Nota" not in df.columns or "Frete" not in df.columns:
        return pd.DataFrame()

    df["_nf_key"] = df["Nota"].map(norm_nf)
    df["_code"] = df["Item"].map(norm_code) if "Item" in df.columns else None
    df["_code_key"] = df["Item"].map(code_key) if "Item" in df.columns else None
    df["_qtd"] = df["Qtde."].map(br_to_float) if "Qtde." in df.columns else None
    df["_venda"] = df["Venda"].map(br_to_float) if "Venda" in df.columns else None
    df["_frete"] = df["Frete"].map(br_to_float)
    df["_custo_unit"] = df["Custo Unit."].map(br_to_float) if "Custo Unit." in df.columns else None
    df["_custo_total"] = df["Custo Total"].map(br_to_float) if "Custo Total" in df.columns else None
    df["_used"] = False

    return df


def _resolve_nf_typo(planilha: pd.DataFrame, nf_key: str | None) -> str | None:
    if not nf_key:
        return None
    if (planilha["_nf_key"] == nf_key).any():
        return nf_key
    # tenta nf com +100 (ex.: 1062 → 1162) — erro comum na planilha jul/26
    if nf_key.isdigit():
        alt = str(int(nf_key) + 100)
        if (planilha["_nf_key"] == alt).any():
            return alt
    return nf_key


def match_frete_ribbon(
    planilha: pd.DataFrame,
    nf_key: str | None,
    code: str | None,
    qtd: float | None,
    venda: float | None,
) -> dict | None:
    """Casa item na planilha ribbon e retorna frete/custo reais.

    Retorno: {"frete", "custo_unit", "custo_total"} (valores podem ser None).
    """
    if planilha is None or planilha.empty or not nf_key:
        return None

    # NFs da planilha com typo 10xx em vez de 11xx
    cands = planilha[(planilha["_nf_key"] == nf_key) & (~planilha["_used"])]
    if cands.empty and nf_key.isdigit():
        alt = str(int(nf_key) - 100)  # faturamento 1162 ↔ planilha 1062
        cands = planilha[(planilha["_nf_key"] == alt) & (~planilha["_used"])]
    if cands.empty:
        return None

    ck = code_key(code)
    best_idx = None
    best_score = -1
    for idx, row in cands.iterrows():
        score = 0
        row_ck = row.get("_code_key")
        if ck and row_ck and ck == row_ck:
            score += 5
        elif ck and row_ck and ck.replace("/", "") == str(row_ck).replace("/", ""):
            score += 4
        qtub = row.get("_qtd")
        if qtd is not None and qtub is not None and abs(qtd - float(qtub)) < 0.01:
            score += 3
        vv = row.get("_venda")
        if venda is not None and vv is not None and abs(venda - float(vv)) < 0.05:
            score += 3
        if score > best_score:
            best_score = score
            best_idx = idx

    if best_idx is None or best_score < 8:
        # Exige código + (qtd ou venda) para evitar colisão RT vs numérica
        livres = cands[~cands["_used"]]
        if (
            best_idx is not None
            and best_score >= 5
            and ck
            and len(livres[livres["_code_key"] == ck]) == 1
            and (
                (
                    qtd is not None
                    and livres.iloc[0].get("_qtd") is not None
                    and abs(qtd - float(livres.iloc[0]["_qtd"])) < 0.01
                )
                or (
                    venda is not None
                    and livres.iloc[0].get("_venda") is not None
                    and abs(venda - float(livres.iloc[0]["_venda"])) < 0.05
                )
            )
        ):
            best_idx = livres[livres["_code_key"] == ck].index[0]
        elif best_idx is None or best_score < 8:
            return None

    planilha.at[best_idx, "_used"] = True
    frete = planilha.at[best_idx, "_frete"]
    custo_unit = planilha.at[best_idx, "_custo_unit"]
    custo_total = planilha.at[best_idx, "_custo_total"]

    def _num(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return float(v)

    return {
        "frete": _num(frete),
        "custo_unit": _num(custo_unit),
        "custo_total": _num(custo_total),
    }


def calcular_relatorio(
    path: Path,
    etiqueta_cost_sheet: Path | None = None,
    frete_ribbon_sheet: Path | None = None,
) -> pd.DataFrame:
    fat = pd.read_excel(path, sheet_name="Faturamento")
    custos = load_custos_ultimo(path)
    segmento = load_segmento(path)

    if etiqueta_cost_sheet is None:
        candidate = path.parent / DEFAULT_ETIQUETA_COST_SHEET
        etiqueta_cost_sheet = candidate if candidate.exists() else None
    planilha = load_planilha_etiquetas(etiqueta_cost_sheet)
    if not planilha.empty:
        planilha["_used"] = False

    if frete_ribbon_sheet is None:
        candidate_f = path.parent / DEFAULT_FRETE_RIBBON_SHEET
        frete_ribbon_sheet = candidate_f if candidate_f.exists() else None
    planilha_frete = load_planilha_frete_ribbon(frete_ribbon_sheet)

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
        desc_u = str(r.get("Descrição", "")).upper()
        if pd.isna(segmento_nome):
            # Fallback por descrição
            if "ETIQUETA" in desc_u or "ETIQ" in desc_u or "ROTULO" in desc_u or "RÓTULO" in desc_u:
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
            "ETIQUETA" in desc_u or "ETIQ" in desc_u or "ROTULO" in desc_u or "RÓTULO" in desc_u
        )

        if is_etiqueta:
            matched = match_planilha_etiqueta(
                planilha,
                norm_nf(r.get("Número")),
                qtd,
                str(r.get("Descrição", "")),
            )
            if matched is not None:
                detalhe = detalhe_from_planilha(matched)
                if not detalhe["completo"]:
                    pendencias.append(detalhe["pendencias"] or "etiqueta_planilha")
                else:
                    # Nº de rolos = nº de tubetes (planilha). Custo unitário = custo do rolo.
                    custo_unit = detalhe["custo_rolo"]
                    base_custo = "planilha_jul26"
                    # Se a NF veio em etiquetas (ex.: 270000) e não em rolos,
                    # o total segue a planilha (rolos/tubetes).
                    if (
                        qtd is not None
                        and detalhe.get("qtd_tubetes")
                        and abs(qtd - float(detalhe["qtd_tubetes"])) > 0.01
                    ):
                        # força total pela planilha via custo unitário equivalente
                        # mantendo a quantidade da NF no relatório
                        if qtd > 0 and detalhe.get("custo_total_planilha") is not None:
                            custo_unit = float(detalhe["custo_total_planilha"]) / qtd
                            base_custo = "planilha_jul26_rateio"
            else:
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

        # Frete/custo real: etiquetas pela planilha de etiquetas; demais pela planilha ribbon
        frete_real = detalhe.get("frete_real")
        base_frete_src = "planilha_etiqueta" if frete_real is not None else None
        match_rib = None
        if not is_etiqueta:
            match_rib = match_frete_ribbon(
                planilha_frete,
                norm_nf(r.get("Número")),
                r.get("code"),
                qtd,
                venda,
            )
            if match_rib is not None:
                if match_rib.get("frete") is not None:
                    frete_real = match_rib["frete"]
                    base_frete_src = "planilha_ribbon"
                # Custo real da planilha (ex.: 33,60 em vez de 32,00 do Custos_RS)
                if match_rib.get("custo_total") is not None and (
                    qtd is None
                    or match_rib.get("custo_unit") is None
                    or (
                        match_rib.get("custo_unit") is not None
                        and qtd is not None
                        and abs(match_rib["custo_total"] - match_rib["custo_unit"] * qtd) < 0.05
                    )
                ):
                    if qtd is not None and qtd > 0:
                        custo_unit = float(match_rib["custo_total"]) / qtd
                    elif match_rib.get("custo_unit") is not None:
                        custo_unit = float(match_rib["custo_unit"])
                    base_custo = "planilha_ribbon"
                    # remove pendência de custo se havia
                    pendencias = [p for p in pendencias if p not in {"custo_rs", "codigo", "segmento_sem_regra"}]
                elif match_rib.get("custo_unit") is not None:
                    custo_unit = float(match_rib["custo_unit"])
                    base_custo = "planilha_ribbon"
                    pendencias = [p for p in pendencias if p not in {"custo_rs", "codigo", "segmento_sem_regra"}]

        completo = custo_unit is not None and qtd is not None and venda is not None
        usa_frete_real = frete_real is not None
        if usa_frete_real:
            base_frete = base_frete_src or "planilha"
        else:
            base_frete = "3%" if venda is not None else None

        if completo:
            # Para planilha com qtd de tubetes alinhada à NF: custo_rolo * qtd
            if (
                base_custo == "planilha_jul26"
                and detalhe.get("custo_total_planilha") is not None
                and detalhe.get("qtd_tubetes") is not None
                and qtd is not None
                and abs(qtd - float(detalhe["qtd_tubetes"])) < 0.01
            ):
                custo_total = float(detalhe["custo_total_planilha"])
            elif base_custo == "planilha_ribbon" and match_rib and match_rib.get("custo_total") is not None:
                # Prefer total da planilha quando o item ribbon foi casado
                custo_total = float(match_rib["custo_total"])
            else:
                custo_total = custo_unit * qtd
            frete = float(frete_real) if usa_frete_real else venda * 0.03
            imposto = venda * 0.092
            # % lucro = (venda - custo - frete - imposto) / custo  (custo do produto, sem frete)
            venda_liquida = venda - custo_total - frete - imposto
            perc_lucro = (venda_liquida / custo_total) if custo_total else None
            status = STATUS_OK
            pendencia_txt = ""
        else:
            custo_total = None
            if usa_frete_real:
                frete = float(frete_real)
            else:
                frete = venda * 0.03 if venda is not None else None
            imposto = venda * 0.092 if venda is not None else None
            venda_liquida = None
            perc_lucro = None
            status = STATUS_INCOMPLETO
            pendencia_txt = ";".join(pendencias)

        rows.append(
            {
                "Número": format_nf_4digitos(r.get("Número")),
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
                "Tubete": detalhe.get("tubete_label"),
                "Custo_tubete": detalhe.get("custo_tubete"),
                "Custo_embalagem_rolo": detalhe.get("custo_embalagem_rolo"),
                "Custo_material_rolo": detalhe.get("custo_material_rolo"),
                "Custo_rolo": detalhe.get("custo_rolo"),
                "Qtd_tubetes": detalhe.get("qtd_tubetes"),
                "Base custo unitário": base_custo,
                "Custo unitário item": custo_unit,
                "Custo total item": custo_total,
                "Frete": frete,
                "Base frete": base_frete,
                "Frete (3%)": frete,  # compatibilidade com dashboard antigo
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
    parser.add_argument(
        "--etiquetas",
        default=DEFAULT_ETIQUETA_COST_SHEET,
        help="Planilha de cálculo de custo de etiquetas (jul/26)",
    )
    parser.add_argument(
        "--frete-ribbon",
        default=DEFAULT_FRETE_RIBBON_SHEET,
        help="Planilha de frete real de ribbons e demais itens (exceto etiquetas)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    etiq_path = Path(args.etiquetas)
    if not etiq_path.exists():
        etiq_path = None
    frete_path = Path(args.frete_ribbon)
    if not frete_path.exists():
        frete_path = None

    df = calcular_relatorio(input_path, etiq_path, frete_path)
    summary = resumo(df)
    incompletos = df[df["Status custo"] == STATUS_INCOMPLETO].copy()
    from_planilha = df[df["Base custo unitário"].fillna("").str.startswith("planilha_jul26")].copy()
    frete_real_rows = df[df["Base frete"].fillna("").str.startswith("planilha")].copy()

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Relatorio", index=False)
        summary.to_excel(writer, sheet_name="Resumo", index=False)
        incompletos.to_excel(writer, sheet_name="Custo_Incompleto", index=False)
        from_planilha.to_excel(writer, sheet_name="Etiquetas_Planilha", index=False)
        frete_real_rows.to_excel(writer, sheet_name="Frete_Real", index=False)

    print(f"Relatório gerado: {output_path}")
    print(summary.to_string(index=False))
    print(f"\nLinhas no relatório: {len(df)}")
    print(f"OK: {(df['Status custo'] == STATUS_OK).sum()}")
    print(f"Custo incompleto: {(df['Status custo'] == STATUS_INCOMPLETO).sum()}")
    print(f"Etiquetas via planilha jul/26: {len(from_planilha)}")
    print(
        "Frete real:",
        frete_real_rows.groupby("Base frete")["Frete"].agg(["count", "sum"]).to_string(),
    )

    # Gera também o dashboard HTML ao lado do Excel
    try:
        import sys

        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from gerar_dashboard_html import build_rows, load_despesas, render_html

        dts = pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce")
        if dts.notna().any():
            periodo = f"{dts.min().strftime('%d/%m/%Y')} a {dts.max().strftime('%d/%m/%Y')}"
        else:
            periodo = "Período não disponível"
        html_path = output_path.with_name("Dashboard_Custo_Faturamento_RBT.html")
        html_path.write_text(
            render_html(build_rows(df), periodo, load_despesas()),
            encoding="utf-8",
        )
        print(f"Dashboard HTML gerado: {html_path}")
    except Exception as exc:  # pragma: no cover - best effort
        print(f"Aviso: não foi possível gerar o dashboard HTML ({exc})")


if __name__ == "__main__":
    main()
