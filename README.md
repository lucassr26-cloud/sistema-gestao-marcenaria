# Sistema de Gestão de Marcenaria (LJ Wood Arts)

Sistema de gestão da marcenaria LJ Wood Arts (tábuas de churrasco end grain, Gravataí-RS).
Site de uma página só, sem servidor: os dados ficam no navegador.

## Módulos
- **Início**: painel com pedidos em aberto, nível de estoque, recomendações de compra e fluxo de caixa.
- **Calculadoras**: precificação da peça (madeira, insumos, horas, custos fixos, taxas e lucro), resina da canaleta (linear × largura × espessura, 2/3 resina e 1/3 endurecedor) e End Grain (filetes, largura no corte e metros lineares a partir da tábua final).
- **Cotações**: numeradas (COT-0001…), com cliente, validade e texto pronto para WhatsApp.
- **Pedidos**: numerados (PED-0001…), em produção até a conclusão; ao concluir, dá baixa no estoque.
- **Finanças**: contas a receber (pagamentos por pedido, cobrança no WhatsApp) e fluxo de caixa mensal.
- **Estoque**: compras com custo médio ponderado móvel, madeira em m³, estornos, saídas e histórico.

## Como abrir
Abra `index.html` no navegador. Para publicar: arraste a pasta no Netlify (aba Deploys) ou use `netlify deploy --prod`.

## Backup
Aba Estoque → Baixar backup (arquivo JSON). Restaure pelo mesmo lugar.

## Teste
`python tests/smoke_test.py` (requer Playwright).
