#!/usr/bin/env python3
"""Gera dashboard HTML a partir do relatório de custo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def br_money(v: float | None) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def br_pct(v: float | None) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"{v * 100:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def br_int(v: float | int) -> str:
    return f"{int(v):,}".replace(",", ".")


def build_payload(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["dt"] = pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce")
    ok = df[df["Status custo"] == "ok"].copy()
    inc = df[df["Status custo"] != "ok"].copy()

    venda_total = float(df["Valor total venda"].sum(skipna=True))
    custo_ok = float(ok["Custo total item"].sum(skipna=True))
    liq_ok = float(ok["Venda líquida"].sum(skipna=True))
    frete_ok = float(ok["Frete (3%)"].sum(skipna=True))
    imposto_ok = float(ok["Imposto (9,2%)"].sum(skipna=True))
    margem = (liq_ok / custo_ok) if custo_ok else None

    por_seg = (
        df.groupby("Segmento", dropna=False)
        .agg(
            itens=("Status custo", "size"),
            ok=("Status custo", lambda s: int((s == "ok").sum())),
            incompleto=("Status custo", lambda s: int((s != "ok").sum())),
            venda=("Valor total venda", "sum"),
            custo=("Custo total item", "sum"),
            liquida=("Venda líquida", "sum"),
        )
        .reset_index()
        .fillna(0)
        .sort_values("venda", ascending=False)
    )

    ok["ym"] = ok["dt"].dt.to_period("M").astype(str)
    mensal = (
        ok.dropna(subset=["dt"])
        .groupby("ym")
        .agg(
            venda=("Valor total venda", "sum"),
            custo=("Custo total item", "sum"),
            liquida=("Venda líquida", "sum"),
        )
        .reset_index()
        .sort_values("ym")
    )

    uf = (
        ok.groupby("UF", dropna=False)["Valor total venda"]
        .sum()
        .sort_values(ascending=False)
        .head(8)
        .reset_index()
    )

    # Pendências simplificadas (primeira tag)
    pend = inc["Pendências"].fillna("").astype(str)
    pend_simple = pend.map(lambda x: x.split(";")[0] if x else "não informado")
    pend_map = {
        "custo_rs": "Sem custo em Custos_RS",
        "tubete": "Tubete não identificado",
        "material": "Material não identificado",
        "qtd_rolo": "Qtd. do rolo não identificada",
        "segmento_sem_regra": "Segmento sem regra de custo",
        "dimensao": "Dimensão não identificada",
        "tubete_sem_preco(2.5)": "Tubete 2,5\" sem preço",
        "codigo": "Código ausente",
        "quantidade_nf": "Quantidade da NF ausente",
        "valor_venda": "Valor de venda ausente",
    }
    pend_labels = pend_simple.map(lambda x: pend_map.get(x, x if x else "não informado"))
    pend_counts = pend_labels.value_counts().head(8).reset_index()
    pend_counts.columns = ["motivo", "qtd"]

    top_clientes = (
        ok.groupby("Nome", dropna=False)
        .agg(
            venda=("Valor total venda", "sum"),
            custo=("Custo total item", "sum"),
            liquida=("Venda líquida", "sum"),
            itens=("Número", "count"),
        )
        .reset_index()
        .sort_values("venda", ascending=False)
        .head(10)
    )
    top_clientes["lucro_pct"] = top_clientes.apply(
        lambda r: (r["liquida"] / r["custo"]) if r["custo"] else None, axis=1
    )

    mat = (
        ok[ok["Material"].notna()]
        .groupby("Material")
        .agg(itens=("Material", "size"), custo=("Custo total item", "sum"), venda=("Valor total venda", "sum"))
        .reset_index()
        .sort_values("venda", ascending=False)
    )

    dt_min = df["dt"].min()
    dt_max = df["dt"].max()
    periodo = (
        f"{dt_min.strftime('%d/%m/%Y')} a {dt_max.strftime('%d/%m/%Y')}"
        if pd.notna(dt_min) and pd.notna(dt_max)
        else "Período não disponível"
    )

    return {
        "periodo": periodo,
        "kpis": {
            "itens": int(len(df)),
            "ok": int(len(ok)),
            "incompleto": int(len(inc)),
            "cobertura": float(len(ok) / len(df)) if len(df) else 0,
            "venda_total": venda_total,
            "custo_ok": custo_ok,
            "liquida_ok": liq_ok,
            "frete_ok": frete_ok,
            "imposto_ok": imposto_ok,
            "lucro_pct": margem,
        },
        "segmentos": {
            "labels": por_seg["Segmento"].astype(str).tolist(),
            "venda": [float(x) for x in por_seg["venda"]],
            "custo": [float(x) for x in por_seg["custo"]],
            "liquida": [float(x) for x in por_seg["liquida"]],
            "ok": [int(x) for x in por_seg["ok"]],
            "incompleto": [int(x) for x in por_seg["incompleto"]],
        },
        "mensal": {
            "labels": mensal["ym"].tolist(),
            "venda": [float(x) for x in mensal["venda"]],
            "custo": [float(x) for x in mensal["custo"]],
            "liquida": [float(x) for x in mensal["liquida"]],
        },
        "uf": {
            "labels": uf["UF"].astype(str).tolist(),
            "venda": [float(x) for x in uf["Valor total venda"]],
        },
        "pendencias": {
            "labels": pend_counts["motivo"].tolist(),
            "qtd": [int(x) for x in pend_counts["qtd"]],
        },
        "materiais": {
            "labels": mat["Material"].astype(str).tolist(),
            "venda": [float(x) for x in mat["venda"]],
            "custo": [float(x) for x in mat["custo"]],
            "itens": [int(x) for x in mat["itens"]],
        },
        "top_clientes": [
            {
                "nome": str(r["Nome"])[:48],
                "itens": int(r["itens"]),
                "venda": float(r["venda"]),
                "custo": float(r["custo"]),
                "liquida": float(r["liquida"]),
                "lucro_pct": float(r["lucro_pct"]) if pd.notna(r["lucro_pct"]) else None,
            }
            for _, r in top_clientes.iterrows()
        ],
        "format": {
            "venda_total": br_money(venda_total),
            "custo_ok": br_money(custo_ok),
            "liquida_ok": br_money(liq_ok),
            "frete_ok": br_money(frete_ok),
            "imposto_ok": br_money(imposto_ok),
            "lucro_pct": br_pct(margem),
            "cobertura": br_pct(len(ok) / len(df) if len(df) else 0),
            "itens": br_int(len(df)),
            "ok": br_int(len(ok)),
            "incompleto": br_int(len(inc)),
        },
    }


def render_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    f = payload["format"]
    k = payload["kpis"]

    rows = []
    for c in payload["top_clientes"]:
        rows.append(
            "<tr>"
            f"<td>{c['nome']}</td>"
            f"<td>{br_int(c['itens'])}</td>"
            f"<td>{br_money(c['venda'])}</td>"
            f"<td>{br_money(c['custo'])}</td>"
            f"<td>{br_money(c['liquida'])}</td>"
            f"<td>{br_pct(c['lucro_pct'])}</td>"
            "</tr>"
        )
    clientes_html = "\n".join(rows)

    seg_cards = []
    for i, label in enumerate(payload["segmentos"]["labels"]):
        venda = payload["segmentos"]["venda"][i]
        ok_n = payload["segmentos"]["ok"][i]
        inc_n = payload["segmentos"]["incompleto"][i]
        total = ok_n + inc_n
        cov = (ok_n / total) if total else 0
        seg_cards.append(
            f"""
            <article class="seg-card">
              <h3>{label}</h3>
              <p class="seg-venda">{br_money(venda)}</p>
              <div class="seg-meta">
                <span>{br_int(ok_n)} ok</span>
                <span>{br_int(inc_n)} incompleto</span>
              </div>
              <div class="bar"><i style="--w:{cov*100:.1f}%"></i></div>
              <small>Cobertura {br_pct(cov)}</small>
            </article>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>RibbonTech · Dashboard de Custo e Lucro</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Sora:wght@500;600;700&display=swap" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --ink: #14212b;
      --ink-soft: #2a3b49;
      --mist: #e6eef3;
      --panel: rgba(255,255,255,0.78);
      --line: rgba(20,33,43,0.12);
      --teal: #1f6f78;
      --teal-deep: #14545c;
      --copper: #c45c26;
      --copper-soft: #f0d2c2;
      --good: #1f7a4c;
      --warn: #a15c12;
      --shadow: 0 18px 50px rgba(20,33,43,0.12);
      --radius: 18px;
    }}

    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1200px 600px at 10% -10%, rgba(31,111,120,0.22), transparent 55%),
        radial-gradient(900px 500px at 90% 0%, rgba(196,92,38,0.16), transparent 50%),
        linear-gradient(180deg, #d9e5ec 0%, var(--mist) 40%, #f4f7f9 100%);
      min-height: 100vh;
    }}

    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.035;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='.55'/%3E%3C/svg%3E");
      z-index: 0;
    }}

    .wrap {{
      position: relative;
      z-index: 1;
      width: min(1180px, calc(100% - 2rem));
      margin: 0 auto;
      padding: 1.5rem 0 3rem;
    }}

    .hero {{
      display: grid;
      gap: 1.25rem;
      padding: 1.6rem 1.6rem 1.4rem;
      border-radius: 28px;
      background:
        linear-gradient(135deg, rgba(20,33,43,0.96), rgba(31,111,120,0.88) 58%, rgba(196,92,38,0.72));
      color: #f7fafc;
      box-shadow: var(--shadow);
      overflow: hidden;
      position: relative;
      animation: rise 0.7s ease both;
    }}

    .hero::after {{
      content: "";
      position: absolute;
      right: -80px;
      top: -60px;
      width: 280px;
      height: 280px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 65%);
    }}

    .brand {{
      font-family: Sora, sans-serif;
      font-size: clamp(2rem, 5vw, 3rem);
      font-weight: 700;
      letter-spacing: -0.03em;
      margin: 0;
      line-height: 1.05;
    }}

    .hero p {{
      margin: 0.35rem 0 0;
      max-width: 46ch;
      color: rgba(247,250,252,0.86);
      font-size: 1.02rem;
    }}

    .period {{
      display: inline-flex;
      margin-top: 0.9rem;
      padding: 0.35rem 0.7rem;
      border: 1px solid rgba(255,255,255,0.22);
      border-radius: 999px;
      font-size: 0.86rem;
      color: rgba(247,250,252,0.9);
    }}

    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0.85rem;
      margin-top: 0.4rem;
    }}

    .kpi {{
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: 16px;
      padding: 0.9rem 1rem;
      backdrop-filter: blur(6px);
      animation: rise 0.8s ease both;
    }}
    .kpi:nth-child(2) {{ animation-delay: 0.06s; }}
    .kpi:nth-child(3) {{ animation-delay: 0.12s; }}
    .kpi:nth-child(4) {{ animation-delay: 0.18s; }}

    .kpi span {{
      display: block;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: rgba(247,250,252,0.72);
      margin-bottom: 0.35rem;
    }}
    .kpi strong {{
      font-family: Sora, sans-serif;
      font-size: clamp(1.15rem, 2.4vw, 1.55rem);
      font-weight: 600;
      letter-spacing: -0.02em;
    }}

    section {{
      margin-top: 1.4rem;
      animation: rise 0.75s ease both;
    }}

    .section-head {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 1rem;
      margin-bottom: 0.8rem;
    }}
    .section-head h2 {{
      font-family: Sora, sans-serif;
      font-size: 1.35rem;
      margin: 0;
      letter-spacing: -0.02em;
    }}
    .section-head p {{
      margin: 0.2rem 0 0;
      color: var(--ink-soft);
      font-size: 0.95rem;
    }}

    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 1rem 1.1rem 1.15rem;
      backdrop-filter: blur(10px);
    }}

    .grid-2 {{
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 1rem;
    }}
    .grid-3 {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
    }}

    .chart-box {{
      position: relative;
      height: 300px;
    }}
    .chart-box.tall {{ height: 340px; }}

    .seg-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.85rem;
    }}
    .seg-card {{
      background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(255,255,255,0.65));
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 0.95rem 1rem;
      transition: transform 0.25s ease, box-shadow 0.25s ease;
    }}
    .seg-card:hover {{
      transform: translateY(-3px);
      box-shadow: 0 14px 30px rgba(20,33,43,0.1);
    }}
    .seg-card h3 {{
      margin: 0;
      font-family: Sora, sans-serif;
      font-size: 1rem;
    }}
    .seg-venda {{
      margin: 0.45rem 0 0.55rem;
      font-family: Sora, sans-serif;
      font-size: 1.2rem;
      font-weight: 600;
      color: var(--teal-deep);
    }}
    .seg-meta {{
      display: flex;
      justify-content: space-between;
      font-size: 0.82rem;
      color: var(--ink-soft);
      margin-bottom: 0.45rem;
    }}
    .bar {{
      height: 7px;
      background: rgba(20,33,43,0.08);
      border-radius: 999px;
      overflow: hidden;
    }}
    .bar i {{
      display: block;
      height: 100%;
      width: var(--w);
      background: linear-gradient(90deg, var(--teal), #3aa0ab);
      border-radius: inherit;
      transform-origin: left;
      animation: fillBar 1.1s ease both;
    }}
    .seg-card small {{
      display: block;
      margin-top: 0.4rem;
      color: var(--ink-soft);
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.92rem;
    }}
    th, td {{
      text-align: left;
      padding: 0.7rem 0.45rem;
      border-bottom: 1px solid var(--line);
    }}
    th {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--ink-soft);
      font-weight: 600;
    }}
    tr:hover td {{ background: rgba(31,111,120,0.05); }}

    .legend-note {{
      margin-top: 0.8rem;
      color: var(--ink-soft);
      font-size: 0.88rem;
    }}

    .footer {{
      margin-top: 1.6rem;
      color: var(--ink-soft);
      font-size: 0.85rem;
      text-align: center;
    }}

    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(14px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes fillBar {{
      from {{ transform: scaleX(0); }}
      to {{ transform: scaleX(1); }}
    }}

    @media (max-width: 920px) {{
      .kpi-grid, .grid-2, .grid-3, .seg-grid {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
    @media (max-width: 640px) {{
      .wrap {{ width: min(100% - 1.2rem, 1180px); }}
      .kpi-grid, .grid-2, .grid-3, .seg-grid {{
        grid-template-columns: 1fr;
      }}
      .chart-box, .chart-box.tall {{ height: 260px; }}
      table {{ font-size: 0.82rem; }}
      th:nth-child(2), td:nth-child(2) {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <div>
        <h1 class="brand">RibbonTech</h1>
        <p>Dashboard de custo, frete, imposto e lucro do faturamento — visão executiva dos resultados calculados.</p>
        <div class="period">Período: {payload["periodo"]}</div>
      </div>
      <div class="kpi-grid">
        <div class="kpi"><span>Venda total</span><strong>{f["venda_total"]}</strong></div>
        <div class="kpi"><span>Custo calculado</span><strong>{f["custo_ok"]}</strong></div>
        <div class="kpi"><span>Venda líquida</span><strong>{f["liquida_ok"]}</strong></div>
        <div class="kpi"><span>% Lucro</span><strong>{f["lucro_pct"]}</strong></div>
      </div>
    </header>

    <section>
      <div class="section-head">
        <div>
          <h2>Cobertura do cálculo</h2>
          <p>{f["ok"]} itens com custo ok · {f["incompleto"]} custo incompleto · cobertura {f["cobertura"]}</p>
        </div>
      </div>
      <div class="grid-3">
        <article class="panel">
          <div class="chart-box"><canvas id="chartCobertura"></canvas></div>
          <p class="legend-note">Itens válidos (sem NF cancelada/rejeitada/denegada): {f["itens"]}.</p>
        </article>
        <article class="panel">
          <div class="chart-box"><canvas id="chartPendencias"></canvas></div>
          <p class="legend-note">Principais motivos de “custo incompleto”.</p>
        </article>
        <article class="panel">
          <div class="chart-box"><canvas id="chartComposicao"></canvas></div>
          <p class="legend-note">Sobre itens com custo ok: frete {f["frete_ok"]} · imposto {f["imposto_ok"]}.</p>
        </article>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Desempenho por segmento</h2>
          <p>Venda, custo e venda líquida nos itens com cálculo completo.</p>
        </div>
      </div>
      <div class="seg-grid">
        {''.join(seg_cards)}
      </div>
      <div class="panel" style="margin-top:1rem;">
        <div class="chart-box tall"><canvas id="chartSegmento"></canvas></div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Evolução mensal</h2>
          <p>Venda, custo e venda líquida ao longo do tempo (somente itens ok).</p>
        </div>
      </div>
      <div class="panel">
        <div class="chart-box tall"><canvas id="chartMensal"></canvas></div>
      </div>
    </section>

    <section class="grid-2">
      <div>
        <div class="section-head">
          <div>
            <h2>Top UFs</h2>
            <p>Maiores volumes de venda com custo calculado.</p>
          </div>
        </div>
        <div class="panel">
          <div class="chart-box"><canvas id="chartUF"></canvas></div>
        </div>
      </div>
      <div>
        <div class="section-head">
          <div>
            <h2>Materiais de etiqueta</h2>
            <p>Participação por substrato nos itens ok.</p>
          </div>
        </div>
        <div class="panel">
          <div class="chart-box"><canvas id="chartMaterial"></canvas></div>
        </div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div>
          <h2>Top 10 clientes</h2>
          <p>% Lucro = venda líquida ÷ custo total do item.</p>
        </div>
      </div>
      <div class="panel" style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th>Cliente</th>
              <th>Itens</th>
              <th>Venda</th>
              <th>Custo</th>
              <th>Venda líquida</th>
              <th>% Lucro</th>
            </tr>
          </thead>
          <tbody>
            {clientes_html}
          </tbody>
        </table>
      </div>
    </section>

    <p class="footer">
      Gerado a partir de Relatorio_Custo_Faturamento_RBT.xlsx · RibbonTech Brasil
    </p>
  </div>

  <script>
    const DATA = {data_json};

    const money = (v) => v.toLocaleString('pt-BR', {{ style: 'currency', currency: 'BRL' }});
    const teal = '#1f6f78';
    const copper = '#c45c26';
    const ink = '#14212b';
    const soft = '#8aa0b0';

    Chart.defaults.font.family = 'IBM Plex Sans, sans-serif';
    Chart.defaults.color = '#2a3b49';

    new Chart(document.getElementById('chartCobertura'), {{
      type: 'doughnut',
      data: {{
        labels: ['Custo ok', 'Custo incompleto'],
        datasets: [{{
          data: [DATA.kpis.ok, DATA.kpis.incompleto],
          backgroundColor: [teal, copper],
          borderWidth: 0,
          hoverOffset: 6
        }}]
      }},
      options: {{
        cutout: '68%',
        plugins: {{
          legend: {{ position: 'bottom' }},
          title: {{ display: true, text: 'Status do custo', font: {{ family: 'Sora', size: 14 }} }}
        }},
        animation: {{ animateRotate: true, duration: 1100 }}
      }}
    }});

    new Chart(document.getElementById('chartPendencias'), {{
      type: 'bar',
      data: {{
        labels: DATA.pendencias.labels,
        datasets: [{{
          label: 'Itens',
          data: DATA.pendencias.qtd,
          backgroundColor: 'rgba(196,92,38,0.85)',
          borderRadius: 8,
          maxBarThickness: 28
        }}]
      }},
      options: {{
        indexAxis: 'y',
        plugins: {{
          legend: {{ display: false }},
          title: {{ display: true, text: 'Pendências', font: {{ family: 'Sora', size: 14 }} }}
        }},
        scales: {{
          x: {{ grid: {{ color: 'rgba(20,33,43,0.06)' }}, ticks: {{ precision: 0 }} }},
          y: {{ grid: {{ display: false }} }}
        }},
        animation: {{ duration: 1000 }}
      }}
    }});

    new Chart(document.getElementById('chartComposicao'), {{
      type: 'doughnut',
      data: {{
        labels: ['Custo', 'Frete 3%', 'Imposto 9,2%', 'Venda líquida'],
        datasets: [{{
          data: [DATA.kpis.custo_ok, DATA.kpis.frete_ok, DATA.kpis.imposto_ok, DATA.kpis.liquida_ok],
          backgroundColor: ['#234a57', '#3aa0ab', '#c45c26', '#1f7a4c'],
          borderWidth: 0
        }}]
      }},
      options: {{
        cutout: '62%',
        plugins: {{
          legend: {{ position: 'bottom' }},
          title: {{ display: true, text: 'Composição da venda (itens ok)', font: {{ family: 'Sora', size: 14 }} }},
          tooltip: {{
            callbacks: {{
              label: (ctx) => `${{ctx.label}}: ${{money(ctx.raw)}}`
            }}
          }}
        }}
      }}
    }});

    new Chart(document.getElementById('chartSegmento'), {{
      type: 'bar',
      data: {{
        labels: DATA.segmentos.labels,
        datasets: [
          {{ label: 'Venda', data: DATA.segmentos.venda, backgroundColor: teal, borderRadius: 6 }},
          {{ label: 'Custo', data: DATA.segmentos.custo, backgroundColor: '#234a57', borderRadius: 6 }},
          {{ label: 'Venda líquida', data: DATA.segmentos.liquida, backgroundColor: copper, borderRadius: 6 }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top' }},
          tooltip: {{ callbacks: {{ label: (c) => `${{c.dataset.label}}: ${{money(c.raw)}}` }} }}
        }},
        scales: {{
          x: {{ grid: {{ display: false }} }},
          y: {{
            grid: {{ color: 'rgba(20,33,43,0.06)' }},
            ticks: {{ callback: (v) => 'R$ ' + (v/1000).toLocaleString('pt-BR') + ' mil' }}
          }}
        }},
        animation: {{ duration: 1200 }}
      }}
    }});

    new Chart(document.getElementById('chartMensal'), {{
      type: 'line',
      data: {{
        labels: DATA.mensal.labels,
        datasets: [
          {{
            label: 'Venda',
            data: DATA.mensal.venda,
            borderColor: teal,
            backgroundColor: 'rgba(31,111,120,0.12)',
            fill: true,
            tension: 0.35,
            pointRadius: 2
          }},
          {{
            label: 'Custo',
            data: DATA.mensal.custo,
            borderColor: ink,
            backgroundColor: 'transparent',
            tension: 0.35,
            pointRadius: 2
          }},
          {{
            label: 'Venda líquida',
            data: DATA.mensal.liquida,
            borderColor: copper,
            backgroundColor: 'transparent',
            tension: 0.35,
            pointRadius: 2
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top' }},
          tooltip: {{ callbacks: {{ label: (c) => `${{c.dataset.label}}: ${{money(c.raw)}}` }} }}
        }},
        scales: {{
          x: {{ grid: {{ display: false }} }},
          y: {{
            grid: {{ color: 'rgba(20,33,43,0.06)' }},
            ticks: {{ callback: (v) => 'R$ ' + (v/1000).toLocaleString('pt-BR') + ' mil' }}
          }}
        }},
        animation: {{ duration: 1300 }}
      }}
    }});

    new Chart(document.getElementById('chartUF'), {{
      type: 'bar',
      data: {{
        labels: DATA.uf.labels,
        datasets: [{{
          data: DATA.uf.venda,
          backgroundColor: 'rgba(31,111,120,0.85)',
          borderRadius: 8,
          maxBarThickness: 36
        }}]
      }},
      options: {{
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{ callbacks: {{ label: (c) => money(c.raw) }} }}
        }},
        scales: {{
          x: {{ grid: {{ display: false }} }},
          y: {{
            grid: {{ color: 'rgba(20,33,43,0.06)' }},
            ticks: {{ callback: (v) => 'R$ ' + (v/1000).toLocaleString('pt-BR') + ' mil' }}
          }}
        }}
      }}
    }});

    new Chart(document.getElementById('chartMaterial'), {{
      type: 'doughnut',
      data: {{
        labels: DATA.materiais.labels,
        datasets: [{{
          data: DATA.materiais.venda,
          backgroundColor: ['#1f6f78', '#c45c26', '#234a57'],
          borderWidth: 0
        }}]
      }},
      options: {{
        cutout: '60%',
        plugins: {{
          legend: {{ position: 'bottom' }},
          tooltip: {{ callbacks: {{ label: (c) => `${{c.label}}: ${{money(c.raw)}}` }} }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera dashboard HTML do relatório de custo")
    parser.add_argument("--input", default="Relatorio_Custo_Faturamento_RBT.xlsx")
    parser.add_argument("--output", default="Dashboard_Custo_Faturamento_RBT.html")
    args = parser.parse_args()

    df = pd.read_excel(args.input, sheet_name="Relatorio")
    payload = build_payload(df)
    html = render_html(payload)
    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard gerado: {out.resolve()}")
    print(
        f"Itens={payload['kpis']['itens']} ok={payload['kpis']['ok']} "
        f"venda={payload['format']['venda_total']} liquida={payload['format']['liquida_ok']}"
    )


if __name__ == "__main__":
    main()
