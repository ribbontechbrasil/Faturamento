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
        dt = dts.loc[i]
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


def render_html(rows: list[dict], periodo_label: str) -> str:
    data_json = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))

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

    .kpi-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: .7rem; margin-top: 1rem; }}
    .kpi {{
      background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.14);
      border-radius: 14px; padding: .75rem .85rem;
    }}
    .kpi span {{ display: block; font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; color: rgba(247,250,252,.72); margin-bottom: .25rem; }}
    .kpi strong {{ font-family: Sora, sans-serif; font-size: clamp(1rem, 2vw, 1.35rem); font-weight: 600; }}

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
    @media (max-width: 640px) {{
      .kpi-grid, .filter-grid, .grid-2 {{ grid-template-columns: 1fr; }}
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
        <div class="kpi"><span>Venda</span><strong id="kpiVenda">—</strong></div>
        <div class="kpi"><span>Custo</span><strong id="kpiCusto">—</strong></div>
        <div class="kpi"><span>Venda líquida</span><strong id="kpiLiq">—</strong></div>
        <div class="kpi"><span>% Lucro</span><strong id="kpiLucro">—</strong></div>
        <div class="kpi"><span>Itens filtrados</span><strong id="kpiItens">—</strong></div>
      </div>
    </header>

    <section class="filters">
      <h2>Filtros</h2>
      <div class="filter-grid">
        <label>Data início<input type="date" id="fInicio" /></label>
        <label>Data fim<input type="date" id="fFim" /></label>
        <label>Segmento
          <select id="fSegmento"><option value="">Todos</option></select>
        </label>
        <label>Cliente
          <select id="fCliente"><option value="">Todos</option></select>
        </label>
        <label>UF
          <select id="fUF"><option value="">Todas</option></select>
        </label>
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
            <option value="neg">Prejuízo (&lt; 0%)</option>
            <option value="0-20">0% a 20%</option>
            <option value="20-50">20% a 50%</option>
            <option value="50+">Acima de 50%</option>
            <option value="na">Sem % (incompleto)</option>
          </select>
        </label>
        <label>Busca cliente / código / descrição
          <input type="search" id="fBusca" placeholder="Ex.: Ribbon, MG, 300443..." />
        </label>
        <label>Mês selecionado (clique no gráfico)
          <input type="month" id="fMes" />
        </label>
        <label>Top N clientes na tabela
          <select id="fTopN">
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
            <option value="100">100</option>
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
      <p class="hint">Dica: clique numa coluna do gráfico mensal ou numa barra de segmento para filtrar. Clique de novo para remover.</p>
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
            <p>Clique no segmento para filtrar.</p>
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
            <h2>Top clientes</h2>
            <p>Clique na linha para filtrar por cliente.</p>
          </div>
        </div>
        <div class="panel table-wrap">
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

    <p class="footer">RibbonTech Brasil · Dashboard HTML interativo gerado a partir do relatório de custo</p>
  </div>

  <script>
    const ROWS = {data_json};
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

    function fillSelect(id, values, allLabel) {{
      const el = document.getElementById(id);
      const current = el.value;
      el.innerHTML = `<option value="">${{allLabel}}</option>` +
        values.map(v => `<option value="${{v.replaceAll('"', '&quot;')}}">${{v}}</option>`).join('');
      if ([...el.options].some(o => o.value === current)) el.value = current;
    }}

    function initFilters() {{
      const dates = ROWS.map(r => r.d).filter(Boolean).sort();
      if (dates.length) {{
        document.getElementById('fInicio').value = dates[0];
        document.getElementById('fFim').value = dates[dates.length - 1];
        document.getElementById('fInicio').min = dates[0];
        document.getElementById('fInicio').max = dates[dates.length - 1];
        document.getElementById('fFim').min = dates[0];
        document.getElementById('fFim').max = dates[dates.length - 1];
      }}
      fillSelect('fSegmento', uniqueSorted(ROWS.map(r => r.seg)), 'Todos');
      fillSelect('fCliente', uniqueSorted(ROWS.map(r => r.c)), 'Todos');
      fillSelect('fUF', uniqueSorted(ROWS.map(r => r.uf)), 'Todas');
      fillSelect('fMaterial', uniqueSorted(ROWS.map(r => r.mat)), 'Todos');
      saveManualCosts({{ showPersistBar: false }});
    }}

    function readFilters() {{
      return {{
        inicio: document.getElementById('fInicio').value || null,
        fim: document.getElementById('fFim').value || null,
        segmento: document.getElementById('fSegmento').value || null,
        cliente: document.getElementById('fCliente').value || state.selectedCliente || null,
        uf: document.getElementById('fUF').value || null,
        material: document.getElementById('fMaterial').value || null,
        status: document.getElementById('fStatus').value || null,
        lucroFaixa: document.getElementById('fLucroFaixa').value || null,
        busca: (document.getElementById('fBusca').value || '').trim().toLowerCase(),
        mes: document.getElementById('fMes').value || null,
        topN: Number(document.getElementById('fTopN').value || 10),
        pageSize: Number(document.getElementById('fPageSize').value || 50),
      }};
    }}

    function inLucroFaixa(p, faixa) {{
      if (!faixa) return true;
      if (faixa === 'na') return p == null;
      if (p == null) return false;
      if (faixa === 'neg') return p < 0;
      if (faixa === '0-20') return p >= 0 && p < 0.20;
      if (faixa === '20-50') return p >= 0.20 && p < 0.50;
      if (faixa === '50+') return p >= 0.50;
      return true;
    }}

    function applyFilters(baseFilters) {{
      const f = baseFilters || readFilters();
      return allRows().filter(r => {{
        if (f.inicio && r.d && r.d < f.inicio) return false;
        if (f.fim && r.d && r.d > f.fim) return false;
        if (f.inicio && !r.d) return false;
        if (f.segmento && r.seg !== f.segmento) return false;
        if (f.cliente && r.c !== f.cliente) return false;
        if (f.uf && r.uf !== f.uf) return false;
        if (f.material && r.mat !== f.material) return false;
        if (f.status === 'com_custo') {{
          if (!(r.st === 'ok' || r.st === 'manual')) return false;
        }} else if (f.status && r.st !== f.status) {{
          return false;
        }}
        if (!inLucroFaixa(r.p, f.lucroFaixa)) return false;
        if (f.mes && ymOf(r.d) !== f.mes) return false;
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

    function updateKpis(rows) {{
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
      const lucro = custo > 0 ? liq / custo : null;
      document.getElementById('kpiVenda').textContent = money(venda);
      document.getElementById('kpiCusto').textContent = money(custo);
      document.getElementById('kpiLiq').textContent = money(liq);
      document.getElementById('kpiLucro').textContent = pct(lucro);
      document.getElementById('kpiItens').textContent =
        rows.length.toLocaleString('pt-BR') +
        ` (${{ok.toLocaleString('pt-BR')}} ok · ${{manual.toLocaleString('pt-BR')}} manual)`;
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
      const ufs = aggregateBy(rows, 'uf', 'v').slice(0, 8);

      upsertChart('chartVendaMensal', {{
        type: 'bar',
        data: {{
          labels: mensalVenda.labels,
          datasets: [{{
            label: 'Venda mensal',
            data: mensalVenda.values,
            backgroundColor: mensalVenda.labels.map(l => l === filters.mes ? '#c45c26' : 'rgba(31,111,120,0.88)'),
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
            const label = mensalVenda.labels[els[0].index];
            const mesEl = document.getElementById('fMes');
            mesEl.value = mesEl.value === label ? '' : label;
            refresh();
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{ callbacks: {{ label: (c) => money(c.raw) }} }},
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
          labels: mensalLucro.labels,
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
            const label = mensalLucro.labels[els[0].index];
            const mesEl = document.getElementById('fMes');
            mesEl.value = mesEl.value === label ? '' : label;
            refresh();
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{ callbacks: {{ label: (c) => money(c.raw) }} }},
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

      upsertChart('chartSegmento', {{
        type: 'bar',
        data: {{
          labels: segs.map(x => x[0]),
          datasets: [{{
            label: 'Venda',
            data: segs.map(x => x[1]),
            backgroundColor: segs.map(x => x[0] === filters.segmento ? '#c45c26' : 'rgba(31,111,120,0.88)'),
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
            if (!els.length) return;
            const label = segs[els[0].index][0];
            const el = document.getElementById('fSegmento');
            el.value = el.value === label ? '' : label;
            refresh();
          }},
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{ callbacks: {{ label: (c) => money(c.raw) }} }},
            ...dataLabelsConfig({{ horizontal: true, count: segs.length }})
          }},
          scales: {{
            x: {{
              grace: '15%',
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

      document.getElementById('mesNote').textContent = filters.mes
        ? `Mês ativo: ${{filters.mes}} (clique novamente no gráfico para limpar).`
        : 'Nenhum mês selecionado. Clique numa coluna para filtrar.';
    }}

    function renderClientes(rows, filters) {{
      const map = new Map();
      for (const r of rows) {{
        const k = r.c || 'N/D';
        const cur = map.get(k) || {{ venda: 0, liq: 0, custo: 0 }};
        if (r.v != null) cur.venda += r.v;
        if (r.l != null) cur.liq += r.l;
        if (r.ct != null) cur.custo += r.ct;
        map.set(k, cur);
      }}
      const ranked = [...map.entries()]
        .map(([nome, v]) => ({{
          nome,
          ...v,
          lucroPct: v.custo > 0 ? v.liq / v.custo : null
        }}))
        .sort((a,b) => b.venda - a.venda)
        .slice(0, filters.topN);

      const tb = document.getElementById('tblClientes');
      tb.innerHTML = ranked.map(c => `
        <tr class="item-row ${{filters.cliente === c.nome ? 'active' : ''}}" data-cliente="${{c.nome.replaceAll('"', '&quot;')}}">
          <td>${{c.nome}}</td>
          <td>${{money(c.venda)}}</td>
          <td class="${{c.liq < 0 ? 'neg' : 'pos'}}">${{money(c.liq)}}</td>
          <td>${{pct(c.lucroPct)}}</td>
        </tr>
      `).join('');

      tb.querySelectorAll('tr[data-cliente]').forEach(tr => {{
        tr.addEventListener('click', () => {{
          const nome = tr.getAttribute('data-cliente');
          const el = document.getElementById('fCliente');
          if (el.value === nome) {{
            el.value = '';
            state.selectedCliente = null;
          }} else {{
            el.value = nome;
            state.selectedCliente = nome;
          }}
          refresh();
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
          if (nome) {{
            document.getElementById('fCliente').value = nome;
            state.selectedCliente = nome;
          }}
          if (seg) document.getElementById('fSegmento').value = seg;
          refresh();
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
      if (filters.segmento) chips.push(`Segmento: ${{filters.segmento}}`);
      if (filters.cliente) chips.push(`Cliente: ${{filters.cliente}}`);
      if (filters.uf) chips.push(`UF: ${{filters.uf}}`);
      if (filters.material) chips.push(`Material: ${{filters.material}}`);
      if (filters.status) chips.push(`Status: ${{filters.status}}`);
      if (filters.mes) chips.push(`Mês: ${{filters.mes}}`);
      if (filters.busca) chips.push(`Busca: ${{filters.busca}}`);
      if (filters.lucroFaixa) chips.push(`Lucro: ${{filters.lucroFaixa}}`);
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
      if (filters.cliente) state.selectedCliente = filters.cliente;
      const rows = applyFilters(filters);
      updateKpis(rows);
      renderCharts(rows, filters);
      renderClientes(rows, filters);
      renderItens(rows, filters);
      updateChips(filters);
    }}

    function clearFilters() {{
      initFilters();
      document.getElementById('fStatus').value = '';
      document.getElementById('fLucroFaixa').value = '';
      document.getElementById('fBusca').value = '';
      document.getElementById('fMes').value = '';
      document.getElementById('fTopN').value = '10';
      document.getElementById('fPageSize').value = '50';
      document.getElementById('fSegmento').value = '';
      document.getElementById('fCliente').value = '';
      document.getElementById('fUF').value = '';
      document.getElementById('fMaterial').value = '';
      state.selectedCliente = null;
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
    ['fInicio','fFim','fSegmento','fCliente','fUF','fMaterial','fStatus','fLucroFaixa','fMes','fTopN','fPageSize']
      .forEach(id => document.getElementById(id).addEventListener('change', () => {{ state.page = 0; refresh(); }}));
    document.getElementById('fBusca').addEventListener('input', () => {{
      clearTimeout(state._t);
      state._t = setTimeout(() => {{ state.page = 0; refresh(); }}, 250);
    }});

    initFilters();
    refresh();
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera dashboard HTML interativo")
    parser.add_argument("--input", default="Relatorio_Custo_Faturamento_RBT.xlsx")
    parser.add_argument("--output", default="Dashboard_Custo_Faturamento_RBT.html")
    args = parser.parse_args()

    df = pd.read_excel(args.input, sheet_name="Relatorio")
    dts = pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce")
    if dts.notna().any():
        periodo = f"{dts.min().strftime('%d/%m/%Y')} a {dts.max().strftime('%d/%m/%Y')}"
    else:
        periodo = "Período não disponível"

    rows = build_rows(df)
    html = render_html(rows, periodo)
    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard gerado: {out.resolve()}")
    print(f"Linhas embutidas: {len(rows)} | tamanho: {out.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
