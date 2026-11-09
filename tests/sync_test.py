"""Teste da sincronização, dos backups e do login contra um servidor de mentira que imita o Supabase.
Rodar:  python tests/sync_test.py
"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mock_supabase import start
from playwright.sync_api import sync_playwright

INDEX = (pathlib.Path(__file__).resolve().parent.parent / "index.html").as_uri()
CHROME = "/opt/pw-browsers/chromium" if pathlib.Path("/opt/pw-browsers/chromium").exists() else None


def abrir(browser, url, key="k" * 40):
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.add_init_script("localStorage.getItem('ljwa-supabase-v1') || localStorage.setItem('ljwa-supabase-v1', JSON.stringify({url: %r, key: %r}))" % (url, key))
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(INDEX)
    pg.wait_for_timeout(300)
    return pg, errs


def conta(pg):
    pg.click("#tab-cad"); pg.click("#cb-conta")


def cadastrar_maquina(pg, nome):
    pg.click("#tab-cad"); pg.click("#cb-maq")
    pg.fill("#mq-nome", nome); pg.fill("#mq-valor", "6000"); pg.fill("#mq-res", "1000"); pg.fill("#mq-vida", "10"); pg.fill("#mq-horas", "80"); pg.fill("#mq-manut", "240")
    pg.click("#mq-save")


def maquinas(pg):
    pg.click("#tab-cad"); pg.click("#cb-maq")
    return pg.inner_text("#mq-list")


def main():
    srv, st = start()
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)
        # --- aparelho A: cria conta com dados locais ---
        A, ea = abrir(b, srv.url)
        cadastrar_maquina(A, "Serra de bancada")
        conta(A)
        A.fill("#sy-email", "marceneiro@teste.com"); A.fill("#sy-senha", "123"); A.click("button:has-text('Criar conta')")
        A.wait_for_timeout(500)
        assert "6 caracteres" in A.inner_text("#sy-msg"), A.inner_text("#sy-msg")          # validação da senha
        assert A.input_value("#sy-email") == "marceneiro@teste.com"                              # o e-mail não some depois do erro
        A.fill("#sy-senha", "segredo123"); A.click("button:has-text('Criar conta')"); A.wait_for_timeout(800)
        assert "Conta pronta" in A.inner_text("#sy-msg"), A.inner_text("#sy-msg")
        assert len(st.dados) == 1 and list(st.dados.values())[0]["versao"] == 1
        assert "Serra de bancada" in str(list(st.dados.values())[0]["conteudo"])
        # --- aparelho B: entra e recebe os dados ---
        B, eb = abrir(b, srv.url)
        conta(B)
        B.fill("#sy-email", "marceneiro@teste.com"); B.fill("#sy-senha", "errada"); B.click("button:has-text('Entrar')"); B.wait_for_timeout(500)
        assert "incorretos" in B.inner_text("#sy-msg"), B.inner_text("#sy-msg")
        B.fill("#sy-senha", "segredo123"); B.click("button:has-text('Entrar')"); B.wait_for_timeout(800)
        assert "carregados" in B.inner_text("#sy-msg"), B.inner_text("#sy-msg")
        assert "Serra de bancada" in maquinas(B)
        # --- B altera; envio automático; A recebe ---
        cadastrar_maquina(B, "Plaina desengrossadeira"); B.wait_for_timeout(3500)
        assert list(st.dados.values())[0]["versao"] == 2, list(st.dados.values())[0]["versao"]
        conta(A); A.click("text=Sincronizar agora"); A.wait_for_timeout(1200)
        assert "Plaina desengrossadeira" in maquinas(A)
        # --- conflito: a nuvem muda por fora enquanto A altera ---
        with st.lock:
            row = list(st.dados.values())[0]; row["versao"] += 1
        cadastrar_maquina(A, "Lixadeira orbital"); A.wait_for_timeout(3500)
        conta(A)
        assert "Escolha qual versão manter" in A.inner_text("#sy-box"), A.inner_text("#sy-box")
        n0 = len(st.backups)
        A.click("text=Usar este aparelho"); A.wait_for_timeout(1200)
        assert len(st.backups) == n0 + 1, (n0, len(st.backups))                            # a versão antiga da nuvem virou backup
        assert "Lixadeira orbital" in str(list(st.dados.values())[0]["conteudo"])
        # --- backups: criar e restaurar ---
        A.click("text=Criar backup agora"); A.wait_for_timeout(800)
        assert "manual" in A.inner_text("#sy-bk"), A.inner_text("#sy-bk")
        cadastrar_maquina(A, "Tupia"); A.wait_for_timeout(3500)
        conta(A); A.wait_for_timeout(500)
        A.click("#sy-bk .drow:has-text('manual') button"); A.click("#sy-bk .drow:has-text('manual') button"); A.wait_for_timeout(1500)
        assert "Tupia" not in maquinas(A) and "Lixadeira orbital" in maquinas(A), maquinas(A)   # voltou ao estado do backup
        # --- sair ---
        conta(A); A.click("text=Sair da conta"); A.click("button:has-text('Confirmar: sair')")
        assert "Você saiu" in A.inner_text("#sy-msg") and A.is_visible("#sy-email")
        assert not ea and not eb, (ea, eb)
        b.close()
    print("OK: sincronização, conflito e backups passaram")


if __name__ == "__main__":
    main()
