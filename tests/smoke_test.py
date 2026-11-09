"""Teste de fumaça ponta a ponta: estoque -> calculadora -> cotação -> pedido -> baixa.
Rodar:  pip install playwright && playwright install chromium && python tests/smoke_test.py
"""
import pathlib
from playwright.sync_api import sync_playwright

INDEX = (pathlib.Path(__file__).resolve().parent.parent / "index.html").as_uri()

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
        pg.click("text=Registrar pagamento"); pg.click("#rec-list .panel .primary")
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
