#!/usr/bin/env python3
"""Gera dashboard HTML interativo a partir do relatório de custo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def br_money(v: float | None) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build_rows(df: pd.DataFrame) -> list[dict]:
    rows = []
    dts = pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce")
    for idx, (i, r) in enumerate(df.iterrows()):
        seg_val = r.get("Segmento")
        if seg_val is not None and not (isinstance(seg_val, float) and pd.isna(seg_val)):
            if str(seg_val).strip().lower() == "ativo":
                continue  # segmento Ativo fora da análise
        dt = dts.loc[i]
        custo_rolo = r.get("Custo_rolo")
        if custo_rolo is None or (isinstance(custo_rolo, float) and pd.isna(custo_rolo)):
            base = str(r.get("Base custo unitário") or "")
            unit = r.get("Custo unitário item")
            if (
                unit is not None
                and not (isinstance(unit, float) and pd.isna(unit))
                and (base in {"rolo", "planilha_jul26"} or base.startswith("planilha_jul26"))
            ):
                custo_rolo = unit
        rows.append(
            {
                "id": idx,
                "n": None if pd.isna(r.get("Número")) else str(r.get("Número")),
                "c": None if pd.isna(r.get("Nome")) else str(r.get("Nome"))[:70],
                "d": None if pd.isna(dt) else dt.strftime("%Y-%m-%d"),
                "uf": None if pd.isna(r.get("UF")) else str(r.get("UF")),
                "cod": None if pd.isna(r.get("Código")) else str(r.get("Código")),
                "desc": None
                if pd.isna(r.get("Descrição"))
                else str(r.get("Descrição"))[:100],
                "seg": None if pd.isna(r.get("Segmento")) else str(r.get("Segmento")),
                "mat": None if pd.isna(r.get("Material")) else str(r.get("Material")),
                "tub": None if pd.isna(r.get("Tubete")) else str(r.get("Tubete")),
                "cr": None
                if custo_rolo is None or (isinstance(custo_rolo, float) and pd.isna(custo_rolo))
                else round(float(custo_rolo), 4),
                "v": None
                if pd.isna(r.get("Valor total venda"))
                else round(float(r.get("Valor total venda")), 2),
                "ct": None
                if pd.isna(r.get("Custo total item"))
                else round(float(r.get("Custo total item")), 2),
                "f": None
                if pd.isna(r.get("Frete (3%)"))
                else round(float(r.get("Frete (3%)")), 2),
                "i": None
                if pd.isna(r.get("Imposto (9,2%)"))
                else round(float(r.get("Imposto (9,2%)")), 2),
                "l": None
                if pd.isna(r.get("Venda líquida"))
                else round(float(r.get("Venda líquida")), 2),
                "p": None if pd.isna(r.get("% Lucro")) else round(float(r.get("% Lucro")), 4),
                "st": "ok" if r.get("Status custo") == "ok" else "inc",
            }
        )
    return rows


def build_despesa_rows(df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, r in df.iterrows():
        rows.append(
            {
                "id": int(r.get("id")) if pd.notna(r.get("id")) else None,
                "f": None if pd.isna(r.get("Fornecedor")) else str(r.get("Fornecedor"))[:70],
                "h": None if pd.isna(r.get("Histórico")) else str(r.get("Histórico"))[:80],
                "d": None if pd.isna(r.get("Liquidação")) else str(r.get("Liquidação"))[:10],
                "m": None if pd.isna(r.get("Competência")) else str(r.get("Competência"))[:7],
                "st": None if pd.isna(r.get("Situação")) else str(r.get("Situação")),
                "v": None if pd.isna(r.get("Valor")) else round(float(r.get("Valor")), 2),
                "cat": None if pd.isna(r.get("Categoria")) else str(r.get("Categoria")),
                "sub": None if pd.isna(r.get("Subcategoria")) else str(r.get("Subcategoria")),
            }
        )
    return rows


def render_html(rows: list[dict], periodo_label: str, despesas: list[dict] | None = None) -> str:
    data_json = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    desp_json = json.dumps(despesas or [], ensure_ascii=False, separators=(",", ":"))

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>RibbonTech · Dashboard Interativo de Custo e Lucro</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Sora:wght@500;600;700&display=swap" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
  <style>
    :root {{
      --ink: #14212b;
      --ink-soft: #2a3b49;
      --mist: #e6eef3;
      --panel: rgba(255,255,255,0.82);
      --line: rgba(20,33,43,0.12);
      --teal: #1f6f78;
      --teal-deep: #14545c;
      --copper: #c45c26;
      --good: #1f7a4c;
      --shadow: 0 18px 50px rgba(20,33,43,0.12);
      --radius: 16px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1100px 520px at 8% -8%, rgba(31,111,120,0.22), transparent 55%),
        radial-gradient(900px 480px at 95% 0%, rgba(196,92,38,0.15), transparent 50%),
        linear-gradient(180deg, #d9e5ec 0%, var(--mist) 42%, #f4f7f9 100%);
      min-height: 100vh;
    }}
    body::before {{
      content: "";
      position: fixed; inset: 0; pointer-events: none; opacity: 0.03; z-index: 0;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='.55'/%3E%3C/svg%3E");
    }}
    .wrap {{ position: relative; z-index: 1; width: min(1240px, calc(100% - 1.5rem)); margin: 0 auto; padding: 1.2rem 0 2.5rem; }}

    .hero {{
      padding: 1.35rem 1.4rem 1.2rem;
      border-radius: 24px;
      background: linear-gradient(135deg, rgba(20,33,43,0.96), rgba(31,111,120,0.88) 58%, rgba(196,92,38,0.7));
      color: #f7fafc;
      box-shadow: var(--shadow);
      animation: rise .6s ease both;
    }}
    .brand {{ font-family: Sora, sans-serif; font-size: clamp(1.8rem, 4.5vw, 2.6rem); margin: 0; letter-spacing: -0.03em; }}
    .hero p {{ margin: .35rem 0 0; color: rgba(247,250,252,.86); max-width: 60ch; }}
    .period {{ display: inline-flex; margin-top: .75rem; padding: .3rem .65rem; border: 1px solid rgba(255,255,255,.22); border-radius: 999px; font-size: .84rem; }}

    .kpi-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: .7rem; margin-top: 1rem; }}
    @media (min-width: 900px) {{
      .kpi-grid {{ grid-template-columns: repeat(4, 1fr); }}
    }}
    @media (min-width: 1200px) {{
      .kpi-grid {{ grid-template-columns: repeat(7, 1fr); }}
    }}
    .kpi.kpi-caixa {{
      background: rgba(255,255,255,.16);
      border-color: rgba(255,255,255,.28);
    }}
    .kpi {{
      background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.14);
      border-radius: 14px; padding: .75rem .85rem;
    }}
    .kpi span {{ display: block; font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; color: rgba(247,250,252,.72); margin-bottom: .25rem; }}
    .kpi strong {{ font-family: Sora, sans-serif; font-size: clamp(1rem, 2vw, 1.35rem); font-weight: 600; display: block; }}
    .kpi em {{
      display: block;
      margin-top: .28rem;
      font-style: normal;
      font-size: .82rem;
      font-weight: 600;
      color: rgba(247,250,252,.82);
    }}

    .filters {{
      margin-top: 1rem;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 1rem;
      backdrop-filter: blur(10px);
      animation: rise .7s ease both;
    }}
    .filters h2 {{ font-family: Sora, sans-serif; font-size: 1.05rem; margin: 0 0 .75rem; }}
    .filter-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: .7rem;
    }}
    label {{ display: grid; gap: .28rem; font-size: .78rem; color: var(--ink-soft); font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }}
    input, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: .55rem .65rem;
      font: 500 0.92rem "IBM Plex Sans", sans-serif;
      color: var(--ink);
      background: #fff;
    }}
    input:focus, select:focus {{ outline: 2px solid rgba(31,111,120,.35); border-color: var(--teal); }}
    .filter-actions {{ display: flex; flex-wrap: wrap; gap: .55rem; margin-top: .85rem; align-items: center; }}
    button {{
      border: 0; border-radius: 999px; padding: .55rem 1rem;
      font: 600 0.9rem "IBM Plex Sans", sans-serif; cursor: pointer;
      transition: transform .15s ease, opacity .15s ease;
    }}
    button:hover {{ transform: translateY(-1px); }}
    .btn-primary {{ background: var(--teal); color: #fff; }}
    .btn-ghost {{ background: rgba(20,33,43,.08); color: var(--ink); }}
    .chip {{
      display: inline-flex; align-items: center; gap: .35rem;
      background: rgba(31,111,120,.12); color: var(--teal-deep);
      border-radius: 999px; padding: .35rem .7rem; font-size: .82rem; font-weight: 600;
    }}
    .chip button {{
      all: unset; cursor: pointer; color: var(--copper); font-weight: 700; padding: 0 .2rem;
    }}
    .hint {{ margin: .55rem 0 0; color: var(--ink-soft); font-size: .84rem; }}

    section {{ margin-top: 1.15rem; animation: rise .75s ease both; }}
    .section-head {{ display: flex; justify-content: space-between; gap: 1rem; align-items: end; margin-bottom: .7rem; }}
    .section-head h2 {{ font-family: Sora, sans-serif; font-size: 1.2rem; margin: 0; letter-spacing: -.02em; }}
    .section-head p {{ margin: .2rem 0 0; color: var(--ink-soft); font-size: .92rem; }}
    .mini-title {{
      margin: 0 0 .65rem;
      font-family: Sora, sans-serif;
      font-size: .95rem;
      letter-spacing: -.01em;
      color: var(--ink);
    }}
    .panel {{
      background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
      box-shadow: var(--shadow); padding: 1rem; backdrop-filter: blur(10px);
    }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: .9rem; }}
    .chart-box {{ position: relative; height: 320px; }}
    .chart-box.tall {{ height: 380px; }}
    .click-note {{ margin-top: .55rem; font-size: .82rem; color: var(--ink-soft); }}

    table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
    th, td {{ text-align: left; padding: .62rem .4rem; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; color: var(--ink-soft); }}
    tr.item-row {{ cursor: pointer; }}
    tr.item-row:hover td, tr.item-row.active td {{ background: rgba(31,111,120,.08); }}
    .neg {{ color: #a12828; font-weight: 600; }}
    .pos {{ color: var(--good); font-weight: 600; }}
    .table-wrap {{ overflow: auto; max-height: 420px; }}
    .table-wrap.tall-list {{ max-height: 560px; }}
    .cost-input {{
      width: 110px;
      border: 1px solid rgba(196,92,38,.45);
      border-radius: 8px;
      padding: .4rem .45rem;
      font: 600 0.86rem "IBM Plex Sans", sans-serif;
      color: var(--ink);
      background: #fff8f3;
    }}
    .cost-input:focus {{ outline: 2px solid rgba(196,92,38,.35); border-color: var(--copper); }}
    .cost-actions {{ display: flex; gap: .35rem; align-items: center; margin-top: .25rem; }}
    .btn-mini {{
      border: 0; border-radius: 999px; padding: .2rem .55rem;
      font: 600 0.72rem "IBM Plex Sans", sans-serif; cursor: pointer;
      background: rgba(31,111,120,.12); color: var(--teal-deep);
    }}
    .faixa-bar {{
      display: flex; flex-wrap: wrap; gap: .45rem; align-items: center;
      margin: 0 0 .75rem;
    }}
    .faixa-bar .faixa-label {{
      font-size: .82rem; font-weight: 600; color: var(--ink-soft); margin-right: .15rem;
    }}
    .faixa-bar button {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: .4rem .75rem;
      font: 600 0.84rem "IBM Plex Sans", sans-serif;
      cursor: pointer;
      background: rgba(255,255,255,.72);
      color: var(--ink);
      transition: background .15s ease, border-color .15s ease, color .15s ease;
    }}
    .faixa-bar button:hover {{
      border-color: rgba(31,111,120,.45);
      background: rgba(31,111,120,.08);
    }}
    .faixa-bar button.active {{
      background: rgba(31,111,120,.92);
      border-color: rgba(31,111,120,.92);
      color: #fff;
    }}
    .faixa-bar button.active[data-faixa="lt10"] {{
      background: rgba(161,40,40,.9);
      border-color: rgba(161,40,40,.9);
    }}
    .faixa-bar button.active[data-faixa="11-30"] {{
      background: rgba(196,92,38,.92);
      border-color: rgba(196,92,38,.92);
    }}
    .faixa-bar button.active[data-faixa="gt30"],
    .faixa-bar button.active[data-faixa="gt51"] {{
      background: rgba(46,125,50,.92);
      border-color: rgba(46,125,50,.92);
    }}
    .faixa-bar button.active[data-faixa="31-50"] {{
      background: rgba(31,111,120,.92);
      border-color: rgba(31,111,120,.92);
    }}
    .faixa-bar button.active[data-faixa="lte30"] {{
      background: rgba(161,40,40,.9);
      border-color: rgba(161,40,40,.9);
      color: #fff;
    }}
    .faixa-bar button.active[data-tipo="Bopp"],
    .faixa-bar button.active[data-tipo="Couche"],
    .faixa-bar button.active[data-tipo="Termico"] {{
      background: rgba(31,111,120,.92);
      border-color: rgba(31,111,120,.92);
      color: #fff;
    }}
    .btn-mini.danger {{ background: rgba(161,40,40,.12); color: #a12828; }}
    .status-pill {{
      display: inline-flex; padding: .15rem .45rem; border-radius: 999px;
      font-size: .75rem; font-weight: 600;
    }}
    .status-ok {{ background: rgba(31,122,76,.12); color: var(--good); }}
    .status-inc {{ background: rgba(196,92,38,.14); color: #8a3d12; }}
    .status-manual {{ background: rgba(31,111,120,.14); color: var(--teal-deep); }}
    .manual-banner {{
      margin-top: .7rem; padding: .65rem .8rem; border-radius: 12px;
      background: rgba(196,92,38,.1); border: 1px solid rgba(196,92,38,.22);
      color: var(--ink-soft); font-size: .86rem;
    }}
    .persist-bar {{
      position: sticky; top: 0; z-index: 20;
      display: none;
      margin: .8rem 0 0;
      padding: .8rem 1rem;
      border-radius: 14px;
      background: linear-gradient(135deg, #14545c, #1f6f78);
      color: #fff;
      box-shadow: var(--shadow);
      align-items: center;
      justify-content: space-between;
      gap: .8rem;
      flex-wrap: wrap;
    }}
    .persist-bar.show {{ display: flex; }}
    .persist-bar p {{ margin: 0; font-size: .9rem; max-width: 62ch; }}
    .persist-bar .btn-primary {{ background: #fff; color: var(--teal-deep); }}
    .persist-bar .btn-ghost {{ background: rgba(255,255,255,.16); color: #fff; }}
    .footer {{ margin-top: 1.4rem; text-align: center; color: var(--ink-soft); font-size: .84rem; }}

    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(12px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    @media (max-width: 980px) {{
      .kpi-grid, .filter-grid, .grid-2 {{ grid-template-columns: 1fr 1fr; }}
    }}
    .check-box {{
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      padding: .55rem .65rem;
      max-height: 150px;
      overflow: auto;
      display: grid;
      gap: .28rem;
    }}
    .check-box label {{
      display: flex;
      align-items: center;
      gap: .45rem;
      text-transform: none;
      letter-spacing: 0;
      font-size: .88rem;
      font-weight: 500;
      color: var(--ink);
      cursor: pointer;
    }}
    .check-box input {{ width: auto; margin: 0; accent-color: var(--teal); }}
    .check-actions {{ display: flex; gap: .45rem; margin-top: .35rem; }}
    .check-actions button {{
      border: 0; border-radius: 999px; padding: .25rem .6rem;
      font: 600 0.75rem "IBM Plex Sans", sans-serif; cursor: pointer;
      background: rgba(20,33,43,.08); color: var(--ink);
    }}
    .filter-span-2 {{ grid-column: span 2; }}

    @media (max-width: 640px) {{
      .kpi-grid, .filter-grid, .grid-2 {{ grid-template-columns: 1fr; }}
      .filter-span-2 {{ grid-column: span 1; }}
      .chart-box, .chart-box.tall {{ height: 250px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <h1 class="brand">RibbonTech</h1>
      <p>Dashboard interativo de faturamento, custo e lucro. Use os filtros ou clique nos gráficos para explorar.</p>
      <div class="period">Base completa: {periodo_label}</div>
      <div class="kpi-grid">
        <div class="kpi"><span>Venda</span><strong id="kpiVenda">—</strong><em id="kpiVendaPct">100%</em></div>
        <div class="kpi"><span>Custo</span><strong id="kpiCusto">—</strong><em id="kpiCustoPct">—</em></div>
        <div class="kpi"><span>Venda líquida</span><strong id="kpiLiq">—</strong><em id="kpiLiqPct">—</em></div>
        <div class="kpi"><span>Despesas ADM</span><strong id="kpiDesp">—</strong><em id="kpiDespPct">—</em></div>
        <div class="kpi"><span>Resultado após despesas</span><strong id="kpiResult">—</strong><em id="kpiResultPct">—</em></div>
        <div class="kpi kpi-caixa"><span>Caixa</span><strong id="kpiCaixa">—</strong><em id="kpiCaixaPct">Acumulado desde jul/2026</em></div>
        <div class="kpi"><span>Itens filtrados</span><strong id="kpiItens">—</strong><em id="kpiBasePct">% sobre a venda</em></div>
      </div>
    </header>

    <section class="filters">
      <h2>Filtros</h2>
      <div class="filter-grid">
        <label>Data início<input type="date" id="fInicio" /></label>
        <label>Data fim<input type="date" id="fFim" /></label>
        <label>Cliente
          <select id="fCliente"><option value="">Todos</option></select>
        </label>
        <label>UF
          <select id="fUF"><option value="">Todas</option></select>
        </label>
        <div class="filter-span-2">
          <label>Segmento (pode marcar mais de um)
            <div class="check-box" id="fSegmentoBox"></div>
            <div class="check-actions">
              <button type="button" id="btnSegAll">Marcar todos</button>
              <button type="button" id="btnSegNone">Limpar</button>
            </div>
          </label>
        </div>
        <div class="filter-span-2">
          <label>Mês selecionado (mais recentes primeiro)
            <div class="check-box" id="fMesBox"></div>
            <div class="check-actions">
              <button type="button" id="btnMesAll">Marcar todos</button>
              <button type="button" id="btnMesNone">Limpar</button>
            </div>
          </label>
        </div>
        <div class="filter-span-2">
          <label>Categoria de despesa (pode marcar mais de uma)
            <div class="check-box" id="fDespCatBox"></div>
            <div class="check-actions">
              <button type="button" id="btnDespAll">Marcar todas</button>
              <button type="button" id="btnDespNone">Limpar</button>
            </div>
          </label>
        </div>
        <label>Material
          <select id="fMaterial"><option value="">Todos</option></select>
        </label>
        <label>Status do custo
          <select id="fStatus">
            <option value="">Todos</option>
            <option value="ok">Custo ok (automático)</option>
            <option value="inc">Custo incompleto</option>
            <option value="manual">Custo manual</option>
            <option value="com_custo">Com custo (ok + manual)</option>
          </select>
        </label>
        <label>Faixa de % lucro
          <select id="fLucroFaixa">
            <option value="">Todas</option>
            <option value="lt10">Abaixo de 10%</option>
            <option value="11-30">11% a 30%</option>
            <option value="gt30">Acima de 30%</option>
            <option value="na">Sem % (incompleto)</option>
          </select>
        </label>
        <label>Busca cliente / código / descrição
          <input type="search" id="fBusca" placeholder="Ex.: Ribbon, MG, 300443..." />
        </label>
        <label>Qtd. clientes na tabela
          <select id="fTopN">
            <option value="0" selected>Todos</option>
            <option value="20">20</option>
            <option value="50">50</option>
            <option value="100">100</option>
            <option value="200">200</option>
          </select>
        </label>
        <label>Itens por página
          <select id="fPageSize">
            <option value="25">25</option>
            <option value="50" selected>50</option>
            <option value="100">100</option>
          </select>
        </label>
      </div>
      <div class="filter-actions">
        <button class="btn-primary" id="btnAplicar" type="button">Aplicar filtros</button>
        <button class="btn-ghost" id="btnLimpar" type="button">Limpar filtros</button>
        <button class="btn-primary" id="btnDownloadHtml" type="button">Baixar dashboard com meus custos</button>
        <button class="btn-ghost" id="btnExportManual" type="button">Exportar CSV</button>
        <button class="btn-ghost" id="btnLoadManual" type="button">Carregar custos salvos</button>
        <button class="btn-ghost" id="btnClearManual" type="button">Limpar custos manuais</button>
        <input type="file" id="fileManual" accept=".json,application/json,.csv,text/csv" hidden />
        <span class="chip" id="activeChips" hidden></span>
      </div>
      <p class="hint">Dica: marque um ou mais segmentos/meses nos checkboxes, ou clique nos gráficos para marcar/desmarcar. O segmento Ativo fica sempre fora da análise.</p>
      <div class="manual-banner">
        <strong>Por que o custo “some”?</strong> O navegador não grava bem dados em arquivo aberto do computador.
        Depois de informar custos, clique em <strong>Baixar dashboard com meus custos</strong> e use
        <em>sempre esse arquivo baixado</em> nos próximos acessos.
        <span id="manualCountLabel"></span>
      </div>
      <div class="persist-bar" id="persistBar">
        <p id="persistMsg">Custo salvo neste navegador. Para não perder no próximo acesso, baixe o dashboard com seus custos.</p>
        <div class="filter-actions" style="margin:0;">
          <button class="btn-primary" id="btnDownloadHtml2" type="button">Baixar agora</button>
          <button class="btn-ghost" id="btnDismissPersist" type="button">Agora não</button>
        </div>
      </div>
    </section>

    <!-- Custos manuais embutidos no arquivo (não apagar) -->
    <script id="manual-baked" type="application/json">{{}}</script>

    <section>
      <div class="section-head">
        <div>
          <h2>Venda mensal no período</h2>
          <p>Gráfico de colunas — clique no mês para filtrar.</p>
        </div>
      </div>
      <div class="panel">
        <div class="chart-box tall"><canvas id="chartVendaMensal"></canvas></div>
        <p class="click-note" id="mesNote">Nenhum mês selecionado.</p>
      </div>
    </section>

    <section class="grid-2">
      <div>
        <div class="section-head">
          <div>
            <h2>Lucro por mês</h2>
            <p>Venda líquida mensal dos itens filtrados.</p>
          </div>
        </div>
        <div class="panel">
          <div class="chart-box"><canvas id="chartLucroMensal"></canvas></div>
        </div>
      </div>
      <div>
        <div class="section-head">
          <div>
            <h2>Faturamento por segmento</h2>
            <p>Valor e % da venda. Clique no segmento para filtrar.</p>
          </div>
        </div>
        <div class="panel">
          <div class="chart-box"><canvas id="chartSegmento"></canvas></div>
        </div>
      </div>
    </section>

    <section class="grid-2">
      <div>
        <div class="section-head">
          <div>
            <h2>Lucro por cliente</h2>
            <p id="clientesMeta">Nas faixas, clientes em ordem crescente de % lucro. Clique na linha para filtrar; clique de novo ou em “Ver todos” para limpar.</p>
          </div>
        </div>
        <div class="faixa-bar" id="faixaClienteBar" role="group" aria-label="Faixas de lucro por cliente">
          <span class="faixa-label">Faixa:</span>
          <button type="button" data-faixa="" class="active">Todas</button>
          <button type="button" data-faixa="lte30">Até 30%</button>
          <button type="button" data-faixa="31-50">31% a 50%</button>
          <button type="button" data-faixa="gt51">Acima de 51%</button>
          <button type="button" id="btnLimparCliente" class="btn-ghost" style="margin-left:.35rem;">Ver todos os clientes</button>
        </div>
        <div class="panel table-wrap tall-list">
          <table>
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Venda</th>
                <th>Lucro</th>
                <th>% Lucro</th>
              </tr>
            </thead>
            <tbody id="tblClientes"></tbody>
          </table>
        </div>
      </div>
      <div>
        <div class="section-head">
          <div>
            <h2>Top UFs</h2>
            <p>Clique na barra para filtrar por UF.</p>
          </div>
        </div>
        <div class="panel">
          <div class="chart-box"><canvas id="chartUF"></canvas></div>
        </div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Lucro por item</h2>
          <p id="itensMeta">Detalhe dos itens no filtro atual.</p>
        </div>
        <div class="filter-actions" style="margin:0;">
          <button class="btn-ghost" id="btnPrev" type="button">Anterior</button>
          <button class="btn-ghost" id="btnNext" type="button">Próxima</button>
        </div>
      </div>
      <div class="faixa-bar" id="faixaLucroBar" role="group" aria-label="Faixas de lucro por item">
        <span class="faixa-label">Faixa de lucro:</span>
        <button type="button" data-faixa="" class="active">Todas</button>
        <button type="button" data-faixa="lt10">Abaixo de 10%</button>
        <button type="button" data-faixa="11-30">11% a 30%</button>
        <button type="button" data-faixa="gt30">Acima de 30%</button>
      </div>
      <div class="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th>Data</th>
              <th>NF</th>
              <th>Cliente</th>
              <th>Segmento</th>
              <th>Descrição</th>
              <th>Venda</th>
              <th>Custo</th>
              <th>Venda líquida</th>
              <th>% Lucro</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody id="tblItens"></tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Custo por rolo de etiqueta</h2>
          <p>Veja o custo de cada rolo por cliente e NF. Use os botões de tipo para filtrar.</p>
        </div>
      </div>
      <div class="faixa-bar" id="faixaTipoEtiqBar" role="group" aria-label="Tipo de etiqueta">
        <span class="faixa-label">Tipo:</span>
        <button type="button" data-tipo="" class="active">Todos</button>
        <button type="button" data-tipo="Bopp">Bopp</button>
        <button type="button" data-tipo="Couche">Couche</button>
        <button type="button" data-tipo="Termico">Térmico</button>
      </div>
      <div class="grid-2">
        <div class="panel table-wrap">
          <h3 class="mini-title">Média de custo/rolo por cliente</h3>
          <table>
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Itens</th>
                <th>Custo médio/rolo</th>
                <th>Custo total</th>
              </tr>
            </thead>
            <tbody id="tblCustoRoloCliente"></tbody>
          </table>
        </div>
        <div class="panel">
          <h3 class="mini-title">Custo médio/rolo por tipo</h3>
          <div class="chart-box"><canvas id="chartTipoEtiqueta"></canvas></div>
        </div>
      </div>
      <div class="panel table-wrap" style="margin-top:.9rem;">
        <h3 class="mini-title">Detalhe por cliente e NF</h3>
        <table>
          <thead>
            <tr>
              <th>Cliente</th>
              <th>NF</th>
              <th>Tipo</th>
              <th>Material / descrição</th>
              <th>Custo/rolo</th>
              <th>Custo total</th>
              <th>Venda</th>
              <th>% Lucro</th>
            </tr>
          </thead>
          <tbody id="tblCustoEtiqueta"></tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Despesas administrativas</h2>
          <p>Pessoal, pró-labore, aluguel, empréstimos, utilidades e demais despesas do período filtrado.</p>
        </div>
      </div>
      <div class="grid-2">
        <div class="panel">
          <div class="chart-box"><canvas id="chartDespesas"></canvas></div>
          <p class="click-note">Clique na barra para marcar/desmarcar a categoria.</p>
        </div>
        <div class="panel table-wrap">
          <table>
            <thead>
              <tr>
                <th>Categoria</th>
                <th>Subcategoria</th>
                <th>Valor</th>
                <th>%</th>
              </tr>
            </thead>
            <tbody id="tblDespResumo"></tbody>
          </table>
        </div>
      </div>
      <div class="panel table-wrap" style="margin-top:.9rem;">
        <table>
          <thead>
            <tr>
              <th>Mês</th>
              <th>Fornecedor</th>
              <th>Histórico</th>
              <th>Categoria</th>
              <th>Situação</th>
              <th>Valor</th>
            </tr>
          </thead>
          <tbody id="tblDespesas"></tbody>
        </table>
      </div>
    </section>

    <p class="footer">RibbonTech Brasil · Dashboard HTML interativo gerado a partir do relatório de custo e despesas</p>
  </div>

  <script>
    const ROWS = {data_json};
    const DESPESAS = {desp_json};
    const MANUAL_KEY = 'rbt_manual_costs_v1';

    const money = (v) => (v == null || Number.isNaN(v))
      ? '—'
      : v.toLocaleString('pt-BR', {{ style: 'currency', currency: 'BRL' }});
    const pct = (v) => (v == null || Number.isNaN(v))
      ? '—'
      : (v * 100).toLocaleString('pt-BR', {{ maximumFractionDigits: 1 }}) + '%';
    const fmtDate = (iso) => {{
      if (!iso) return '—';
      const [y,m,d] = iso.split('-');
      return `${{d}}/${{m}}/${{y}}`;
    }};
    const ymOf = (iso) => iso ? iso.slice(0, 7) : null;
    const MESES_PT = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
    const fmtMonthLabel = (ym) => {{
      if (!ym || ym.length < 7) return ym || '—';
      const y = ym.slice(0, 4);
      const m = Number(ym.slice(5, 7));
      if (!m || m < 1 || m > 12) return ym;
      return `${{MESES_PT[m - 1]}}/${{y}}`;
    }};
    const fmtMonthsList = (meses) => (meses || []).map(fmtMonthLabel).join(', ');
    const parseMoneyInput = (raw) => {{
      if (raw == null) return null;
      let t = String(raw).trim();
      if (!t) return null;
      t = t.replace(/R\\$\\s?/i, '').replace(/\\s/g, '');
      if (t.includes(',')) t = t.replace(/\\./g, '').replace(',', '.');
      const n = Number(t);
      return Number.isFinite(n) ? n : null;
    }};
    const formatInputMoney = (v) => {{
      if (v == null || Number.isNaN(v)) return '';
      return v.toLocaleString('pt-BR', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
    }};

    const state = {{
      page: 0,
      charts: {{}},
      selectedCliente: null,
      clienteLucroFaixa: '',
      tipoEtiqueta: '',
      manualCosts: loadManualCosts(),
    }};

    function normalizeCostMap(obj) {{
      const out = {{}};
      Object.entries(obj || {{}}).forEach(([k, v]) => {{
        const n = Number(v);
        if (Number.isFinite(n)) out[String(k)] = n;
      }});
      return out;
    }}

    function loadBakedCosts() {{
      try {{
        const el = document.getElementById('manual-baked');
        if (!el) return {{}};
        const txt = (el.textContent || '').trim();
        if (!txt) return {{}};
        return normalizeCostMap(JSON.parse(txt));
      }} catch (e) {{
        return {{}};
      }}
    }}

    function loadManualCosts() {{
      let local = {{}};
      try {{
        const raw = localStorage.getItem(MANUAL_KEY);
        if (raw) local = normalizeCostMap(JSON.parse(raw));
      }} catch (e) {{
        local = {{}};
      }}
      // Arquivo baixado com custos embutidos + memória do navegador
      return {{ ...loadBakedCosts(), ...local }};
    }}

    function updateManualCountLabel() {{
      const n = Object.keys(state.manualCosts).length;
      const el = document.getElementById('manualCountLabel');
      if (el) {{
        el.textContent = n
          ? ` · ${{n}} custo(s) manual(is) ativo(s). Lembre de baixar o dashboard para não perder.`
          : '';
      }}
    }}

    function saveManualCosts({{ showPersistBar = false, autoJsonBackup = false }} = {{}}) {{
      try {{
        localStorage.setItem(MANUAL_KEY, JSON.stringify(state.manualCosts));
      }} catch (e) {{
        // file:// ou bloqueio de storage — seguimos com arquivo embutido/backup
      }}
      const baked = document.getElementById('manual-baked');
      if (baked) baked.textContent = JSON.stringify(state.manualCosts);
      updateManualCountLabel();
      if (showPersistBar) {{
        const bar = document.getElementById('persistBar');
        if (bar) bar.classList.add('show');
      }}
      if (autoJsonBackup && Object.keys(state.manualCosts).length) {{
        downloadManualJson(false);
      }}
    }}

    function downloadBlob(filename, content, type) {{
      const blob = new Blob([content], {{ type }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }}

    function downloadManualJson(alertIfEmpty = true) {{
      const ids = Object.keys(state.manualCosts);
      if (!ids.length) {{
        if (alertIfEmpty) alert('Não há custos manuais para salvar.');
        return;
      }}
      downloadBlob(
        'custos_manuais_rbt.json',
        JSON.stringify(state.manualCosts, null, 2),
        'application/json;charset=utf-8;'
      );
    }}

    function downloadHtmlWithCosts() {{
      if (!Object.keys(state.manualCosts).length) {{
        alert('Informe ao menos um custo manual antes de baixar.');
        return;
      }}
      saveManualCosts({{ showPersistBar: false }});
      const html = '<!DOCTYPE html>\\n' + document.documentElement.outerHTML;
      downloadBlob(
        'Dashboard_Custo_Faturamento_RBT_com_custos.html',
        html,
        'text/html;charset=utf-8;'
      );
      const bar = document.getElementById('persistBar');
      if (bar) bar.classList.remove('show');
      alert('Arquivo baixado! Nos próximos acessos, abra “Dashboard_Custo_Faturamento_RBT_com_custos.html” (não o arquivo antigo sem custos).');
    }}

    function enrichRow(r) {{
      const out = {{ ...r }};
      const key = String(r.id);
      const manual = state.manualCosts[key];
      if (r.st === 'inc' && manual != null && Number.isFinite(manual)) {{
        out.ct = Math.round(manual * 100) / 100;
        out.f = out.v != null ? Math.round(out.v * 0.03 * 100) / 100 : null;
        out.i = out.v != null ? Math.round(out.v * 0.092 * 100) / 100 : null;
        if (out.v != null) {{
          out.l = Math.round((out.v - out.ct - (out.f || 0) - (out.i || 0)) * 100) / 100;
          out.p = out.ct ? out.l / out.ct : null;
        }} else {{
          out.l = null;
          out.p = null;
        }}
        out.st = 'manual';
        out.manual = true;
      }} else {{
        out.manual = false;
      }}
      return out;
    }}

    function allRows() {{
      return ROWS.map(enrichRow);
    }}

    function uniqueSorted(values) {{
      return [...new Set(values.filter(Boolean))].sort((a,b) => a.localeCompare(b, 'pt-BR'));
    }}

    function uniqueSortedDesc(values) {{
      return [...new Set(values.filter(Boolean))].sort((a,b) => b.localeCompare(a, 'pt-BR'));
    }}

    const CAIXA_INICIO = '2026-07';

    function computeCaixaAcumulado() {{
      // Caixa da empresa: soma dos resultados após despesas a partir de jul/2026
      const liqByMonth = new Map();
      for (const r of baseRows()) {{
        const m = ymOf(r.d);
        if (!m || m < CAIXA_INICIO) continue;
        if (r.l != null) liqByMonth.set(m, (liqByMonth.get(m) || 0) + r.l);
      }}
      const despByMonth = new Map();
      for (const d of DESPESAS) {{
        const m = d.m;
        if (!m || m < CAIXA_INICIO) continue;
        if (d.v != null) despByMonth.set(m, (despByMonth.get(m) || 0) + d.v);
      }}
      const months = uniqueSorted([
        ...liqByMonth.keys(),
        ...despByMonth.keys()
      ].filter(m => m >= CAIXA_INICIO));
      let caixa = 0;
      const serie = [];
      for (const m of months) {{
        const resultadoMes = (liqByMonth.get(m) || 0) - (despByMonth.get(m) || 0);
        caixa += resultadoMes;
        serie.push({{ m, resultado: resultadoMes, caixa }});
      }}
      return {{ caixa, serie }};
    }}

    function fillSelect(id, values, allLabel) {{
      const el = document.getElementById(id);
      const current = el.value;
      el.innerHTML = `<option value="">${{allLabel}}</option>` +
        values.map(v => `<option value="${{v.replaceAll('"', '&quot;')}}">${{v}}</option>`).join('');
      if ([...el.options].some(o => o.value === current)) el.value = current;
    }}

    function isAtivo(seg) {{
      return String(seg || '').trim().toLowerCase() === 'ativo';
    }}

    function baseRows() {{
      // Segmento Ativo sempre excluído da análise
      return allRows().filter(r => !isAtivo(r.seg));
    }}

    function fillCheckboxes(boxId, values, name, selectedSet = null, labelFn = null) {{
      const box = document.getElementById(boxId);
      const prev = selectedSet || new Set(
        [...box.querySelectorAll('input[type=checkbox]:checked')].map(i => i.value)
      );
      box.innerHTML = values.map((v, idx) => {{
        const id = `${{name}}_${{idx}}`;
        const checked = prev.size === 0 ? '' : (prev.has(v) ? 'checked' : '');
        const label = labelFn ? labelFn(v) : v;
        return `<label for="${{id}}"><input type="checkbox" id="${{id}}" name="${{name}}" value="${{String(v).replaceAll('"', '&quot;')}}" ${{checked}} /> ${{label}}</label>`;
      }}).join('');
      box.querySelectorAll('input[type=checkbox]').forEach(inp => {{
        inp.addEventListener('change', () => {{ state.page = 0; refresh(); }});
      }});
    }}

    function checkedValues(name) {{
      return [...document.querySelectorAll(`input[name="${{name}}"]:checked`)].map(i => i.value);
    }}

    function setAllChecks(name, on) {{
      document.querySelectorAll(`input[name="${{name}}"]`).forEach(i => {{ i.checked = on; }});
      state.page = 0;
      refresh();
    }}

    function toggleCheckValue(name, value) {{
      const inputs = [...document.querySelectorAll(`input[name="${{name}}"]`)];
      const target = inputs.find(i => i.value === value);
      if (!target) return;
      target.checked = !target.checked;
      state.page = 0;
      refresh();
    }}

    function initFilters() {{
      const usable = ROWS.filter(r => !isAtivo(r.seg));
      const dates = usable.map(r => r.d).filter(Boolean).sort();
      if (dates.length) {{
        document.getElementById('fInicio').value = dates[0];
        document.getElementById('fFim').value = dates[dates.length - 1];
        document.getElementById('fInicio').min = dates[0];
        document.getElementById('fInicio').max = dates[dates.length - 1];
        document.getElementById('fFim').min = dates[0];
        document.getElementById('fFim').max = dates[dates.length - 1];
      }}
      const segs = uniqueSorted(usable.map(r => r.seg));
      const monthsFat = usable.map(r => ymOf(r.d)).filter(Boolean);
      const monthsDesp = DESPESAS.map(d => d.m).filter(Boolean);
      // Meses mais recentes primeiro na barra de seleção
      const months = uniqueSortedDesc([...monthsFat, ...monthsDesp]);
      const cats = uniqueSorted(DESPESAS.map(d => d.cat));
      fillCheckboxes('fSegmentoBox', segs, 'seg');
      fillCheckboxes('fMesBox', months, 'mes', null, fmtMonthLabel);
      fillCheckboxes('fDespCatBox', cats, 'despcat');
      fillSelect('fCliente', uniqueSorted(usable.map(r => r.c)), 'Todos');
      fillSelect('fUF', uniqueSorted(usable.map(r => r.uf)), 'Todas');
      fillSelect('fMaterial', uniqueSorted(usable.map(r => r.mat)), 'Todos');
      saveManualCosts({{ showPersistBar: false }});
    }}

    function readFilters() {{
      return {{
        inicio: document.getElementById('fInicio').value || null,
        fim: document.getElementById('fFim').value || null,
        segmentos: checkedValues('seg'),
        cliente: document.getElementById('fCliente').value || null,
        uf: document.getElementById('fUF').value || null,
        material: document.getElementById('fMaterial').value || null,
        status: document.getElementById('fStatus').value || null,
        lucroFaixa: document.getElementById('fLucroFaixa').value || null,
        busca: (document.getElementById('fBusca').value || '').trim().toLowerCase(),
        meses: checkedValues('mes'),
        despCats: checkedValues('despcat'),
        topN: Number(document.getElementById('fTopN').value || 0),
        pageSize: Number(document.getElementById('fPageSize').value || 50),
      }};
    }}

    function applyDespesaFilters(filters) {{
      const f = filters || readFilters();
      return DESPESAS.filter(d => {{
        if (f.meses && f.meses.length && !f.meses.includes(d.m)) return false;
        if (f.despCats && f.despCats.length && !f.despCats.includes(d.cat)) return false;
        if (f.inicio && d.d && d.d < f.inicio) return false;
        if (f.fim && d.d && d.d > f.fim) return false;
        if (f.busca) {{
          const blob = `${{d.f || ''}} ${{d.h || ''}} ${{d.cat || ''}} ${{d.sub || ''}}`.toLowerCase();
          if (!blob.includes(f.busca)) return false;
        }}
        return true;
      }});
    }}

    const LUCRO_FAIXA_LABEL = {{
      '': 'Todas',
      lt10: 'Abaixo de 10%',
      '11-30': '11% a 30%',
      gt30: 'Acima de 30%',
      na: 'Sem % (incompleto)'
    }};

    function inLucroFaixa(p, faixa) {{
      if (!faixa) return true;
      if (faixa === 'na') return p == null;
      if (p == null) return false;
      // Abaixo de 10% (inclui prejuízo); 10% entra na faixa intermediária para não ficar sem faixa
      if (faixa === 'lt10') return p < 0.10;
      if (faixa === '11-30') return p >= 0.10 && p <= 0.30;
      if (faixa === 'gt30') return p > 0.30;
      return true;
    }}

    function syncFaixaButtons(faixa) {{
      const value = faixa || '';
      document.querySelectorAll('#faixaLucroBar button[data-faixa]').forEach(btn => {{
        btn.classList.toggle('active', (btn.getAttribute('data-faixa') || '') === value);
      }});
      const sel = document.getElementById('fLucroFaixa');
      if (sel && sel.value !== value && [...sel.options].some(o => o.value === value)) {{
        sel.value = value;
      }}
    }}

    const CLIENTE_FAIXA_LABEL = {{
      '': 'Todas',
      lte30: 'Até 30%',
      '31-50': '31% a 50%',
      gt51: 'Acima de 51%'
    }};

    function inLucroFaixaCliente(p, faixa) {{
      if (!faixa) return true;
      if (p == null) return false;
      // Negativo até 30% (inclusive)
      if (faixa === 'lte30') return p <= 0.30;
      if (faixa === '31-50') return p >= 0.31 && p <= 0.50;
      if (faixa === 'gt51') return p >= 0.51;
      return true;
    }}

    function syncFaixaClienteButtons(faixa) {{
      const value = faixa || '';
      document.querySelectorAll('#faixaClienteBar button[data-faixa]').forEach(btn => {{
        btn.classList.toggle('active', (btn.getAttribute('data-faixa') || '') === value);
      }});
    }}

    function applyFilters(baseFilters) {{
      const f = baseFilters || readFilters();
      return baseRows().filter(r => {{
        if (f.inicio && r.d && r.d < f.inicio) return false;
        if (f.fim && r.d && r.d > f.fim) return false;
        if (f.inicio && !r.d) return false;
        if (f.segmentos && f.segmentos.length && !f.segmentos.includes(r.seg)) return false;
        if (f.cliente && r.c !== f.cliente) return false;
        if (f.uf && r.uf !== f.uf) return false;
        if (f.material && r.mat !== f.material) return false;
        if (f.status === 'com_custo') {{
          if (!(r.st === 'ok' || r.st === 'manual')) return false;
        }} else if (f.status && r.st !== f.status) {{
          return false;
        }}
        if (!inLucroFaixa(r.p, f.lucroFaixa)) return false;
        if (f.meses && f.meses.length && !f.meses.includes(ymOf(r.d))) return false;
        if (f.busca) {{
          const blob = `${{r.c || ''}} ${{r.cod || ''}} ${{r.desc || ''}} ${{r.n || ''}}`.toLowerCase();
          if (!blob.includes(f.busca)) return false;
        }}
        return true;
      }});
    }}

    function aggregateMonth(rows, field) {{
      const map = new Map();
      for (const r of rows) {{
        const ym = ymOf(r.d);
        if (!ym) continue;
        const val = r[field];
        if (val == null) continue;
        map.set(ym, (map.get(ym) || 0) + val);
      }}
      const labels = [...map.keys()].sort();
      return {{ labels, values: labels.map(k => map.get(k)) }};
    }}

    function aggregateBy(rows, key, field) {{
      const map = new Map();
      for (const r of rows) {{
        const k = r[key] || 'N/D';
        const val = r[field];
        if (val == null) continue;
        map.set(k, (map.get(k) || 0) + val);
      }}
      return [...map.entries()].sort((a,b) => b[1] - a[1]);
    }}

    function updateKpis(rows, despesas, filters) {{
      let venda = 0, custo = 0, liq = 0, frete = 0, imposto = 0, ok = 0, manual = 0;
      for (const r of rows) {{
        if (r.v != null) venda += r.v;
        if (r.ct != null) custo += r.ct;
        if (r.l != null) liq += r.l;
        if (r.f != null) frete += r.f;
        if (r.i != null) imposto += r.i;
        if (r.st === 'ok') ok += 1;
        if (r.st === 'manual') manual += 1;
      }}
      let desp = 0;
      for (const d of despesas) {{
        if (d.v != null) desp += d.v;
      }}
      const resultado = liq - desp;
      const pctOfSales = (v) => (venda > 0 ? pct(v / venda) : '—');
      document.getElementById('kpiVenda').textContent = money(venda);
      const mesesSel = (filters && filters.meses) || [];
      const mesHint = mesesSel.length ? ` · ${{fmtMonthsList(mesesSel)}}` : '';
      document.getElementById('kpiVendaPct').textContent = venda > 0 ? `100% da venda${{mesHint}}` : '—';
      document.getElementById('kpiCusto').textContent = money(custo);
      document.getElementById('kpiCustoPct').textContent = pctOfSales(custo);
      document.getElementById('kpiLiq').textContent = money(liq);
      document.getElementById('kpiLiqPct').textContent = pctOfSales(liq);
      document.getElementById('kpiDesp').textContent = money(desp);
      document.getElementById('kpiDespPct').textContent = pctOfSales(desp);
      const elRes = document.getElementById('kpiResult');
      elRes.textContent = money(resultado);
      elRes.style.color = resultado < 0 ? '#ffd0d0' : '#ffffff';
      const elResPct = document.getElementById('kpiResultPct');
      elResPct.textContent = pctOfSales(resultado);
      elResPct.style.color = resultado < 0 ? '#ffd0d0' : 'rgba(247,250,252,.82)';

      const {{ caixa, serie }} = computeCaixaAcumulado();
      const elCaixa = document.getElementById('kpiCaixa');
      elCaixa.textContent = money(caixa);
      elCaixa.style.color = caixa < 0 ? '#ffd0d0' : '#ffffff';
      const elCaixaPct = document.getElementById('kpiCaixaPct');
      const last = serie.length ? serie[serie.length - 1] : null;
      elCaixaPct.textContent = last
        ? `Desde jul/2026 · até ${{last.m}}`
        : 'Desde jul/2026';
      elCaixaPct.style.color = caixa < 0 ? '#ffd0d0' : 'rgba(247,250,252,.82)';
      state.caixaSerie = serie;

      document.getElementById('kpiItens').textContent =
        rows.length.toLocaleString('pt-BR') +
        ` (${{ok.toLocaleString('pt-BR')}} ok · ${{despesas.length}} desp.)`;
    }}

    function renderDespesas(despesas, filters) {{
      const byCat = new Map();
      let total = 0;
      for (const d of despesas) {{
        const k = d.cat || 'Outros';
        byCat.set(k, (byCat.get(k) || 0) + (d.v || 0));
        total += (d.v || 0);
      }}
      const ranked = [...byCat.entries()].sort((a,b) => b[1] - a[1]);
      const labels = ranked.length ? ranked.map(x => x[0]) : ['Sem despesas'];
      const values = ranked.length ? ranked.map(x => x[1]) : [0];

      upsertChart('chartDespesas', {{
        type: 'bar',
        data: {{
          labels,
          datasets: [{{
            data: values,
            backgroundColor: labels.map(x => (filters.despCats || []).includes(x) ? '#c45c26' : 'rgba(31,111,120,0.88)'),
            borderRadius: 7,
            maxBarThickness: 34
          }}]
        }},
        options: {{
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          layout: {{ padding: {{ right: 56 }} }},
          onClick: (evt, els) => {{
            if (!els.length || !ranked.length) return;
            toggleCheckValue('despcat', ranked[els[0].index][0]);
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{ callbacks: {{ label: (c) => money(c.raw) }} }},
            ...dataLabelsConfig({{ horizontal: true, count: labels.length }})
          }},
          scales: {{
            x: {{
              beginAtZero: true,
              grace: '12%',
              grid: {{ color: 'rgba(20,33,43,0.06)' }},
              ticks: {{ callback: (v) => 'R$ ' + (v/1000).toLocaleString('pt-BR') + ' mil' }}
            }},
            y: {{ grid: {{ display: false }} }}
          }}
        }}
      }});

      const tbResumo = document.getElementById('tblDespResumo');
      // detalhe por categoria + subcategoria
      const bySub = new Map();
      for (const d of despesas) {{
        const key = `${{d.cat || 'Outros'}}||${{d.sub || ''}}`;
        bySub.set(key, (bySub.get(key) || 0) + (d.v || 0));
      }}
      const subRanked = [...bySub.entries()]
        .map(([k, v]) => {{
          const [cat, sub] = k.split('||');
          return {{ cat, sub, v }};
        }})
        .sort((a,b) => b.v - a.v);

      tbResumo.innerHTML = subRanked.map(r => `
        <tr>
          <td>${{r.cat}}</td>
          <td>${{r.sub || '—'}}</td>
          <td>${{money(r.v)}}</td>
          <td>${{total ? pct(r.v / total) : '—'}}</td>
        </tr>
      `).join('') || `<tr><td colspan="4">Nenhuma despesa no filtro atual.</td></tr>`;

      const tb = document.getElementById('tblDespesas');
      const detalhe = [...despesas].sort((a,b) => {{
        const ma = a.m || '';
        const mb = b.m || '';
        if (ma !== mb) return mb.localeCompare(ma);
        return (b.v || 0) - (a.v || 0);
      }});
      tb.innerHTML = detalhe.map(d => `
        <tr>
          <td>${{d.m || '—'}}</td>
          <td>${{d.f || '—'}}</td>
          <td>${{d.h || '—'}}</td>
          <td>${{d.cat || '—'}}</td>
          <td>${{d.st || '—'}}</td>
          <td>${{money(d.v)}}</td>
        </tr>
      `).join('') || `<tr><td colspan="6">Nenhuma despesa no filtro atual.</td></tr>`;
    }}

    function statusLabel(st) {{
      if (st === 'ok') return '<span class="status-pill status-ok">ok</span>';
      if (st === 'manual') return '<span class="status-pill status-manual">manual</span>';
      return '<span class="status-pill status-inc">incompleto</span>';
    }}

    function setManualCost(id, value) {{
      const key = String(id);
      if (value == null) {{
        delete state.manualCosts[key];
      }} else {{
        state.manualCosts[key] = value;
      }}
      // Salva no navegador + pede para baixar o arquivo (persistência real)
      saveManualCosts({{ showPersistBar: true, autoJsonBackup: true }});
      refresh();
    }}

    function moneyShort(v, compact = false) {{
      if (v == null || Number.isNaN(v)) return '';
      const sign = v < 0 ? '-' : '';
      const abs = Math.abs(v);
      if (abs >= 1000000) {{
        return sign + (compact ? '' : 'R$ ') + (abs / 1000000).toLocaleString('pt-BR', {{ maximumFractionDigits: 1 }}) + ' mi';
      }}
      if (abs >= 1000) {{
        return sign + (compact ? '' : 'R$ ') + (abs / 1000).toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }}) + ' mil';
      }}
      return (compact ? '' : 'R$ ') + abs.toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }});
    }}

    function dataLabelsConfig({{ horizontal = false, count = 0 }} = {{}}) {{
      const dense = !horizontal && count > 12;
      // Barras verticais: rótulo DENTRO da coluna (evita corte fora do gráfico)
      // Barras horizontais: rótulo à direita
      return {{
        datalabels: {{
          display: (ctx) => {{
            const value = ctx.dataset.data[ctx.dataIndex];
            return value != null && Number(value) !== 0;
          }},
          formatter: (value) => moneyShort(value, dense),
          color: (ctx) => {{
            if (horizontal) return '#14212b';
            return '#ffffff';
          }},
          backgroundColor: (ctx) => horizontal ? 'rgba(255,255,255,0.9)' : 'rgba(20,33,43,0.28)',
          borderRadius: 4,
          padding: dense ? {{ top: 1, bottom: 1, left: 2, right: 2 }} : {{ top: 2, bottom: 2, left: 4, right: 4 }},
          anchor: horizontal ? 'end' : 'center',
          align: horizontal ? 'right' : 'center',
          offset: horizontal ? 6 : 0,
          clamp: false,
          clip: false,
          font: {{
            family: 'IBM Plex Sans',
            weight: '700',
            size: dense ? 9 : 11
          }},
          rotation: dense ? -90 : 0
        }}
      }};
    }}

    function upsertChart(id, config) {{
      // Recria o gráfico para garantir que os rótulos de dados sejam aplicados
      if (state.charts[id]) {{
        state.charts[id].destroy();
      }}
      state.charts[id] = new Chart(document.getElementById(id), config);
      return state.charts[id];
    }}

    function renderCharts(rows, filters) {{
      const mensalVenda = aggregateMonth(rows, 'v');
      const mensalLucro = aggregateMonth(rows, 'l');
      const segs = aggregateBy(rows, 'seg', 'v').slice(0, 8);
      const segsTotal = rows.reduce((acc, r) => acc + (r.v || 0), 0);
      const ufs = aggregateBy(rows, 'uf', 'v').slice(0, 8);

      upsertChart('chartVendaMensal', {{
        type: 'bar',
        data: {{
          labels: mensalVenda.labels.map(fmtMonthLabel),
          datasets: [{{
            label: 'Venda mensal',
            data: mensalVenda.values,
            backgroundColor: mensalVenda.labels.map(l => (filters.meses || []).includes(l) ? '#c45c26' : 'rgba(31,111,120,0.88)'),
            borderRadius: 7,
            maxBarThickness: 42
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          layout: {{ padding: {{ top: 12, right: 8, bottom: 4 }} }},
          onClick: (evt, els) => {{
            if (!els.length) return;
            toggleCheckValue('mes', mensalVenda.labels[els[0].index]);
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                title: (items) => {{
                  const i = items[0] && items[0].dataIndex;
                  return i == null ? '' : fmtMonthLabel(mensalVenda.labels[i]);
                }},
                label: (c) => 'Venda: ' + money(c.raw)
              }}
            }},
            ...dataLabelsConfig({{ count: mensalVenda.labels.length }})
          }},
          scales: {{
            x: {{ grid: {{ display: false }} }},
            y: {{
              beginAtZero: true,
              grace: '8%',
              grid: {{ color: 'rgba(20,33,43,0.06)' }},
              ticks: {{ callback: (v) => 'R$ ' + (v/1000).toLocaleString('pt-BR') + ' mil' }}
            }}
          }}
        }}
      }});

      upsertChart('chartLucroMensal', {{
        type: 'bar',
        data: {{
          labels: mensalLucro.labels.map(fmtMonthLabel),
          datasets: [{{
            label: 'Venda líquida',
            data: mensalLucro.values,
            backgroundColor: mensalLucro.values.map(v => v < 0 ? 'rgba(161,40,40,0.85)' : 'rgba(196,92,38,0.88)'),
            borderRadius: 7,
            maxBarThickness: 36
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          layout: {{ padding: {{ top: 12, right: 8, bottom: 4 }} }},
          onClick: (evt, els) => {{
            if (!els.length) return;
            toggleCheckValue('mes', mensalLucro.labels[els[0].index]);
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                title: (items) => {{
                  const i = items[0] && items[0].dataIndex;
                  return i == null ? '' : fmtMonthLabel(mensalLucro.labels[i]);
                }},
                label: (c) => money(c.raw)
              }}
            }},
            ...dataLabelsConfig({{ count: mensalLucro.labels.length }})
          }},
          scales: {{
            x: {{ grid: {{ display: false }} }},
            y: {{
              beginAtZero: true,
              grace: '8%',
              grid: {{ color: 'rgba(20,33,43,0.06)' }},
              ticks: {{ callback: (v) => 'R$ ' + (v/1000).toLocaleString('pt-BR') + ' mil' }}
            }}
          }}
        }}
      }});

      const segLabelsCfg = dataLabelsConfig({{ horizontal: true, count: segs.length }});
      segLabelsCfg.datalabels.formatter = (value) => {{
        const share = segsTotal > 0 ? pct(value / segsTotal) : '—';
        return moneyShort(value) + ' (' + share + ')';
      }};
      segLabelsCfg.datalabels.padding = {{ top: 2, bottom: 2, left: 5, right: 5 }};

      upsertChart('chartSegmento', {{
        type: 'bar',
        data: {{
          labels: segs.map(x => x[0]),
          datasets: [{{
            label: 'Venda',
            data: segs.map(x => x[1]),
            backgroundColor: segs.map(x => (filters.segmentos || []).includes(x[0]) ? '#c45c26' : 'rgba(31,111,120,0.88)'),
            borderRadius: 7,
            maxBarThickness: 34
          }}]
        }},
        options: {{
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          layout: {{ padding: {{ right: 88 }} }},
          onClick: (evt, els) => {{
            if (!els.length) return;
            toggleCheckValue('seg', segs[els[0].index][0]);
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                label: (c) => {{
                  const share = segsTotal > 0 ? pct(c.raw / segsTotal) : '—';
                  return money(c.raw) + ' (' + share + ' da venda)';
                }}
              }}
            }},
            ...segLabelsCfg
          }},
          scales: {{
            x: {{
              grace: '22%',
              grid: {{ color: 'rgba(20,33,43,0.06)' }},
              ticks: {{ callback: (v) => 'R$ ' + (v/1000).toLocaleString('pt-BR') + ' mil' }}
            }},
            y: {{ grid: {{ display: false }} }}
          }}
        }}
      }});

      upsertChart('chartUF', {{
        type: 'bar',
        data: {{
          labels: ufs.map(x => x[0]),
          datasets: [{{
            data: ufs.map(x => x[1]),
            backgroundColor: ufs.map(x => x[0] === filters.uf ? '#c45c26' : 'rgba(31,111,120,0.85)'),
            borderRadius: 7,
            maxBarThickness: 34
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          layout: {{ padding: {{ top: 12, right: 8, bottom: 4 }} }},
          onClick: (evt, els) => {{
            if (!els.length) return;
            const label = ufs[els[0].index][0];
            const el = document.getElementById('fUF');
            el.value = el.value === label ? '' : label;
            refresh();
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{ callbacks: {{ label: (c) => money(c.raw) }} }},
            ...dataLabelsConfig({{ count: ufs.length }})
          }},
          scales: {{
            x: {{ grid: {{ display: false }} }},
            y: {{
              beginAtZero: true,
              grace: '8%',
              grid: {{ color: 'rgba(20,33,43,0.06)' }},
              ticks: {{ callback: (v) => 'R$ ' + (v/1000).toLocaleString('pt-BR') + ' mil' }}
            }}
          }}
        }}
      }});

      document.getElementById('mesNote').textContent = (filters.meses && filters.meses.length)
        ? `Meses ativos: ${{fmtMonthsList(filters.meses)}} · venda filtrada: ${{money(rows.reduce((a,r) => a + (r.v || 0), 0))}}`
        : 'Nenhum mês marcado. Marque os checkboxes ou clique nas colunas para filtrar.';
    }}

    function isEtiquetaSeg(seg) {{
      const s = String(seg || '').toLowerCase();
      return s.includes('etiqueta');
    }}

    function tipoEtiquetaOf(mat) {{
      const u = String(mat || '').trim().toUpperCase();
      if (!u) return 'Sem tipo';
      if (u === 'BOPP' || u.startsWith('BOPP') || u.includes('BOPP')) return 'Bopp';
      if (u === 'COUCHE' || u.startsWith('COUCHE') || u.includes('COUCHE') || u.includes('COUCHÊ')) return 'Couche';
      if (u === 'TERMICO' || u.startsWith('TERMICO') || u.includes('TÉRMIC') || u.includes('TERMIC') || u.includes('THERMAL')) return 'Termico';
      if (u === 'BOPP') return 'Bopp';
      return 'Outros';
    }}

    function syncTipoEtiquetaButtons(tipo) {{
      const value = tipo || '';
      document.querySelectorAll('#faixaTipoEtiqBar button[data-tipo]').forEach(btn => {{
        btn.classList.toggle('active', (btn.getAttribute('data-tipo') || '') === value);
      }});
    }}

    function renderCustoEtiquetas(rows, filters) {{
      const tipoFiltro = state.tipoEtiqueta || '';
      const etiq = rows.filter(r => isEtiquetaSeg(r.seg));
      const filtered = tipoFiltro
        ? etiq.filter(r => tipoEtiquetaOf(r.mat) === tipoFiltro)
        : etiq;

      // Resumo por tipo (gráfico: custo médio/rolo)
      const byTipo = new Map();
      for (const r of filtered) {{
        const tipo = tipoEtiquetaOf(r.mat);
        const cur = byTipo.get(tipo) || {{ tipo, comRolo: 0, somaRolo: 0, custo: 0 }};
        if (r.cr != null) {{
          cur.comRolo += 1;
          cur.somaRolo += r.cr;
        }}
        if (r.ct != null) cur.custo += r.ct;
        byTipo.set(tipo, cur);
      }}
      const rankedTipo = [...byTipo.values()]
        .map(x => ({{ ...x, medioRolo: x.comRolo ? x.somaRolo / x.comRolo : null }}))
        .sort((a, b) => (b.medioRolo || 0) - (a.medioRolo || 0));

      const labels = rankedTipo.length ? rankedTipo.map(x => x.tipo) : ['Sem etiquetas'];
      const values = rankedTipo.length ? rankedTipo.map(x => x.medioRolo || 0) : [0];
      const tipoLabelsCfg = dataLabelsConfig({{ horizontal: true, count: labels.length }});
      tipoLabelsCfg.datalabels.formatter = (value) => money(value);

      upsertChart('chartTipoEtiqueta', {{
        type: 'bar',
        data: {{
          labels,
          datasets: [{{
            label: 'Custo médio / rolo',
            data: values,
            backgroundColor: labels.map(t => (tipoFiltro && t === tipoFiltro) ? '#c45c26' : 'rgba(31,111,120,0.88)'),
            borderRadius: 7,
            maxBarThickness: 34
          }}]
        }},
        options: {{
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          layout: {{ padding: {{ right: 72 }} }},
          onClick: (evt, els) => {{
            if (!els.length) return;
            const tipo = labels[els[0].index];
            if (!tipo || tipo === 'Sem etiquetas') return;
            state.tipoEtiqueta = (state.tipoEtiqueta === tipo) ? '' : tipo;
            refresh();
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                label: (c) => 'Custo médio/rolo: ' + money(c.raw)
              }}
            }},
            ...tipoLabelsCfg
          }},
          scales: {{
            x: {{
              grace: '18%',
              grid: {{ color: 'rgba(20,33,43,0.06)' }},
              ticks: {{ callback: (v) => 'R$ ' + Number(v).toLocaleString('pt-BR', {{ maximumFractionDigits: 0 }}) }}
            }},
            y: {{ grid: {{ display: false }} }}
          }}
        }}
      }});

      // Resumo por cliente (custo médio/rolo)
      const byCli = new Map();
      for (const r of filtered) {{
        const nome = r.c || 'N/D';
        const cur = byCli.get(nome) || {{ nome, itens: 0, comRolo: 0, somaRolo: 0, custo: 0 }};
        cur.itens += 1;
        if (r.cr != null) {{
          cur.comRolo += 1;
          cur.somaRolo += r.cr;
        }}
        if (r.ct != null) cur.custo += r.ct;
        byCli.set(nome, cur);
      }}
      const rankedCli = [...byCli.values()]
        .map(x => ({{
          ...x,
          medioRolo: x.comRolo ? x.somaRolo / x.comRolo : null
        }}))
        .sort((a, b) => {{
          const ma = a.medioRolo, mb = b.medioRolo;
          if (ma == null && mb == null) return a.nome.localeCompare(b.nome, 'pt-BR');
          if (ma == null) return 1;
          if (mb == null) return -1;
          if (ma !== mb) return ma - mb; // crescente: mais fácil achar custo/rolo
          return a.nome.localeCompare(b.nome, 'pt-BR');
        }});

      const topN = Number(filters.topN || 0);
      const cliView = topN > 0 ? rankedCli.slice(0, topN) : rankedCli;
      const tbCli = document.getElementById('tblCustoRoloCliente');
      tbCli.innerHTML = cliView.map(c => `
        <tr class="item-row ${{filters.cliente === c.nome ? 'active' : ''}}" data-cliente="${{c.nome.replaceAll('"', '&quot;')}}">
          <td>${{c.nome}}</td>
          <td>${{c.comRolo.toLocaleString('pt-BR')}}</td>
          <td><strong>${{money(c.medioRolo)}}</strong></td>
          <td>${{money(c.custo)}}</td>
        </tr>
      `).join('') || `<tr><td colspan="4">Nenhuma etiqueta com custo/rolo no filtro atual.</td></tr>`;

      if (rankedCli.length > cliView.length) {{
        tbCli.innerHTML += `<tr><td colspan="4">Mostrando ${{cliView.length}} de ${{rankedCli.length}} clientes. Aumente o Top N ou filtre.</td></tr>`;
      }}

      tbCli.querySelectorAll('tr[data-cliente]').forEach(tr => {{
        tr.addEventListener('click', () => {{
          toggleClienteFilter(tr.getAttribute('data-cliente'));
        }});
      }});

      // Detalhe: Cliente → NF → custo/rolo
      const detalhe = [...filtered].sort((a, b) => {{
        const ca = a.c || '';
        const cb = b.c || '';
        if (ca !== cb) return ca.localeCompare(cb, 'pt-BR');
        const na = String(a.n || '');
        const nb = String(b.n || '');
        if (na !== nb) return na.localeCompare(nb, 'pt-BR');
        const cra = a.cr == null ? Infinity : a.cr;
        const crb = b.cr == null ? Infinity : b.cr;
        return cra - crb;
      }});

      const tb = document.getElementById('tblCustoEtiqueta');
      const maxRows = 250;
      const pageRows = detalhe.slice(0, maxRows);
      tb.innerHTML = pageRows.map(r => {{
        const tipo = tipoEtiquetaOf(r.mat);
        const tipoLabel = tipo === 'Termico' ? 'Térmico' : tipo;
        const matDesc = r.mat && r.mat !== tipo && r.mat !== 'Bopp' && r.mat !== 'Couche' && r.mat !== 'Termico'
          ? r.mat
          : (r.desc || '—');
        return `
        <tr class="item-row" data-cliente="${{(r.c || '').replaceAll('"', '&quot;')}}" data-nf="${{(r.n || '').replaceAll('"', '&quot;')}}" data-tipo="${{tipo}}">
          <td>${{r.c || '—'}}</td>
          <td>${{r.n || '—'}}</td>
          <td>${{tipoLabel}}</td>
          <td title="${{(r.desc || '').replaceAll('"', '&quot;')}}">${{matDesc}}</td>
          <td><strong>${{money(r.cr)}}</strong></td>
          <td>${{money(r.ct)}}</td>
          <td>${{money(r.v)}}</td>
          <td class="${{(r.p ?? 0) < 0 ? 'neg' : 'pos'}}">${{pct(r.p)}}</td>
        </tr>`;
      }}).join('') || `<tr><td colspan="8">Nenhuma etiqueta no filtro atual. Marque o segmento de etiqueta ou limpe filtros.</td></tr>`;

      if (detalhe.length > maxRows) {{
        tb.innerHTML += `<tr><td colspan="8">Mostrando ${{maxRows}} de ${{detalhe.length.toLocaleString('pt-BR')}} itens. Filtre por cliente ou tipo.</td></tr>`;
      }}

      tb.querySelectorAll('tr[data-cliente]').forEach(tr => {{
        tr.addEventListener('click', () => {{
          const nome = tr.getAttribute('data-cliente');
          if (nome) toggleClienteFilter(nome);
        }});
      }});

      syncTipoEtiquetaButtons(tipoFiltro);
    }}

    function setClienteFilter(nome) {{
      const el = document.getElementById('fCliente');
      const next = nome || '';
      // Garante que a opção exista no select (evita value “fantasma”)
      if (next && el && ![...el.options].some(o => o.value === next)) {{
        const opt = document.createElement('option');
        opt.value = next;
        opt.textContent = next;
        el.appendChild(opt);
      }}
      if (el) el.value = next;
      state.selectedCliente = next || null;
    }}

    function clearClienteFilter() {{
      setClienteFilter('');
      state.page = 0;
      refresh();
    }}

    function toggleClienteFilter(nome) {{
      if (!nome) {{
        clearClienteFilter();
        return;
      }}
      const atual = document.getElementById('fCliente').value || state.selectedCliente || '';
      setClienteFilter(atual === nome ? '' : nome);
      state.page = 0;
      refresh();
    }}

    function renderClientes(rows, filters) {{
      // Lista de clientes sem o filtro de cliente, para poder voltar / trocar de cliente
      const baseForList = applyFilters({{ ...filters, cliente: null }});
      const map = new Map();
      for (const r of baseForList) {{
        const k = r.c || 'N/D';
        const cur = map.get(k) || {{ venda: 0, liq: 0, custo: 0 }};
        if (r.v != null) cur.venda += r.v;
        if (r.l != null) cur.liq += r.l;
        if (r.ct != null) cur.custo += r.ct;
        map.set(k, cur);
      }}
      const faixaCli = state.clienteLucroFaixa || '';
      const allRanked = [...map.entries()]
        .map(([nome, v]) => ({{
          nome,
          ...v,
          lucroPct: v.custo > 0 ? v.liq / v.custo : null
        }}))
        .filter(c => inLucroFaixaCliente(c.lucroPct, faixaCli))
        .sort((a, b) => {{
          // Com filtro de faixa: ordem crescente de % lucro
          if (faixaCli) {{
            const pa = a.lucroPct, pb = b.lucroPct;
            if (pa == null && pb == null) return a.nome.localeCompare(b.nome, 'pt-BR');
            if (pa == null) return 1;
            if (pb == null) return -1;
            if (pa !== pb) return pa - pb;
            return b.venda - a.venda;
          }}
          return b.venda - a.venda;
        }});
      const topN = Number(filters.topN || 0);
      const ranked = topN > 0 ? allRanked.slice(0, topN) : allRanked;

      const clienteAtivo = filters.cliente || '';
      const btnLimpar = document.getElementById('btnLimparCliente');
      if (btnLimpar) {{
        btnLimpar.style.display = clienteAtivo ? 'inline-flex' : 'none';
        btnLimpar.textContent = clienteAtivo
          ? `Ver todos (limpo: ${{clienteAtivo.length > 28 ? clienteAtivo.slice(0, 28) + '…' : clienteAtivo}})`
          : 'Ver todos os clientes';
      }}

      const meta = document.getElementById('clientesMeta');
      if (meta) {{
        const faixaTxt = faixaCli ? ` · faixa ${{CLIENTE_FAIXA_LABEL[faixaCli] || faixaCli}}` : '';
        const limTxt = topN > 0 && allRanked.length > ranked.length
          ? ` · mostrando ${{ranked.length}} de ${{allRanked.length}}`
          : ` · ${{ranked.length}} cliente(s)`;
        meta.textContent = `Clique na linha para filtrar; clique de novo ou em “Ver todos” para limpar${{faixaTxt}}${{limTxt}}.`;
      }}

      const tb = document.getElementById('tblClientes');
      tb.innerHTML = ranked.map(c => `
        <tr class="item-row ${{clienteAtivo === c.nome ? 'active' : ''}}" data-cliente="${{c.nome.replaceAll('"', '&quot;')}}">
          <td>${{c.nome}}</td>
          <td>${{money(c.venda)}}</td>
          <td class="${{c.liq < 0 ? 'neg' : 'pos'}}">${{money(c.liq)}}</td>
          <td class="${{(c.lucroPct ?? 0) < 0 ? 'neg' : 'pos'}}">${{pct(c.lucroPct)}}</td>
        </tr>
      `).join('') || `<tr><td colspan="4">Nenhum cliente na faixa ${{CLIENTE_FAIXA_LABEL[faixaCli] || 'selecionada'}}.</td></tr>`;

      syncFaixaClienteButtons(faixaCli);

      tb.querySelectorAll('tr[data-cliente]').forEach(tr => {{
        tr.addEventListener('click', () => {{
          toggleClienteFilter(tr.getAttribute('data-cliente'));
        }});
      }});
    }}

    function renderItens(rows, filters) {{
      const sorted = [...rows].sort((a,b) => {{
        // incompletos e manuais primeiro facilitam a digitação
        const rank = (st) => st === 'inc' ? 0 : st === 'manual' ? 1 : 2;
        const ra = rank(a.st), rb = rank(b.st);
        if (ra !== rb) return ra - rb;
        const da = a.d || '';
        const db = b.d || '';
        if (da !== db) return db.localeCompare(da);
        return (b.v || 0) - (a.v || 0);
      }});
      const pageSize = filters.pageSize;
      const pages = Math.max(1, Math.ceil(sorted.length / pageSize));
      if (state.page >= pages) state.page = pages - 1;
      if (state.page < 0) state.page = 0;
      const start = state.page * pageSize;
      const pageRows = sorted.slice(start, start + pageSize);

      document.getElementById('itensMeta').textContent =
        `${{sorted.length.toLocaleString('pt-BR')}} itens · página ${{state.page + 1}} de ${{pages}} · digite o custo nos incompletos`;

      const tb = document.getElementById('tblItens');
      tb.innerHTML = pageRows.map(r => {{
        const editable = r.st === 'inc' || r.st === 'manual';
        const costCell = editable
          ? `<div>
              <input class="cost-input" data-id="${{r.id}}" inputmode="decimal"
                placeholder="0,00" value="${{formatInputMoney(r.manual ? r.ct : state.manualCosts[String(r.id)])}}" />
              <div class="cost-actions">
                <button type="button" class="btn-mini btn-save-cost" data-id="${{r.id}}">Salvar</button>
                ${{r.st === 'manual' ? `<button type="button" class="btn-mini danger btn-clear-cost" data-id="${{r.id}}">Limpar</button>` : ''}}
              </div>
            </div>`
          : money(r.ct);
        return `
        <tr class="item-row" data-cliente="${{(r.c || '').replaceAll('"', '&quot;')}}" data-seg="${{(r.seg || '').replaceAll('"', '&quot;')}}">
          <td>${{fmtDate(r.d)}}</td>
          <td>${{r.n || '—'}}</td>
          <td>${{r.c || '—'}}</td>
          <td>${{r.seg || '—'}}</td>
          <td title="${{(r.desc || '').replaceAll('"', '&quot;')}}">${{r.desc || '—'}}</td>
          <td>${{money(r.v)}}</td>
          <td class="cost-cell">${{costCell}}</td>
          <td class="${{(r.l ?? 0) < 0 ? 'neg' : ''}}">${{money(r.l)}}</td>
          <td class="${{(r.p ?? 0) < 0 ? 'neg' : 'pos'}}">${{pct(r.p)}}</td>
          <td>${{statusLabel(r.st)}}</td>
        </tr>`;
      }}).join('') || `<tr><td colspan="10">Nenhum item para os filtros atuais.</td></tr>`;

      tb.querySelectorAll('tr[data-cliente]').forEach(tr => {{
        tr.addEventListener('click', (ev) => {{
          if (ev.target.closest('.cost-cell')) return;
          const nome = tr.getAttribute('data-cliente');
          const seg = tr.getAttribute('data-seg');
          if (seg && !isAtivo(seg)) {{
            const inputs = [...document.querySelectorAll('input[name="seg"]')];
            inputs.forEach(i => {{ i.checked = (i.value === seg); }});
          }}
          if (nome) {{
            toggleClienteFilter(nome);
          }} else {{
            state.page = 0;
            refresh();
          }}
        }});
      }});

      tb.querySelectorAll('.btn-save-cost').forEach(btn => {{
        btn.addEventListener('click', (ev) => {{
          ev.stopPropagation();
          const id = btn.getAttribute('data-id');
          const input = tb.querySelector(`.cost-input[data-id="${{id}}"]`);
          const val = parseMoneyInput(input && input.value);
          if (val == null || val < 0) {{
            alert('Informe um custo válido (ex.: 12,50).');
            return;
          }}
          setManualCost(id, val);
        }});
      }});

      tb.querySelectorAll('.btn-clear-cost').forEach(btn => {{
        btn.addEventListener('click', (ev) => {{
          ev.stopPropagation();
          setManualCost(btn.getAttribute('data-id'), null);
        }});
      }});

      tb.querySelectorAll('.cost-input').forEach(input => {{
        input.addEventListener('click', (ev) => ev.stopPropagation());
        input.addEventListener('keydown', (ev) => {{
          if (ev.key === 'Enter') {{
            ev.preventDefault();
            const id = input.getAttribute('data-id');
            const val = parseMoneyInput(input.value);
            if (val == null || val < 0) {{
              alert('Informe um custo válido (ex.: 12,50).');
              return;
            }}
            setManualCost(id, val);
          }}
        }});
      }});
    }}

    function updateChips(filters) {{
      const chips = [];
      if (filters.inicio || filters.fim) chips.push(`Período: ${{fmtDate(filters.inicio)}} → ${{fmtDate(filters.fim)}}`);
      if (filters.segmentos && filters.segmentos.length) chips.push(`Segmento: ${{filters.segmentos.join(', ')}}`);
      if (filters.cliente) chips.push(`Cliente: ${{filters.cliente}}`);
      if (filters.uf) chips.push(`UF: ${{filters.uf}}`);
      if (filters.material) chips.push(`Material: ${{filters.material}}`);
      if (filters.status) chips.push(`Status: ${{filters.status}}`);
      if (filters.meses && filters.meses.length) chips.push(`Mês: ${{fmtMonthsList(filters.meses)}}`);
      if (filters.despCats && filters.despCats.length) chips.push(`Despesa: ${{filters.despCats.join(', ')}}`);
      if (filters.busca) chips.push(`Busca: ${{filters.busca}}`);
      if (filters.lucroFaixa) chips.push(`Lucro item: ${{LUCRO_FAIXA_LABEL[filters.lucroFaixa] || filters.lucroFaixa}}`);
      if (state.clienteLucroFaixa) chips.push(`Lucro cliente: ${{CLIENTE_FAIXA_LABEL[state.clienteLucroFaixa] || state.clienteLucroFaixa}}`);
      if (state.tipoEtiqueta) chips.push(`Tipo etiqueta: ${{state.tipoEtiqueta === 'Termico' ? 'Térmico' : state.tipoEtiqueta}}`);
      chips.push('Ativo excluído');
      const el = document.getElementById('activeChips');
      if (!chips.length) {{
        el.hidden = true;
        el.textContent = '';
        return;
      }}
      el.hidden = false;
      el.innerHTML = chips.map(c => `<span>${{c}}</span>`).join(' · ');
    }}

    function refresh() {{
      const filters = readFilters();
      state.selectedCliente = filters.cliente || null;
      const rows = applyFilters(filters);
      const despesas = applyDespesaFilters(filters);
      updateKpis(rows, despesas, filters);
      renderCharts(rows, filters);
      renderDespesas(despesas, filters);
      renderClientes(rows, filters);
      renderCustoEtiquetas(rows, filters);
      renderItens(rows, filters);
      syncFaixaButtons(filters.lucroFaixa);
      updateChips(filters);
    }}

    function clearFilters() {{
      initFilters();
      document.getElementById('fStatus').value = '';
      document.getElementById('fLucroFaixa').value = '';
      document.getElementById('fBusca').value = '';
      document.getElementById('fTopN').value = '0';
      document.getElementById('fPageSize').value = '50';
      document.getElementById('fCliente').value = '';
      document.getElementById('fUF').value = '';
      document.getElementById('fMaterial').value = '';
      document.querySelectorAll('input[name="seg"], input[name="mes"], input[name="despcat"]').forEach(i => {{ i.checked = false; }});
      state.selectedCliente = null;
      state.clienteLucroFaixa = '';
      state.tipoEtiqueta = '';
      state.page = 0;
      refresh();
    }}

    if (typeof ChartDataLabels !== 'undefined') {{
      Chart.register(ChartDataLabels);
    }} else {{
      console.warn('Plugin de rótulos de dados não carregou. Verifique a conexão com a internet.');
    }}
    Chart.defaults.font.family = 'IBM Plex Sans, sans-serif';
    Chart.defaults.color = '#2a3b49';

    document.getElementById('btnAplicar').addEventListener('click', () => {{ state.page = 0; refresh(); }});
    document.getElementById('btnLimpar').addEventListener('click', clearFilters);
    document.getElementById('btnPrev').addEventListener('click', () => {{ state.page -= 1; refresh(); }});
    document.getElementById('btnNext').addEventListener('click', () => {{ state.page += 1; refresh(); }});
    document.getElementById('faixaLucroBar').addEventListener('click', (ev) => {{
      const btn = ev.target.closest('button[data-faixa]');
      if (!btn) return;
      const value = btn.getAttribute('data-faixa') || '';
      document.getElementById('fLucroFaixa').value = value;
      state.page = 0;
      refresh();
    }});
    document.getElementById('faixaClienteBar').addEventListener('click', (ev) => {{
      if (ev.target.closest('#btnLimparCliente')) return;
      const btn = ev.target.closest('button[data-faixa]');
      if (!btn) return;
      state.clienteLucroFaixa = btn.getAttribute('data-faixa') || '';
      refresh();
    }});
    document.getElementById('btnLimparCliente').addEventListener('click', (ev) => {{
      ev.preventDefault();
      ev.stopPropagation();
      clearClienteFilter();
    }});
    document.getElementById('fCliente').addEventListener('change', () => {{
      state.selectedCliente = document.getElementById('fCliente').value || null;
    }});
    document.getElementById('faixaTipoEtiqBar').addEventListener('click', (ev) => {{
      const btn = ev.target.closest('button[data-tipo]');
      if (!btn) return;
      state.tipoEtiqueta = btn.getAttribute('data-tipo') || '';
      refresh();
    }});
    document.getElementById('btnClearManual').addEventListener('click', () => {{
      if (!Object.keys(state.manualCosts).length) {{
        alert('Não há custos manuais salvos.');
        return;
      }}
      if (confirm('Apagar todos os custos manuais salvos neste navegador e neste arquivo?')) {{
        state.manualCosts = {{}};
        saveManualCosts({{ showPersistBar: false }});
        const bar = document.getElementById('persistBar');
        if (bar) bar.classList.remove('show');
        refresh();
      }}
    }});
    document.getElementById('btnDownloadHtml').addEventListener('click', downloadHtmlWithCosts);
    document.getElementById('btnDownloadHtml2').addEventListener('click', downloadHtmlWithCosts);
    document.getElementById('btnDismissPersist').addEventListener('click', () => {{
      document.getElementById('persistBar').classList.remove('show');
    }});
    document.getElementById('btnLoadManual').addEventListener('click', () => {{
      document.getElementById('fileManual').click();
    }});
    document.getElementById('fileManual').addEventListener('change', async (ev) => {{
      const file = ev.target.files && ev.target.files[0];
      ev.target.value = '';
      if (!file) return;
      try {{
        const text = await file.text();
        let map = {{}};
        if (file.name.toLowerCase().endsWith('.csv')) {{
          const lines = text.split(/\\r?\\n/).filter(Boolean);
          lines.slice(1).forEach(line => {{
            const parts = line.split(';');
            if (parts.length >= 7) {{
              const id = parts[0];
              const custo = parseMoneyInput(parts[6]);
              if (id && custo != null) map[String(id)] = custo;
            }} else if (parts.length >= 2) {{
              const id = parts[0];
              const custo = parseMoneyInput(parts[1]);
              if (id && custo != null) map[String(id)] = custo;
            }}
          }});
        }} else {{
          map = normalizeCostMap(JSON.parse(text));
        }}
        if (!Object.keys(map).length) {{
          alert('Arquivo sem custos válidos.');
          return;
        }}
        state.manualCosts = {{ ...state.manualCosts, ...map }};
        saveManualCosts({{ showPersistBar: true }});
        refresh();
        alert(`Custos carregados: ${{Object.keys(map).length}}. Clique em “Baixar dashboard com meus custos” para fixar no arquivo.`);
      }} catch (e) {{
        alert('Não foi possível ler o arquivo. Use o JSON/CSV exportado por este dashboard.');
      }}
    }});
    document.getElementById('btnExportManual').addEventListener('click', () => {{
      const ids = Object.keys(state.manualCosts);
      if (!ids.length) {{
        alert('Não há custos manuais para exportar.');
        return;
      }}
      const byId = new Map(ROWS.map(r => [String(r.id), r]));
      const lines = [['id','numero_nf','cliente','codigo','descricao','venda','custo_manual']];
      ids.forEach(id => {{
        const r = byId.get(id) || {{}};
        lines.push([
          id,
          r.n || '',
          (r.c || '').replaceAll(';', ','),
          r.cod || '',
          (r.desc || '').replaceAll(';', ','),
          r.v != null ? String(r.v).replace('.', ',') : '',
          String(state.manualCosts[id]).replace('.', ',')
        ]);
      }});
      const csv = lines.map(row => row.join(';')).join('\\n');
      downloadBlob('custos_manuais_rbt.csv', csv, 'text/csv;charset=utf-8;');
      downloadManualJson(false);
    }});
    ['fInicio','fFim','fCliente','fUF','fMaterial','fStatus','fLucroFaixa','fTopN','fPageSize']
      .forEach(id => document.getElementById(id).addEventListener('change', () => {{ state.page = 0; refresh(); }}));
    document.getElementById('fBusca').addEventListener('input', () => {{
      clearTimeout(state._t);
      state._t = setTimeout(() => {{ state.page = 0; refresh(); }}, 250);
    }});
    document.getElementById('btnSegAll').addEventListener('click', () => setAllChecks('seg', true));
    document.getElementById('btnSegNone').addEventListener('click', () => setAllChecks('seg', false));
    document.getElementById('btnMesAll').addEventListener('click', () => setAllChecks('mes', true));
    document.getElementById('btnMesNone').addEventListener('click', () => setAllChecks('mes', false));
    document.getElementById('btnDespAll').addEventListener('click', () => setAllChecks('despcat', true));
    document.getElementById('btnDespNone').addEventListener('click', () => setAllChecks('despcat', false));

    initFilters();
    refresh();
  </script>
</body>
</html>
"""


def load_despesas(path: Path | None = None) -> list[dict]:
    candidates = []
    if path:
        candidates.append(Path(path))
    candidates.extend(
        [
            Path("Despesas_RBT_Normalizadas.xlsx"),
            Path("Despesas_RBT.xlsx"),
        ]
    )
    for p in candidates:
        if not p.exists():
            continue
        try:
            if p.name.endswith("Normalizadas.xlsx"):
                df = pd.read_excel(p, sheet_name="Despesas")
            else:
                from processar_despesas import processar

                df = processar(p)
            return build_despesa_rows(df)
        except Exception as exc:
            print(f"Aviso ao ler despesas ({p}): {exc}")
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera dashboard HTML interativo")
    parser.add_argument("--input", default="Relatorio_Custo_Faturamento_RBT.xlsx")
    parser.add_argument("--despesas", default="Despesas_RBT_Normalizadas.xlsx")
    parser.add_argument("--output", default="Dashboard_Custo_Faturamento_RBT.html")
    args = parser.parse_args()

    df = pd.read_excel(args.input, sheet_name="Relatorio")
    dts = pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce")
    if dts.notna().any():
        periodo = f"{dts.min().strftime('%d/%m/%Y')} a {dts.max().strftime('%d/%m/%Y')}"
    else:
        periodo = "Período não disponível"

    rows = build_rows(df)
    despesas = load_despesas(Path(args.despesas))
    html = render_html(rows, periodo, despesas)
    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard gerado: {out.resolve()}")
    print(
        f"Linhas embutidas: {len(rows)} | despesas: {len(despesas)} | "
        f"tamanho: {out.stat().st_size / 1024:.1f} KB"
    )


if __name__ == "__main__":
    main()
