"""Gera prints reais do app clicando em cada aba/modal com um navegador de verdade (Playwright + Edge)."""
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "docs" / "screenshots" / "linkedin"
URL = "http://127.0.0.1:8008/?demo=1"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    srv = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8008"],
        cwd=str(BASE), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge")
            page = browser.new_page(viewport={"width": 1550, "height": 1100}, device_scale_factor=1.2)
            page.on("pageerror", lambda e: print("JS ERROR:", e))

            def fresh():
                page.goto(URL)
                page.wait_for_selector("#tab-local")
                page.wait_for_timeout(1200)

            def shot(name):
                page.wait_for_timeout(600)
                page.screenshot(path=str(OUT / name))
                print(" ->", name)

            def close_modals():
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)

            fresh()
            page.click("#tab-local"); shot("1_motores_local.png")
            page.click("#tab-cloud"); shot("1b_motores_nuvem.png")

            page.click("#btn-open-custom-providers-llm")
            page.click("#tab-modal-custom"); shot("1c_gerenciador_conexoes.png")
            page.click("#tab-modal-cloud")
            page.fill("#modal-key-groq", "gsk_live_94F2k9x" + "•" * 20)
            page.fill("#modal-key-openai", "sk-proj-7a8K9x" + "•" * 20)
            page.fill("#modal-key-gemini", "AIzaSyD-" + "•" * 24)
            shot("1c_chaves_api_nuvem.png"); close_modals()

            page.click("#tab-local")
            page.click("#hardware-badge"); shot("1d_diagnostico_hardware.png"); close_modals()

            page.click("#tab-dropzone-url")
            page.fill("#web-url-input", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            shot("2_transcricao_por_url.png")
            page.click("#tab-dropzone-mic"); shot("2b_gravacao_microfone.png")

            shot("3_player_e_minutagem.png")
            page.locator("#llm-actions-card").scroll_into_view_if_needed()
            shot("4_acoes_ia_resumo.png")
            page.evaluate("window.scrollTo(0,0)")

            page.click("#remote-btn"); page.wait_for_timeout(800)
            page.click("#tab-remote-lan"); shot("5_acesso_remoto_qrcode.png"); close_modals()

            shot("6_visao_geral.png")
            (OUT / "5_visao_geral.png").write_bytes((OUT / "6_visao_geral.png").read_bytes())
            browser.close()
    finally:
        srv.terminate()


if __name__ == "__main__":
    main()
