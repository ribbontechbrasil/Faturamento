# Despesas — não é faturamento

Esta pasta relaciona **duas planilhas de despesas**, em assunto separado das notas, custos de etiqueta e do dashboard de faturamento.

| Arquivo na raiz do repositório | Papel |
|---|---|
| `Despesas_RBT.xlsx` | Planilha **modelo** (julho: Fornecedor, Histórico, Valor) |
| `Despesas Ago 2026.xlsx` | Planilha **nova** (agosto, sem cabeçalho) |

Nada daqui altera `Faturamento Ago 2026.xlsx`, `Faturamento_RBT (2).xlsx` nem o relatório de custo.

## O que é preenchido na planilha nova

A relação é Fornecedor + Histórico (acento e espaço não importam).

Na planilha nova preenchida:

- **Valor ago/2026** — permanece o valor de agosto (não é sobrescrito)
- **Valor no modelo** — célula preenchida com o valor da planilha modelo quando a linha já existia
- **Relação** — `Encontrado no modelo` (verde) ou `Novo (não está no modelo)` (amarelo)
- **Categoria** e **Subcategoria** — mesma classificação usada na planilha modelo

Linhas que estão só no modelo (ex.: rescisão da Maria Maira, Simples Nacional) ficam na aba **Só no modelo**, para não misturar com agosto.

## Arquivos gerados

- [Despesas_Ago_2026_Relacionada.xlsx](Despesas_Ago_2026_Relacionada.xlsx) — abrir no Excel
- [relacao_despesas.html](relacao_despesas.html) — conferência no navegador

## Como gerar de novo

Na raiz do repositório:

```bash
python3 scripts/relacionar_despesas.py
python3 scripts/test_relacionar_despesas.py
```
