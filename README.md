# Sistema de Gestão de Marcenaria (LJ Wood Arts)

Sistema de gestão da marcenaria LJ Wood Arts (tábuas de churrasco end grain, Gravataí-RS).
Site de uma página só, sem servidor: os dados ficam no navegador.

## Módulos
- **Início**: painel com pedidos em aberto, nível de estoque, recomendações de compra e contas a receber.
- **Calculadoras**: precificação da peça (madeira, insumos, **máquinas**, **serviços**, horas, custos fixos, taxas e lucro; com **fichas técnicas**), resina da canaleta e End Grain (filetes e metros lineares).
- **Cotações**: numeradas (COT-0001…), com cliente, validade, texto para WhatsApp e **documento em PDF ou imagem**.
- **Pedidos**: numerados (PED-0001…), em produção até a conclusão; ao concluir, dá baixa no estoque.
- **Finanças**: contas a receber (pagamentos por pedido) e fluxo de caixa mensal.
- **Estoque**: compras com custo médio ponderado móvel, madeira em m³, estornos, saídas e histórico.
- **Relatórios**: movimentos de estoque e lançamentos financeiros, com filtro por período e exportação para **Excel** (observações com a origem de cada lançamento).
- **Cadastros**: **máquinas** (depreciação por hora de uso), **serviços** (laser, plaina, frete), **fichas técnicas** por tipo de peça e **conta e backup** (login, sincronização entre aparelhos e backups na nuvem).

## Como abrir
Abra `index.html` no navegador. Para publicar: arraste a pasta no Netlify (aba Deploys) ou use `netlify deploy --prod`.

## Sincronização e backup
Passo a passo em `SINCRONIZACAO.md` (Supabase gratuito; esquema em `supabase.sql`). Sem a nuvem, os dados ficam no navegador e o backup é feito na aba Estoque (arquivo ou texto).

## Testes
`python tests/smoke_test.py` e `python tests/sync_test.py` (requerem Playwright).
