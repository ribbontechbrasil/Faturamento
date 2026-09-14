#!/usr/bin/env python3
"""NF 3611 FRANCAP: ETBOPP80185 custo R$ 5.166,90; P11074108 venda R$ 146,70 e custo R$ 92,68."""

from pathlib import Path

from gerar_relatorio_custo import (
    calcular_relatorio,
    custo_override,
    load_faturamento_agosto,
    venda_liquida_override,
    venda_override,
)

ROOT = Path(__file__).resolve().parents[1]
NF_3611_ETIQUETA_CUSTO = 5166.90
NF_3611_ETIQUETA_CUSTO_ANTIGO = 3818.40  # 3163,50 + 70 + 584,90
NF_3611_ETIQUETA_VENDA = 6364.50
NF_3611_RIBBON_VENDA = 146.70
NF_3611_RIBBON_CUSTO = 92.68
NF_3611_RIBBON_LIQ = 54.02  # 146,70 − 92,68


def approx(a, b, tol=0.02):
    return abs(float(a) - float(b)) <= tol


def _row_etiqueta(df):
    return df[(df["Número"] == "3611") & (df["Código"].astype(str).str.contains("ETBOPP80185"))]


def _row_ribbon(df):
    return df[(df["Número"] == "3611") & (df["Código"].astype(str).str.contains("P11074108"))]


def test_override_direto():
    assert custo_override(3611, "ETBOPP80185") == NF_3611_ETIQUETA_CUSTO
    assert custo_override("3611", "ETBOPP80185") == NF_3611_ETIQUETA_CUSTO
    assert venda_override(3611, "P11074108") == NF_3611_RIBBON_VENDA
    assert venda_override("3611", "P11074108") == NF_3611_RIBBON_VENDA
    assert custo_override(3611, "P11074108") == NF_3611_RIBBON_CUSTO
    assert custo_override("3611", "P11074108") == NF_3611_RIBBON_CUSTO
    assert venda_liquida_override(3611, "P11074108") == NF_3611_RIBBON_LIQ
    assert venda_override(3611, "ETBOPP80185") is None
    assert custo_override(3601, "P11074108") is None


def test_inclui_ribbon_mesmo_sem_linha_na_planilha():
    import pandas as pd
    from gerar_relatorio_custo import NF_3611_P11074108_AGO, _ensure_agosto_item_conferido

    vazio = pd.DataFrame(
        [{"Nota": 3611, "Item": "ETBOPP80185", "Venda": 6364.50, "Cliente": "FRANCAP"}]
    )
    vazio["_nf"] = "3611"
    out = _ensure_agosto_item_conferido(vazio, NF_3611_P11074108_AGO)
    rib = out[out["Item"].astype(str).str.contains("P11074108")]
    assert len(rib) == 1
    assert float(rib.iloc[0]["Venda"]) == NF_3611_RIBBON_VENDA
    # não duplica se já existir
    out2 = _ensure_agosto_item_conferido(out, NF_3611_P11074108_AGO)
    assert len(out2[out2["Item"].astype(str).str.contains("P11074108")]) == 1


def test_planilha_agosto_item():
    ago = load_faturamento_agosto(ROOT)
    etq = _row_etiqueta(ago)
    assert len(etq) == 1, etq
    r = etq.iloc[0]
    assert approx(r["Valor total venda"], NF_3611_ETIQUETA_VENDA, tol=0.05)
    assert approx(r["Custo total item"], NF_3611_ETIQUETA_CUSTO), r["Custo total item"]
    assert not approx(r["Custo total item"], NF_3611_ETIQUETA_CUSTO_ANTIGO, tol=1.0)
    assert not approx(r["Custo total item"], 3163.50, tol=1.0)
    assert r["Base custo unitário"] == "custo_conferido"

    rib = _row_ribbon(ago)
    assert len(rib) == 1, rib
    rr = rib.iloc[0]
    assert str(rr["Nome"]).upper().find("FRANCAP") >= 0
    assert approx(rr["Valor total venda"], NF_3611_RIBBON_VENDA, tol=0.05)
    assert approx(rr["Custo total item"], NF_3611_RIBBON_CUSTO), rr["Custo total item"]
    assert approx(rr["Venda líquida"], NF_3611_RIBBON_LIQ), rr["Venda líquida"]
    assert rr["Base custo unitário"] == "custo_conferido"
    assert rr["Segmento"] == "Ribbon"


def test_relatorio_inclui_override():
    df = calcular_relatorio(ROOT / "Faturamento_RBT (2).xlsx")
    dts = pd_to_month(df)
    ago = df[dts == "2026-08"]
    etq = _row_etiqueta(ago)
    assert len(etq) == 1, etq
    assert approx(float(etq.iloc[0]["Custo total item"]), NF_3611_ETIQUETA_CUSTO)

    rib = _row_ribbon(ago)
    assert len(rib) == 1, rib
    r = rib.iloc[0]
    assert approx(float(r["Valor total venda"]), NF_3611_RIBBON_VENDA, tol=0.05)
    assert approx(float(r["Custo total item"]), NF_3611_RIBBON_CUSTO)
    assert approx(float(r["Venda líquida"]), NF_3611_RIBBON_LIQ)


def pd_to_month(df):
    import pandas as pd

    return pd.to_datetime(df["Data de emissão"], dayfirst=True, errors="coerce").dt.strftime(
        "%Y-%m"
    )


if __name__ == "__main__":
    test_override_direto()
    test_inclui_ribbon_mesmo_sem_linha_na_planilha()
    test_planilha_agosto_item()
    test_relatorio_inclui_override()
    print("OK: NF 3611 ETBOPP80185 custo R$ 5.166,90 · P11074108 venda R$ 146,70 custo R$ 92,68")
