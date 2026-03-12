# IR Calculator

Calcula preço médio de compra e lucro/prejuízo por venda, gerando um relatório Excel separado por ano para auxiliar na declaração do Imposto de Renda.

---

### Ideia do projeto

Hoje a b3 não da suporte mais a integração pela api oficial, apenas sendo possível exportar o xlsx. Para não ter que pagar nenhuma calculadora de IR, é possível utilizar a B3 e exportar o xlsx ou outras plataformas e utilizar o script para calcular.

## Instalação

```bash
pip install pandas openpyxl
```

---

## Como usar

### 1. Exporte suas negociações

**Opção A — Exportar do Investidor B3 (ações nacionais)**

Acesse https://www.investidor.b3.com.br/extrato/negociacao, selecione o período e exporte o Excel.

![Tela de negociações do Investidor B3](docs/b3-tela-negociacao.png)

![Modal de exportação do período](docs/b3-modal-exportar.png)

Salve como `nacional.xlsx` na pasta do script.

**Opção B — Exportar do Status Invest (todos os ativos + internacional)**

Exporte o histórico de operações do Status Invest e salve como `status-invest.xlsx`. O script detecta automaticamente a categoria de cada ativo:

| Categoria no arquivo | Mercado no relatório |
|---|---|
| Ações, FII, ETF, BDR | Nacional |
| Stocks, ETF Exterior | Internacional |
| Tesouro direto | Tesouro Direto |

**Opção C — Arquivo da corretora (ativos internacionais)**

Exportado pela corretora (Inter, Apex, etc.) com as colunas: `Data operação`, `Código Ativo`, `Operação C/V`, `Quantidade`, `Preço unitário`. Salve como `internacional.xlsx`.

---

### 2. Configure o script

Abra `seven-biz-calculate.py` e ajuste as variáveis no topo:

```python
ARQUIVO_NACIONAL      = "nacional.xlsx"       # ou None
ARQUIVO_INTERNACIONAL = "internacional.xlsx"  # ou None
ARQUIVO_STATUS_INVEST = "status-invest.xlsx"  # ou None
```

Os três podem ser usados juntos ou separados.

### 3. Execute

```bash
python3 seven-biz-calculate.py
```

Gera o arquivo `resultado_ir.xlsx` com as abas:

| Aba | Conteúdo |
|---|---|
| Carteira Atual | Posição atual: qtd, custo total, preço médio |
| Vendas XXXX | Detalhe de cada venda do ano |
| Resumo XXXX | Posição em 31/12 + resultado das vendas — use para declarar o IR |
| Todas as Vendas | Histórico completo de vendas |

---

## Observações

- O preço médio é cumulativo entre anos: compras de 2022 afetam o preço médio numa venda de 2024.
- Cada ano é independente para fins de IR. Lucros e prejuízos de anos diferentes não se compensam.
- Desdobramentos (splits) não são calculados automaticamente. Se um ativo sofreu split, ajuste manualmente os dados de compra antes de rodar o script.
- Os arquivos `nacional.xlsx`, `internacional.xlsx`, `status-invest.xlsx` e `resultado_ir.xlsx` estão no `.gitignore`.

---

## Roadmap

- Suporte automático a desdobramentos (splits e inplits)
- Agrupamento por mês para cálculo de imposto mensal sobre day trade
- Sugestão de DARF a pagar por mês

---

## Contribuindo

Pull requests são bem-vindos. Para mudanças maiores, abra uma issue primeiro para discutir o que você gostaria de mudar.

---

## Licença

[Apache 2.0](LICENSE)

