"""Teste de fumaça ponta a ponta: estoque -> calculadora -> cotação -> pedido -> baixa.
Rodar:  pip install playwright && playwright install chromium && python tests/smoke_test.py
"""
import pathlib
from playwright.sync_api import sync_playwright

INDEX = (pathlib.Path(__file__).resolve().parent.parent / "index.html").as_uri()
import tempfile, os
XLSX_ESTOQUE = os.path.join(tempfile.gettempdir(), "ljwa-teste-estoque.xlsx")
XLSX_FIN = os.path.join(tempfile.gettempdir(), "ljwa-teste-financeiro.xlsx")

def main():
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 390, "height": 844})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(INDEX); pg.wait_for_timeout(300)
        # Estoque: compra de madeira por dimensões e de insumo por peso
        pg.click("#tab-est"); pg.fill("#b-nome", "Muiracatiara"); pg.click("[data-tipo=madeira]")
        pg.fill("#b-c", "250"); pg.fill("#b-l", "30"); pg.fill("#b-e", "5"); pg.fill("#b-valor", "150")
        pg.click("#buy button[type=submit]")
        pg.fill("#b-nome", "Resina epóxi"); pg.click("[data-tipo=insumo]"); pg.fill("#b-qtd", "1")
        pg.select_option("#b-un", "kg"); pg.fill("#b-valor", "120"); pg.click("#buy button[type=submit]")
        # Calculadora
        pg.click("#tab-orc")
        pg.query_selector("#rows-madeira .use-top select").select_option(label="Muiracatiara")
        d = pg.query_selector_all("#rows-madeira .use-dims input"); d[0].fill("40"); d[1].fill("30"); d[2].fill("3,5")
        pg.query_selector("#rows-insumo .use-top select").select_option(label="Resina epóxi")
        pg.fill("#rows-insumo .use-bot input", "150"); pg.query_selector("#rows-insumo .use-bot select").select_option("g")
        assert pg.text_content("#preco") != "R$ 0,00"
        # Cotação -> pedido -> conclusão
        pg.fill("#nome", "End grain Muiracatiara"); pg.fill("#dimC", "40"); pg.fill("#dimL", "30"); pg.fill("#dimE", "3,5")
        pg.click("#save-cot"); pg.fill("#sc-cli", "Cliente Teste"); pg.fill("#sc-qtd", "2"); pg.click("#save-cot-panel .primary")
        assert "COT-0001" in pg.text_content("#status")
        pg.evaluate("() => { window.__c = null; Object.defineProperty(navigator, 'clipboard', {value: {writeText: (x) => { window.__c = x; return Promise.resolve(); }}, configurable: true}); }")
        pg.click("#tab-cot"); pg.click("text=Copiar para o cliente"); msg = pg.evaluate("() => window.__c")
        assert "Madeira: Muiracatiara" in msg and "Dimensão final: 40 x 30 x 3,5 cm" in msg, msg
        assert "Prazo de entrega: de 4 a 8 semanas, a depender da complexidade do projeto." in msg, msg
        assert "Valor no Pix: R$" in msg and "Parcelado no cartão: consultar taxa." in msg and "Valor no cartão" not in msg, msg
        assert "Condição de pagamento:\n50% ao fechar o pedido\n50% na postagem na transportadora ou entrega presencial em mãos." in msg, msg
        pg.click("#tab-cot"); ct = pg.inner_text("#cot-list")
        assert "Lucro da marcenaria" in ct and "mão de obra" in ct and "no Pix" in ct, ct
        pg.click("#tab-cot"); pg.click("text=Converter em pedido")
        sug = pg.input_value("[id^=cv-v-]"); assert sug not in ("", "0"), sug
        pg.fill("[id^=cv-v-]", "1000"); assert "R$ 1.000,00" in pg.inner_text("#cot-list .panel").replace("\xa0", " ")
        pg.click("#cot-list .panel .primary")
        assert "PED-0001" in pg.text_content("#cot-msg")
        # Pedido em produção que já foi vendido e recebeu sinal: mostra % pago e só libera o envio com 100%
        pg.click("#tab-ped"); lst = pg.inner_text("#ped-list")
        assert "Sem sinal" in lst and "0% pago" in lst and "só é liberado com 100%" in lst, lst
        pg.click("#ped-list button:has-text('Registrar pagamento')"); pg.fill("[id^=pg-v-]", "100"); pg.click("#ped-list .panel .primary")
        assert "10% pago" in pg.text_content("#ped-msg") and "R$ 100,00" in pg.text_content("#ped-msg").replace("\xa0", " "), pg.text_content("#ped-msg")
        lst = pg.inner_text("#ped-list").replace("\xa0", " ")
        assert "Sinal 10%" in lst and "R$ 100,00 de R$ 1.000,00 (10% pago)" in lst and "falta R$ 900,00" in lst, lst
        pg.click("[data-pf=sinal]"); assert "PED-0001" in pg.inner_text("#ped-list")                 # filtro: em produção com sinal
        pg.click("[data-pf=receber]"); assert "PED-0001" in pg.inner_text("#ped-list")               # filtro: aguardando pagamento
        pg.click("[data-pf=aberto]")
        pg.click("#tab-ini"); assert "10% pago" in pg.inner_text("#d-ped") and "1 com sinal" in pg.inner_text("#kpis"), pg.inner_text("#d-ped")
        pg.click("#tab-ped"); pg.click("text=Concluir produção"); pg.click("#ped-list .panel .primary")
        assert "concluído" in pg.text_content("#ped-msg")
        pg.click("#tab-ped"); pg.click("[data-pf=concluido]"); pd_txt = pg.inner_text("#ped-list")
        assert "Lucro da marcenaria" in pd_txt and "mão de obra" in pd_txt and "%" in pd_txt, pd_txt
        # Estoque após baixa: 0,0375 - (0,0042 x 2 x 1,2) = 0,0274 m³ ; resina 1 kg - 300 g = 0,7 kg
        pg.click("#tab-est"); txt = pg.inner_text("#items")
        assert "0,0274 m³" in txt and "0,7 kg" in txt, txt
        # Tela inicial: dashboards com os dados do fluxo acima
        pg.click("#tab-ini"); ini = pg.inner_text("#view-ini")
        assert "Pedidos em produção" in ini and "Contas a receber" in ini and "Recomendações de compra" in ini, ini
        assert "Peças prontas em estoque" in ini and "Nenhuma peça pronta" in ini, ini
        # Finanças: pedido concluído sem pagamento aparece a receber; registrar o saldo total quita
        pg.click("#tab-fin"); rec = pg.inner_text("#rec-list")
        assert "PED-0001" in rec and "Falta pagar" in rec, rec
        pg.click("#rec-list button:has-text('Registrar pagamento')"); pg.click("#rec-list .panel .primary")
        assert "quitado" in pg.text_content("#rec-msg"), pg.text_content("#rec-msg")
        assert "Nada a receber" in pg.inner_text("#rec-list")
        pg.click("#sub-caixa"); cash = pg.inner_text("#fin-cash").replace("\xa0", " ")
        assert "R$ 270,00" in cash and "Entrou" in cash, cash   # compras do mês (150 + 120)
        assert "R$ 0,00" not in pg.inner_text("#fin-kpis").split("Entradas")[1].split("Saídas")[0], pg.inner_text("#fin-kpis")  # entrada registrada
        # Resina da canaleta: linear = 40 + 40 + 2 x média(30, 34) = 144 cm; x 2 cm x 10 mm = 288 ml; 2/3 resina e 1/3 endurecedor
        pg.click("#tab-orc"); pg.click("#sub-resina")
        for k, v in {"ma1": "40", "ma2": "40", "me1": "30", "me2": "34", "larg": "2", "prof": "10", "pecas": "1", "folga": "0"}.items():
            pg.fill("#r-" + k, v)
        assert pg.text_content("#r-lin") == "144 cm", pg.text_content("#r-lin")
        assert pg.text_content("#r-total") == "288 ml", pg.text_content("#r-total")
        assert pg.text_content("#r-a") == "192 ml" and pg.text_content("#r-b") == "96 ml"
        # Botão x limpa o campo e recalcula
        assert pg.is_visible("#r-ma1 >> xpath=../button")
        pg.click("#r-ma1 >> xpath=../button")
        assert pg.input_value("#r-ma1") == "" and pg.text_content("#r-lin") == "104 cm", pg.text_content("#r-lin")
        # Alternar branco/preto
        pg.click("#th-dark"); assert pg.get_attribute("html", "data-theme") == "dark"
        assert pg.evaluate("() => getComputedStyle(document.body).backgroundColor") == "rgb(11, 11, 11)"
        pg.click("#th-light"); assert pg.get_attribute("html", "data-theme") == "light"
        assert pg.title() == "Sistema de Gestão de Marcenaria"
        # Peça para estoque -> venda (fecha o pedido de estoque e gera pedido concluído com cliente, preço e data)
        pg.click("#tab-orc"); pg.click("#sub-preco"); pg.click("#baixa"); pg.fill("#pe-q", "2"); pg.click("#estq-panel .panel .primary")
        pg.click("#tab-ped"); pg.click("[data-pf=estoque]")
        assert "Em estoque" in pg.inner_text("#ped-list")
        pg.click("text=Copiar para o cliente"); eg = pg.evaluate("() => window.__c")
        assert "Peça disponível" in eg and "Dimensão final: 40 x 30 x 3,5 cm" in eg and "Madeira: Muiracatiara" in eg and "pronta entrega" in eg and "50% ao fechar o pedido" in eg, eg
        assert "Parcelado no cartão: consultar taxa." in eg and "Valor no cartão" not in eg, eg
        pg.click("text=Registrar venda"); pg.fill("[id^=vd-c-]", "Carlos Souza"); pg.fill("[id^=vd-q-]", "2")
        pg.fill("[id^=vd-p-]", "900"); pg.fill("[id^=vd-d-]", "2026-10-20"); pg.fill("[id^=vd-o-]", "Retirou na oficina")
        pg.click("#ped-list .panel .primary")
        assert "fechado" in pg.text_content("#ped-msg"), pg.text_content("#ped-msg")
        est_txt = pg.inner_text("#ped-list")
        assert "Vendido" in est_txt and "Carlos Souza" in est_txt and "Retirou na oficina" in est_txt, est_txt
        pg.click("#tab-fin"); pg.click("#sub-rec"); pg.click("[data-rcf=quitado]"); q = pg.inner_text("#rec-list")
        assert "Carlos Souza" in q and "Quitado" in q, q   # venda recebida entra em Finanças
        pg.click("#tab-ini"); assert "Nenhuma peça pronta" in pg.inner_text("#kpis")
        # Filetes End Grain: tábua 40 x 25 x 4,5 em madeira de 30 cm de largura -> ~50 cm lineares (0,52 m com margem), 6 filetes de 4,8 cm
        pg.click("#tab-orc"); pg.click("#sub-fil")
        pg.fill("#fi-C", "40"); pg.fill("#fi-L", "25"); pg.fill("#fi-E", "4,5"); pg.fill("#fi-W0", "30")
        fr = pg.inner_text("#fi-res").replace("\xa0", " ")
        assert "0,52 m" in fr and "52 cm" in fr and "4,8 cm" in fr, fr
        assert pg.text_content("#fi-q") == "6", pg.text_content("#fi-q")
        assert "comprimento de cada filete" not in fr.lower() and "blocos" not in fr.lower(), fr
        pg.fill("#fi-C", "50"); pg.fill("#fi-L", "30"); assert "0,81 m" in pg.inner_text("#fi-m").replace("\xa0", " ")   # 50 x 30 x 4,5 ~ 80 cm
        pg.fill("#fi-W0", ""); assert "Informe a largura da madeira" in pg.inner_text("#fi-m-l")
        pg.fill("#fi-C", ""); assert "Digite comprimento" in pg.inner_text("#fi-erro")
        pg.fill("#fi-C", "50"); pg.fill("#fi-W0", "30")
        # Máquinas: custo por hora = (6000 - 1000) / (10 anos x 12 meses x 80 h) + 240 / 12 / 80 = R$ 0,77
        pg.click("#tab-cad"); pg.click("#cb-maq")
        pg.fill("#mq-nome", "Serra de bancada"); pg.fill("#mq-valor", "6000"); pg.fill("#mq-res", "1000"); pg.fill("#mq-vida", "10"); pg.fill("#mq-horas", "80"); pg.fill("#mq-manut", "240")
        assert "R$ 0,77" in pg.inner_text("#mq-hora").replace("\xa0", " "), pg.inner_text("#mq-hora")
        pg.click("#mq-save"); assert "Serra de bancada" in pg.inner_text("#mq-list")
        pg.click("#tab-orc"); pg.click("#sub-preco"); pg.click("#add-maq")
        pg.select_option("#rows-maq select", label="Serra de bancada"); pg.fill("#rows-maq .use-bot input", "2")
        assert "R$ 1,54" in pg.inner_text("#tot-maq").replace("\xa0", " "), pg.inner_text("#tot-maq")   # 2 h x R$ 0,77
        assert "Máquinas (depreciação)" in pg.inner_text("#legend")
        # Ficha técnica: salvar, limpar e carregar de volta
        pg.fill("#nome", "Tábua de teste"); pg.click("#fic-save"); pg.click("#fic-panel .panel .primary")
        assert "salva" in pg.text_content("#fic-msg"), pg.text_content("#fic-msg")
        pg.click("#reset"); assert "Nenhuma máquina" in pg.inner_text("#rows-maq")
        pg.select_option("#fic-sel", label="Tábua de teste")
        assert pg.input_value("#nome") == "Tábua de teste" and "R$ 1,54" in pg.inner_text("#tot-maq").replace("\xa0", " ")
        pg.click("#tab-cad"); pg.click("#cb-fic"); assert "Tábua de teste" in pg.inner_text("#fc-list")
        # Serviços: cadastro e uso no orçamento
        pg.click("#tab-cad"); pg.click("#cb-srv")
        pg.fill("#sv-nome", "Gravação a laser"); pg.fill("#sv-custo", "40"); pg.click("#sv-save")
        pg.fill("#sv-nome", "Plaina"); pg.fill("#sv-custo", "60"); pg.select_option("#sv-un", "h"); pg.click("#sv-save")
        assert "Gravação a laser" in pg.inner_text("#sv-list") and "por hora" in pg.inner_text("#sv-list")
        pg.click("#tab-orc"); pg.click("#sub-preco"); pg.click("#add-srv")
        pg.select_option("#rows-srv .use:nth-child(1) select", label="Gravação a laser")
        pg.click("#add-srv"); pg.select_option("#rows-srv .use:nth-child(2) select", label="Plaina"); pg.fill("#rows-srv .use:nth-child(2) .use-bot input", "1,5")
        pg.click("#add-srv"); pg.select_option("#rows-srv .use:nth-child(3) select", label="Outro serviço (digitar R$)"); pg.fill("#rows-srv .use:nth-child(3) input[aria-label='Valor do serviço em reais']", "55")
        assert "R$ 185,00" in pg.inner_text("#tot-srv").replace("\xa0", " "), pg.inner_text("#tot-srv")   # 40 + 1,5 h x 60 + 55
        assert "Serviços" in pg.inner_text("#legend")
        pg.click("#fic-save"); pg.fill("#fic-nome", "Com serviços"); pg.click("#fic-panel .panel .primary"); pg.click("#reset")
        assert "Nenhum serviço" in pg.inner_text("#rows-srv")
        pg.select_option("#fic-sel", label="Com serviços"); assert "R$ 185,00" in pg.inner_text("#tot-srv").replace("\xa0", " ")
        # Cotação em PDF e em imagem
        pg.click("#tab-cot"); pg.click("[data-cf=todas]"); pg.click("text=Documento PDF ou imagem")
        pg.wait_for_selector("#cot-list .panel canvas")
        with pg.expect_download() as dl:
            pg.click("#cot-list .panel button:has-text('Salvar PDF')")
        pdf = open(dl.value.path(), "rb").read()
        assert pdf[:5] == b"%PDF-" and pdf.rstrip().endswith(b"%%EOF") and len(pdf) > 20000 and dl.value.suggested_filename.endswith(".pdf"), (len(pdf), dl.value.suggested_filename)
        with pg.expect_download() as dl2:
            pg.click("#cot-list .panel button:has-text('Salvar imagem')")
        png = open(dl2.value.path(), "rb").read()
        assert png[:4] == b"\x89PNG" and len(png) > 20000 and dl2.value.suggested_filename.endswith(".png")
        # Lançamento manual de caixa: saldo inicial de R$ 600 e uma saída de R$ 80
        import re
        def num(txt):
            m = re.search(r"R\$\s*(-?[\d.]+,\d\d)", txt.replace("\xa0", " ")); return float(m.group(1).replace(".", "").replace(",", ".")) if m else None
        pg.click("#tab-fin"); pg.click("#sub-lan")
        antes = num(pg.inner_text("#fin-kpis"))
        pg.click("#ln-saldo"); pg.fill("#ln-valor", "600"); pg.fill("#ln-obs", "Dinheiro que havia na gaveta da oficina"); pg.click("#ln-salvar")
        assert "Saldo inicial do caixa" in pg.inner_text("#ln-list") and "Dinheiro que havia na gaveta" in pg.inner_text("#ln-list")
        assert abs(num(pg.inner_text("#fin-kpis")) - (antes + 600)) < 0.01, (antes, pg.inner_text("#fin-kpis"))
        pg.click("[data-lt=saida]"); pg.select_option("#ln-cat", "Frete"); pg.fill("#ln-valor", "80"); pg.fill("#ln-obs", "Frete da tábua do cliente teste"); pg.click("#ln-salvar")
        assert abs(num(pg.inner_text("#fin-kpis")) - (antes + 520)) < 0.01
        pg.click("#tab-ini"); assert "Saldo em caixa" in pg.inner_text("#kpis") and abs(num(pg.inner_text("#kpis").split("Saldo em caixa")[1]) - (antes + 520)) < 0.01
        pg.click("#tab-rel"); pg.click("[data-rp=mes]"); pg.click("#rb-fin"); fl = pg.inner_text("#rel-list").replace("\xa0", " ")
        assert "Saldo inicial do caixa" in fl and "Lançamento manual no caixa" in fl and "Frete da tábua do cliente teste" in fl, fl
        with pg.expect_download() as dz:
            pg.click("#rel-xlsx")
        try:
            import openpyxl
            dz.value.save_as(XLSX_FIN); wz = openpyxl.load_workbook(XLSX_FIN)["Lançamentos"]
            obs = [c.value for c in wz["L"]]; docs = [c.value for c in wz["E"]]
            assert "Lançamento manual" in docs and any("gaveta da oficina" in str(o) for o in obs), obs
        except ImportError:
            pass
        pg.click("#tab-fin"); pg.click("#sub-lan")
        pg.click("#ln-list .doc:has-text('Frete') button:has-text('Estornar')"); pg.click("#ln-list .doc:has-text('Frete') button:has-text('Confirmar estorno')")
        assert abs(num(pg.inner_text("#fin-kpis")) - (antes + 600)) < 0.01 and "Estornado" in pg.inner_text("#ln-list")   # estorno devolve o saldo e mantém o histórico
        # Relatório de movimentos de estoque, com filtro de período, e exportação para Excel
        pg.click("#tab-rel"); pg.click("#rb-est"); pg.click("[data-rp=mes]")
        rel = pg.inner_text("#rel-list").replace("\xa0", " ")
        assert "Compra" in rel and "Muiracatiara" in rel and "Baixa de produção do pedido PED-0001" in rel, rel
        assert "R$ 270,00" in pg.inner_text("#rel-kpis").replace("\xa0", " "), pg.inner_text("#rel-kpis")      # compras de 150 + 120
        pg.click("[data-rt=saida]"); assert "Baixa de produção" in pg.inner_text("#rel-list") and "Compra lançada" not in pg.inner_text("#rel-list")
        pg.click("[data-rt=todos]")
        pg.fill("#rel-de", "2020-01-01"); pg.fill("#rel-ate", "2020-12-31"); assert "Nenhum lançamento" in pg.inner_text("#rel-list")   # período sem movimento
        pg.click("[data-rp=mes]")
        with pg.expect_download() as dx:
            pg.click("#rel-xlsx")
        open(XLSX_ESTOQUE, "wb").write(open(dx.value.path(), "rb").read())
        assert dx.value.suggested_filename.endswith(".xlsx")
        pg.click("#rb-fin"); fin = pg.inner_text("#rel-list").replace("\xa0", " ")
        assert "Pagamento de pedido" in fin and "Compra de madeira" in fin and "Recebimento registrado em Contas a receber do pedido PED-0001" in fin, fin
        with pg.expect_download() as dy:
            pg.click("#rel-xlsx")
        open(XLSX_FIN, "wb").write(open(dy.value.path(), "rb").read())
        # As planilhas são arquivos .xlsx válidos (zip íntegro; se o openpyxl existir, confere abas, cabeçalho e dados)
        import zipfile
        for f in (XLSX_ESTOQUE, XLSX_FIN):
            z = zipfile.ZipFile(f); assert z.testzip() is None and "xl/workbook.xml" in z.namelist() and "xl/worksheets/sheet2.xml" in z.namelist()
        try:
            import openpyxl
            w1 = openpyxl.load_workbook(XLSX_ESTOQUE); assert w1.sheetnames == ["Movimentos", "Resumo"] and w1["Movimentos"]["B1"].value == "Tipo" and w1["Movimentos"].max_row >= 4
            w2 = openpyxl.load_workbook(XLSX_FIN); assert w2.sheetnames == ["Lançamentos", "Resumo"] and w2["Lançamentos"]["L1"].value.startswith("Observações") and "PED-0001" in str([c.value for c in w2["Lançamentos"]["E"]])
        except ImportError:
            pass
        # Margem e distribuição de custos nas cotações e nos pedidos (mesma pizza e mesmos números da calculadora)
        def valores_legenda(sel):
            return [float(m.replace(".", "").replace(",", ".")) for m in re.findall(r"R\$\s*(-?[\d.]+,\d\d)", pg.inner_text(sel).replace("\xa0", " "))]
        pg.click("#tab-cot"); pg.click("[data-cf=todas]")
        pg.click("#cot-list .doc:has-text('COT-0001') summary:has-text('Margem e distribuição')")
        pg.wait_for_selector("#cot-list .doc:has-text('COT-0001') .board svg")
        legpix = pg.inner_text("#cot-list .doc:has-text('COT-0001') .legend").replace("\xa0", " ")
        assert "Madeira com perda" in legpix and "Seu trabalho" in legpix and "Taxa e imposto" in legpix and "Lucro" in legpix, legpix
        cx = pg.inner_text("#cot-list .doc:has-text('COT-0001') .cards").replace("\xa0", " ")
        assert "Custo total das 2 peças" in cx and "Lucro da marcenaria" in cx and "Preço mínimo" in cx and "Mão de obra" in cx, cx
        centro = num(pg.text_content("#cot-list .doc:has-text('COT-0001') .board svg text:nth-of-type(2)"))
        soma = sum(valores_legenda("#cot-list .doc:has-text('COT-0001') .legend")); assert abs(soma - centro) < 0.05, (soma, centro)   # as partes somam o preço
        assert "Preço no Pix" in pg.inner_text("#cot-list .doc:has-text('COT-0001') .board")
        pg.click("#cot-list .doc:has-text('COT-0001') button:has-text('No cartão')"); assert "Preço no cartão" in pg.inner_text("#cot-list .doc:has-text('COT-0001') .board")
        pg.click("#tab-ped"); pg.click("[data-pf=todos]")
        pg.click("#ped-list .doc:has-text('PED-0001') summary:has-text('Margem e distribuição')")
        pg.wait_for_selector("#ped-list .doc:has-text('PED-0001') .board svg")
        legp = pg.inner_text("#ped-list .doc:has-text('PED-0001') .legend").replace("\xa0", " ")
        centrop = num(pg.text_content("#ped-list .doc:has-text('PED-0001') .board svg text:nth-of-type(2)"))
        assert "Madeira com perda" in legp and abs(sum(valores_legenda("#ped-list .doc:has-text('PED-0001') .legend")) - centrop) < 0.05
        assert "R$ 1.000,00" in pg.inner_text("#ped-list .doc:has-text('PED-0001') .board").replace("\xa0", " ")   # valor final negociado do pedido
        # Backup por texto: copia o JSON, apaga tudo e restaura colando
        pg.click("#tab-est"); import json
        bk = pg.evaluate("() => JSON.stringify({app:'ljwa-calculadora',versao:6,estoque:JSON.parse(localStorage.getItem('ljwa-estoque-v2')),vendas:JSON.parse(localStorage.getItem('ljwa-vendas-v1'))})")
        pg.evaluate("() => { localStorage.clear(); }"); pg.reload(); pg.wait_for_timeout(300); pg.click("#tab-est")
        pg.fill("#bk-txt", bk); pg.click("#bk-paste"); pg.click("#bk-paste")
        assert "Backup restaurado" in pg.text_content("#bk-msg"), pg.text_content("#bk-msg")
        assert "Muiracatiara" in pg.inner_text("#items")
        assert not errs, errs
        b.close(); print("OK: fluxo completo passou")

if __name__ == "__main__":
    main()
