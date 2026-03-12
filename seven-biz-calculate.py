"""
Calcula preço médio de compra e lucro/prejuízo por ticker.
Gera abas separadas por ANO no Excel de saída (para IR).

Suporta três formatos de arquivo:
  - Nacional        : Excel (.xlsx) exportado do site B3 / Investidor B3
  - Internacional   : xlsx da corretora com ativos internacionais
  - Status Invest   : xlsx exportado do Status Invest — contém tudo (Ações, Stocks,
                      Tesouro Direto, ETF Exterior) em um único arquivo, com coluna Categoria

Uso:
    python3 seven-biz-calculate.py
    (ajuste as variáveis abaixo e coloque os arquivos na mesma pasta)
"""
import pandas as pd
from pathlib import Path

# ── CONFIGURAÇÃO ─────────────────────────────────────────────────────────────
ARQUIVO_NACIONAL       = None        # xlsx exportado do B3 (ou None)
ARQUIVO_INTERNACIONAL  = None   # xlsx da corretora (ou None)
ARQUIVO_STATUS_INVEST  = "status-invest.xlsx"   # xlsx do Status Invest (ou None)
# ─────────────────────────────────────────────────────────────────────────────


def remove_sufixo_fracionario(ticker: str) -> str:
    """Remove o 'F' final de mercado fracionário (VIVT3F→VIVT3). Não toca em nomes como HFOF11."""
    ticker = ticker.strip()
    if ticker.endswith("F"):
        return ticker[:-1]
    return ticker


def parse_numero_br(valor) -> float:
    """Converte '1.234,56' ou '1,234.56' ou 1234.56 para float."""
    if isinstance(valor, (int, float)):
        return float(valor)
    valor = str(valor).strip().replace("R$", "").strip()
    if "," in valor and "." in valor:
        if valor.index(",") > valor.index("."):
            valor = valor.replace(".", "").replace(",", ".")
        else:
            valor = valor.replace(",", "")
    elif "," in valor:
        valor = valor.replace(",", ".")
    return float(valor)


def carrega_nacional(arquivo: str) -> pd.DataFrame:
    """Lê o xlsx exportado do Investidor B3."""
    df = pd.read_excel(arquivo)
    df.columns = df.columns.str.strip()
    df["Ticker"]  = df["Código de Negociação"].apply(remove_sufixo_fracionario)
    df["Tipo"]    = df["Tipo de Movimentação"].str.strip()
    df["Qtd"]     = pd.to_numeric(df["Quantidade"], errors="coerce")
    df["Preco"]   = df["Preço"].apply(parse_numero_br)
    df["Valor"]   = df["Valor"].apply(parse_numero_br)
    df["Data"]    = pd.to_datetime(df["Data do Negócio"], dayfirst=True)
    df["Mercado"] = "Nacional"
    return df[["Data", "Ticker", "Tipo", "Qtd", "Preco", "Valor", "Mercado"]]


def carrega_internacional(arquivo: str) -> pd.DataFrame:
    """
    Lê o xlsx exportado pela corretora para ativos internacionais.
    Colunas esperadas:
      Data operação | Categoria | Código Ativo | Operação C/V | Quantidade | Preço unitário | ...
    Também suporta TXT/TSV (tab-separado, sem cabeçalho):
      Data | TipoAtivo | Ticker | C/V | Qtd | Preço | Corretora | t1..t4
    """
    ext = Path(arquivo).suffix.lower()

    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(arquivo)
        df.columns = df.columns.str.strip()
        df["Data"]    = pd.to_datetime(df["Data operação"], dayfirst=True, errors="coerce")
        df["Ticker"]  = df["Código Ativo"].str.strip()
        df["Tipo"]    = df["Operação C/V"].str.strip().map({"C": "Compra", "V": "Venda"})
        df["Qtd"]     = df["Quantidade"].apply(parse_numero_br)
        df["Preco"]   = df["Preço unitário"].apply(parse_numero_br)
        df["Valor"]   = df["Qtd"] * df["Preco"]
    else:
        # fallback: TSV sem cabeçalho
        colunas = ["Data", "TipoAtivo", "Ticker", "CV", "Qtd", "Preco",
                   "Corretora", "t1", "t2", "t3", "t4"]
        df = pd.read_csv(arquivo, sep="\t", header=None, names=colunas,
                         decimal=",", thousands=".")
        df["Data"]    = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
        df["Ticker"]  = df["Ticker"].str.strip()
        df["Tipo"]    = df["CV"].str.strip().map({"C": "Compra", "V": "Venda"})
        df["Qtd"]     = df["Qtd"].apply(parse_numero_br)
        df["Preco"]   = df["Preco"].apply(parse_numero_br)
        df["Valor"]   = df["Qtd"] * df["Preco"]

    df["Mercado"] = "Internacional"
    return df[["Data", "Ticker", "Tipo", "Qtd", "Preco", "Valor", "Mercado"]]


# Mapeamento de Categoria do Status Invest → Mercado usado no relatório
_CATEGORIA_PARA_MERCADO = {
    "Ações":         "Nacional",
    "FII":           "Nacional",
    "Tesouro direto": "Tesouro Direto",
    "Stocks":        "Internacional",
    "ETF Exterior":  "Internacional",
    "ETF":           "Nacional",
    "BDR":           "Nacional",
}


def carrega_status_invest(arquivo: str) -> pd.DataFrame:
    """
    Lê o xlsx exportado do Status Invest (contém ativos nacionais, internacionais e tesouro).
    Colunas esperadas:
      Data operação | Categoria | Código Ativo | Operação C/V | Quantidade | Preço unitário | ...
    """
    df = pd.read_excel(arquivo)
    df.columns = df.columns.str.strip()

    df["Data"]   = pd.to_datetime(df["Data operação"], dayfirst=True, errors="coerce")
    df["Ticker"] = df["Código Ativo"].str.strip()
    df["Tipo"]   = df["Operação C/V"].str.strip().map({"C": "Compra", "V": "Venda"})
    df["Qtd"]    = df["Quantidade"].apply(parse_numero_br)
    df["Preco"]  = df["Preço unitário"].apply(parse_numero_br)
    df["Valor"]  = df["Qtd"] * df["Preco"]

    # Mapeia Categoria → Mercado; categorias desconhecidas ficam como "Outro"
    df["Mercado"] = df["Categoria"].str.strip().map(_CATEGORIA_PARA_MERCADO).fillna("Outro")

    categorias_desconhecidas = set(df[df["Mercado"] == "Outro"]["Categoria"].unique())
    if categorias_desconhecidas:
        print(f"[AVISO] Categorias não mapeadas (serão salvas como 'Outro'): {categorias_desconhecidas}")

    return df[["Data", "Ticker", "Tipo", "Qtd", "Preco", "Valor", "Mercado"]]


def calcula(df: pd.DataFrame):
    """
    Calcula preço médio acumulado e detalha cada venda com o ano da operação.
    O preço médio de compra é cumulativo (não reseta por ano).
    O lucro/prejuízo é registrado no ano em que a venda ocorreu.
    Retorna também a posição em carteira ao final de cada ano (para declaração IR).
    """
    df = df.sort_values("Data").reset_index(drop=True)

    resumo_linhas    = []
    detalhe_vendas   = []
    posicoes_por_ano = []   # snapshot ao final de cada ano calendário

    for (ticker, mercado), grupo in df.groupby(["Ticker", "Mercado"], sort=False):
        grupo = grupo.sort_values("Data")

        qtd_atual    = 0.0
        custo_total  = 0.0
        ano_anterior = None

        def _snapshot(ano_ref, qtd=None, custo=None):
            q = qtd   if qtd   is not None else qtd_atual
            c = custo if custo is not None else custo_total
            pm = (c / q) if q > 0 else 0.0
            posicoes_por_ano.append({
                "Ano":           ano_ref,
                "Mercado":       mercado,
                "Ticker":        ticker,
                "Qtd em 31/12":  round(q, 6),
                "Custo Total":   round(c, 2),
                "Preço Médio":   round(pm, 4),
            })

        for _, row in grupo.iterrows():
            ano = row["Data"].year

            # Ao cruzar a virada de ano, grava posição ao final do ano anterior
            if ano_anterior is not None and ano != ano_anterior:
                for a in range(ano_anterior, ano):
                    _snapshot(a)
            ano_anterior = ano

            if row["Tipo"] == "Compra":
                qtd_atual   += row["Qtd"]
                custo_total += row["Valor"]

            elif row["Tipo"] == "Venda":
                if qtd_atual > 0:
                    pm            = custo_total / qtd_atual
                    custo_vendido = pm * row["Qtd"]
                    resultado     = row["Valor"] - custo_vendido

                    custo_total -= custo_vendido
                    qtd_atual   -= row["Qtd"]

                    detalhe_vendas.append({
                        "Ano":                 ano,
                        "Mercado":             mercado,
                        "Ticker":              ticker,
                        "Data Venda":          row["Data"].strftime("%d/%m/%Y"),
                        "Qtd Vendida":         round(row["Qtd"], 6),
                        "Preço Médio Compra":  round(pm, 4),
                        "Preço Médio Venda":   round(row["Preco"], 4),
                        "Total Venda":         round(row["Valor"], 2),
                        "Lucro/Prejuízo":      round(resultado, 2),
                    })
                else:
                    detalhe_vendas.append({
                        "Ano":                 ano,
                        "Mercado":             mercado,
                        "Ticker":              ticker,
                        "Data Venda":          row["Data"].strftime("%d/%m/%Y"),
                        "Qtd Vendida":         round(row["Qtd"], 6),
                        "Preço Médio Compra":  "N/D",
                        "Preço Médio Venda":   round(row["Preco"], 4),
                        "Total Venda":         round(row["Valor"], 2),
                        "Lucro/Prejuízo":      "N/D",
                    })

        # Grava posição ao final do último ano com operações desse ticker
        if ano_anterior is not None:
            _snapshot(ano_anterior)

        pm_atual = (custo_total / qtd_atual) if qtd_atual > 0 else 0.0
        resumo_linhas.append({
            "Mercado":         mercado,
            "Ticker":          ticker,
            "Qtd em Carteira": round(qtd_atual, 6),
            "Custo Total":     round(custo_total, 2),
            "Preço Médio":     round(pm_atual, 4),
        })

    return (
        pd.DataFrame(resumo_linhas),
        pd.DataFrame(detalhe_vendas),
        pd.DataFrame(posicoes_por_ano),
    )


def lucro_num(series) -> float:
    return series.apply(lambda x: x if isinstance(x, (int, float)) else 0).sum()


# ── MAIN ─────────────────────────────────────────────────────────────────────
frames = []
if ARQUIVO_NACIONAL and Path(ARQUIVO_NACIONAL).exists():
    print(f"Carregando nacional: {ARQUIVO_NACIONAL}")
    frames.append(carrega_nacional(ARQUIVO_NACIONAL))
elif ARQUIVO_NACIONAL:
    print(f"[AVISO] Arquivo nacional não encontrado: {ARQUIVO_NACIONAL}")

if ARQUIVO_INTERNACIONAL and Path(ARQUIVO_INTERNACIONAL).exists():
    print(f"Carregando internacional: {ARQUIVO_INTERNACIONAL}")
    frames.append(carrega_internacional(ARQUIVO_INTERNACIONAL))
elif ARQUIVO_INTERNACIONAL:
    print(f"[AVISO] Arquivo internacional não encontrado: {ARQUIVO_INTERNACIONAL}")

if ARQUIVO_STATUS_INVEST and Path(ARQUIVO_STATUS_INVEST).exists():
    print(f"Carregando Status Invest: {ARQUIVO_STATUS_INVEST}")
    frames.append(carrega_status_invest(ARQUIVO_STATUS_INVEST))
elif ARQUIVO_STATUS_INVEST:
    print(f"[AVISO] Arquivo Status Invest não encontrado: {ARQUIVO_STATUS_INVEST}")

if not frames:
    print("Nenhum arquivo encontrado. Ajuste ARQUIVO_NACIONAL / ARQUIVO_INTERNACIONAL no topo do script.")
    exit(1)

df_total = pd.concat(frames, ignore_index=True)
df_resumo, df_vendas, df_posicoes = calcula(df_total)

df_resumo   = df_resumo.sort_values(["Mercado", "Ticker"])
df_vendas   = df_vendas.sort_values(["Ano", "Mercado", "Ticker", "Data Venda"])
df_posicoes = df_posicoes.sort_values(["Ano", "Mercado", "Ticker"])

# ── Terminal ─────────────────────────────────────────────────────────────────
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

print("\n" + "=" * 90)
print("POSIÇÃO ATUAL DA CARTEIRA")
print("=" * 90)
print(df_resumo.to_string(index=False))

if not df_vendas.empty:
    for ano, grupo_ano in df_vendas.groupby("Ano"):
        print(f"\n{'=' * 90}")
        print(f"VENDAS {ano}  —  Lucro/Prejuízo realizado: R$ {lucro_num(grupo_ano['Lucro/Prejuízo']):,.2f}")
        print("=" * 90)
        print(grupo_ano.drop(columns=["Ano"]).to_string(index=False))

# ── Excel ─────────────────────────────────────────────────────────────────────
SAIDA = "resultado_ir.xlsx"
with pd.ExcelWriter(SAIDA, engine="openpyxl") as writer:
    # Aba: posição atual completa
    df_resumo.to_excel(writer, sheet_name="Carteira Atual", index=False)

    # Abas por ano: vendas + posição em 31/12
    anos_vendas   = set(df_vendas["Ano"].unique()) if not df_vendas.empty else set()
    anos_posicoes = set(df_posicoes["Ano"].unique()) if not df_posicoes.empty else set()
    anos = sorted(anos_vendas | anos_posicoes)

    for ano in anos:
        # ── Aba Vendas {ano} ──────────────────────────────────────────────────
        if ano in anos_vendas:
            grupo_vendas = df_vendas[df_vendas["Ano"] == ano].drop(columns=["Ano"])
            grupo_vendas.to_excel(writer, sheet_name=f"Vendas {ano}", index=False)

        # ── Aba Resumo {ano}: posição em 31/12 + totais de vendas ─────────────
        posicao_ano = (
            df_posicoes[df_posicoes["Ano"] == ano]
            .drop(columns=["Ano"])
            .sort_values(["Mercado", "Ticker"])
        )

        # Totais de vendas desse ano por ticker
        if ano in anos_vendas:
            gv = df_vendas[df_vendas["Ano"] == ano]
            totais = (
                gv[gv["Lucro/Prejuízo"] != "N/D"]
                .assign(lp=lambda d: pd.to_numeric(d["Lucro/Prejuízo"]))
                .groupby(["Mercado", "Ticker"])
                .agg(Total_Vendido=("Total Venda", "sum"),
                     Lucro_Prejuizo=("lp", "sum"))
                .reset_index()
                .rename(columns={"Total_Vendido": "Total Vendido no Ano",
                                  "Lucro_Prejuizo": "Lucro/Prejuízo no Ano"})
            )
            resumo_ano = posicao_ano.merge(totais, on=["Mercado", "Ticker"], how="left")
        else:
            resumo_ano = posicao_ano.copy()
            resumo_ano["Total Vendido no Ano"]  = 0.0
            resumo_ano["Lucro/Prejuízo no Ano"] = 0.0

        resumo_ano.to_excel(writer, sheet_name=f"Resumo {ano}", index=False)

    # Aba com todas as vendas juntas (histórico completo)
    if not df_vendas.empty:
        df_vendas.to_excel(writer, sheet_name="Todas as Vendas", index=False)

print(f"\nSalvo em {SAIDA}")
print("Abas: Carteira Atual | Vendas XXXX | Resumo XXXX (posição 31/12 + vendas do ano) | Todas as Vendas")
