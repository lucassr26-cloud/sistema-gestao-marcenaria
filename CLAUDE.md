# CLAUDE.md — Sistema de Gestão de Marcenaria (LJ Wood Arts)

Contexto para o Claude Code. O dono é marceneiro (tábuas de churrasco end grain premium, Gravataí-RS), não programador:
explique mudanças em português simples e confirme antes de qualquer coisa que possa apagar ou alterar dados salvos.

## O que é
ERP leve de uma página (`index.html`: HTML + CSS + JS puro, sem build, sem dependências) com 8 abas:
Início/dashboards (`#view-ini`), Calculadoras (`#view-orc`: Precificação, Resina da canaleta e End Grain), Cotações (`#view-cot`), Pedidos (`#view-ped`),
Finanças (`#view-fin`: Contas a receber e Fluxo de caixa), Estoque (`#view-est`), Relatórios (`#view-rel`: Movimentos de estoque e Lançamentos financeiros, com Excel) e Cadastros (`#view-cad`: Máquinas, Serviços, Fichas técnicas e Conta e backup).
Interface em **pt-BR**. Moeda BRL via `Intl.NumberFormat('pt-BR')`. Campos numéricos aceitam vírgula (`parseLoose`).

## Persistência
`localStorage` (só neste navegador):
- `ljwa-estoque-v2` → `{ items: Item[] }`
- `ljwa-orcamento-v2` → estado da Calculadora (`quote`)
- `ljwa-vendas-v1` → `{ seqCot, seqPed, cotacoes: Cotacao[], pedidos: Pedido[] }`
- `ljwa-maquinas-v1` → `{ items: Maquina[] }`; `ljwa-servicos-v1` → `{ items: Servico[] }`; `ljwa-fichas-v1` → `{ items: Ficha[] }`
- `ljwa-precificacao-v1` → legado, usado só em migração
- `ljwa-sync-v1` (sessão, versão, pendências), `ljwa-supabase-v1` (endereço e chave colados na tela) e `ljwa-backup-meta-v1`: controle da nuvem, não entram no backup
Backup/restauração (aba Estoque) e pacote da nuvem: JSON `{ app:'ljwa-calculadora', versao:8, exportadoEm, estoque, orcamento, vendas, maquinas, fichas, servicos }`. `restoreObj` aceita backups antigos (sem máquinas/fichas/serviços).
**Nunca mude um formato salvo sem migração** que leia os dados antigos: o dono tem dados reais.

Existe uma variante hospedada no claude.ai que salva na conta Claude (capability `db`, documentos em
`data/users/<id>/estoque|orcamento|vendas`). Nesta versão standalone esse bloco foi removido.

## Modelo de dados
- **Unidades**: tudo guardado na unidade-base da família (`UNITS`): g, ml, cm, cm³, un… e `k` converte
  (kg = 1000 g; m³ = 1.000.000 cm³).
- **Item**: `{ id, nome, tipo:'madeira'|'insumo', unit, compras[], saidas[], baixas[], consumido? }`
  - madeira nova usa `unit:'m³'`; a compra guarda `dims:{c,l,e,n}` em cm.
  - `compras[]`: `{ id, data:'YYYY-MM-DD', qtd(base), valor, forn?, dims?, estorno?:{data,motivo} }`
  - `saidas[]` (manuais): `{ id, data(ISO), qtd, motivo, obs }`; `baixas[]` (produção): `{ id, data(ISO), qtd, pedido? }`
  - `consumido`: legado (baixas antigas sem data), tratado como saída no fim da linha do tempo.
- **Cotacao**: `{ id:'COT-0001', n, cliente, fone, data, validadeDias, peca, qtd, unitCartao, unitPix, custoUnit, lucroUnit,
  materiais[], perda, obs, status:'aberta'|'convertida'|'recusada', pedido?, calc }` (`calc` = cópia do estado da Calculadora)
- **Pedido**: `{ id:'PED-0001', n, tipo?:'estoque', cotacao, cliente, fone, peca, qtd, pagamento:'pix'|'cartao', unit, total,
  sinal, pagamentos?:[{id,data:'YYYY-MM-DD',valor,forma,obs,estorno?:{data,motivo}}], previsao, obs, status:'aberto'|'concluido'|'cancelado', concluidoEm?, canceladoEm?, baixa, materiais[], perda, custoUnit }`
- `materiais[]`: `{ item, nome, tipo, base }` (quantidade-base consumida por peça).
- **Maquina**: `{ id, nome, valor, residual, vidaAnos, horasMes, manutAno }`. Custo/hora = `(valor − residual)/(vidaAnos·12·horasMes) + manutAno/12/horasMes` (`maqHora`).
- **Ficha**: `{ id, nome, calc:{nome, dimC, dimL, dimE, perda, horas, madeira[], insumo[], maquinas[]}, criado }`. Ao carregar, mantém taxa, imposto, margem, custos fixos e valor/hora atuais.
- **Servico**: `{ id, nome, custo, unidade:'un'|'h'|'m'|'m2'|'kg', obs }`. `quote.servicos[]`: `{ id, item, qtd }` (custo = qtd × custo do serviço) ou `{ item:'avulso', nome, valor }` (valor digitado em R$). Entra no custo antes da margem (`srvRowCost`); a ficha técnica também guarda os serviços.
- `quote.maquinas[]`: `{ id, item, horas }` (uso de máquina na peça; custo entra antes da margem, igual aos insumos). `compute(q)` calcula todos os números do preço e é usado pela calculadora e pelas fichas.

## Regras de negócio (não quebrar)
1. **Custo médio ponderado móvel** (`itemTotals`): reprocessa os eventos em ordem de data; compra soma quantidade e valor;
   saída/baixa sai pelo custo médio do momento. Compras estornadas são ignoradas.
2. **Perda de madeira** (%) multiplica só materiais `tipo:'madeira'`, no preço e na baixa.
3. **Preço** = `custo / (1 − taxa − imposto − margem)`; Pix = mesma conta sem a taxa do cartão;
   preço de vitrine = arredonda para cima até a dezena e subtrai 0,10.
4. **IDs sequenciais** COT/PED nunca são reutilizados (`seqCot` e `seqPed` só crescem).
5. Concluir pedido grava baixas com `pedido:<id>`; reabrir ou estornar remove essas baixas (`desfazerBaixa`).
6. "Salvar como peça para estoque" cria um pedido `tipo:'estoque'` já concluído e dá baixa nos materiais.
7. **Contas a receber**: recebido = `sinal` + pagamentos não estornados; saldo = `total − recebido`. Fluxo de caixa: entrada = sinal (data do pedido) + pagamentos (data de cada um); saída = compras de estoque não estornadas. Pedidos cancelados e `tipo:'estoque'` ficam de fora.
8. **Margem exibida** (cotações e pedidos): lucro da marcenaria = preço − custo (já inclui a mão de obra) − taxa do cartão (só se cartão) − imposto; mão de obra = horas × valor/hora de `calc` (pedido novo guarda isso em `fin`; pedido antigo busca na cotação de origem).
9. **Venda de peça do estoque**: gera um pedido concluído novo com `origemEstoque:'PED-xxxx'` (cliente, data, preço final, `sinal` = total se já recebido). Peças restantes = `qtd` − soma das vendas não canceladas; zero restante = pedido de estoque "Vendido". Cancelar a venda devolve a peça ao estoque.
10. **Texto da cotação para o cliente** (`cotText`): inclui espécies de madeira (materiais tipo madeira), dimensão final (`quote.dimC/dimL/dimE`, copiada em `cotacao.dim`; cotação antiga tenta ler as medidas do nome da peça) e prazo fixo de 4 a 8 semanas.
11. **Cotação em PDF/imagem** (`cotCanvas`, `pdfDeJpeg`): folha A4 desenhada em canvas (logo embutido em base64, sem biblioteca); o PDF é montado à mão com a imagem JPEG. O conteúdo é medido e encolhe só se não couber.
12. **Nuvem (Supabase)**: login por e-mail e senha, um registro por usuário em `ljwa_dados` com `versao`; gravar usa `PATCH ... versao=eq.N` (se 0 linhas, houve conflito e o dono escolhe a versão). Backups em `ljwa_backups` (1 por dia, últimos 30, e um antes de trocar versões). Config em `config.js` ou colada na tela. Esquema em `supabase.sql`; passo a passo em `SINCRONIZACAO.md`.
13. **Pagamento do pedido** (aba Pedidos): `pctPago(pd)` = recebido ÷ total. Cartão do pedido mostra "Sinal X%", "Pago 100%", "Aguardando pagamento" (concluído com saldo) ou "Liberado para envio" (concluído e quitado). O botão Registrar pagamento do pedido usa o mesmo `payForm` das Contas a receber. Filtros: Em produção com sinal e Aguardando pagamento.
14. **Relatórios** (`relEstoqueRows`, `relFinRows`): movimentos de estoque (compras = entrada; baixas de produção e saídas manuais = saída, valorizadas pelo custo médio do momento, mesma lógica do `itemTotals`) e lançamentos financeiros (sinal, pagamentos e vendas de peças = entrada; compras de estoque = saída). Estornos aparecem como "Estornado" e ficam fora dos totais; pedidos cancelados idem. Cada linha leva a origem em Observações. Filtros por período, tipo, item e busca.
15. **Excel (.xlsx)** (`xlsxBlob`, `zipBlob`): arquivo escrito à mão (zip sem compressão + XML), sem bibliotecas, funciona offline. Duas abas por relatório: dados (filtro e linha fixa) e Resumo (totais por SUMIFS, por mês/categoria ou por item).
16. Correção de lançamento usa **estorno** (mantém o histórico), nunca exclusão silenciosa.

## Interface
- Mobile-first (usado no celular, na oficina): alvos de toque ≥ 44 px; abas viram grade de 3 colunas abaixo de 480 px.
- Cores como variáveis em `:root`, com tema escuro (`prefers-color-scheme`); paleta preto e branco da marca (logo em `logo.png`; `icon.png` é o ícone do app).
  Fontes: Fraunces (títulos) e Manrope (texto).
- Ações destrutivas pedem confirmação em dois toques (`arm()`).

## Testes
`python tests/smoke_test.py` (Playwright + Chromium). Rode depois de qualquer mudança em cálculo, estoque ou vendas.
`python tests/sync_test.py` testa login, sincronização, conflito e backups contra `tests/mock_supabase.py` (imita o Supabase, sem internet).

## Deploy
Publicado no GitHub Pages (branch `main`, pasta raiz): https://lucassr26-cloud.github.io/sistema-gestao-marcenaria/ . Cada push em `main` atualiza o site.

## Próximos passos possíveis (combinar com o dono antes)
- Despesas avulsas (aluguel, energia, frete) no fluxo de caixa.
- Separar `index.html` em `styles.css` + módulos JS (storage, estoque, vendas, calculadora), mantendo sem build.
- PWA (manifest + service worker) para abrir offline na oficina.
- Relatórios: margem real por pedido e giro de estoque por espécie.

Resina da canaleta guarda só as últimas medidas em `ljwa-resina-v1` (fora do backup).

## End Grain (calculadora simples de filetes)
Entrada: comprimento, largura e espessura finais (cm); ajustes opcionais (largura do filete, sobra, serra, margem, largura da madeira). Guarda em `ljwa-filetes-v1` (fora do backup). `fiCalc` é função pura (marcada `FI-CALC-START/END`).
- Filete `a` = espessura final (salvo ajuste); largura no corte = `a + sobra`; fatia `ws = E + sobra`.
- `n = ⌈(medida + sobra)/a⌉` filetes, `m = ⌈(outra medida + sobra)/a⌉` fatias; comprimento do filete `S = m·ws + (m−1)·serra + 2·sobra`; escolhe a orientação que gasta menos.
- Número em destaque = metros lineares da madeira: `n·S/k/100` (×(1+margem)), com `k = ⌊(largura da madeira + serra)/(largura no corte + serra)⌋` filetes cortados lado a lado. Referência real do dono: tábua 50x30x4,5 gasta ~80 cm lineares (a calculadora dá 0,81 m com madeira de 30 cm de largura). A tela mostra só: metros lineares da madeira, quantidade de filetes e largura do corte (`E + sobra`, que vira a espessura). Comprimento do filete e blocos não são exibidos (o dono não usa essa informação). Conferência do dono: 40x25x4,5 ≈ 50 cm lineares (dá 0,52 m); 50x30x4,5 ≈ 80 cm (dá 0,81 m).
