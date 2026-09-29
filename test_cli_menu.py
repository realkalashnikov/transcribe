"""
Testes unitários para o módulo app.core.cli_menu.
Verifica renderização, mapeamento de teclas e execução do menu interativo.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

import app.core.cli_menu as cli_menu


class TestCliMenu(unittest.TestCase):
    def test_menu_items_structure(self):
        """Verifica se todos os itens do menu possuem chaves e ações esperadas."""
        self.assertEqual(len(cli_menu.MENU_ITEMS), 4)
        actions = [item["action"] for item in cli_menu.MENU_ITEMS]
        self.assertEqual(actions, ["local", "public", "tunnel", "exit"])
        keys = [item["key"] for item in cli_menu.MENU_ITEMS]
        self.assertEqual(keys, ["1", "2", "3", "4"])

    def test_render_menu_all_indices(self):
        """Verifica se a renderização não lança exceções para nenhum índice."""
        for idx in range(len(cli_menu.MENU_ITEMS)):
            lines_rendered = cli_menu._render_menu(idx, first_render=True)
            self.assertGreater(lines_rendered, 0)

    def test_safe_str_fallback(self):
        """Verifica se o helper de codificação trata símbolos sem quebrar."""
        raw = "🗂 Transcribe Studio — Menu ◈ ✕ ↑ ↓ ✔"
        safe = cli_menu._safe_str(raw)
        self.assertIsInstance(safe, str)
        self.assertIn("Transcribe Studio", safe)

    @patch("sys.stdin.isatty", return_value=False)
    def test_non_interactive_returns_local(self, mock_isatty):
        """Quando o terminal não é interativo (ex: CI/pipes), deve retornar 'local'."""
        result = cli_menu.run_interactive_menu()
        self.assertEqual(result, "local")

    @patch("sys.stdin.isatty", return_value=True)
    @patch("app.core.cli_menu.get_key", side_effect=["enter"])
    def test_interactive_select_default(self, mock_get_key, mock_isatty):
        """Pressionar Enter na primeira opção deve retornar 'local'."""
        result = cli_menu.run_interactive_menu()
        self.assertEqual(result, "local")

    @patch("sys.stdin.isatty", return_value=True)
    @patch("app.core.cli_menu.get_key", side_effect=["down", "enter"])
    def test_interactive_navigate_down(self, mock_get_key, mock_isatty):
        """Navegar para baixo e pressionar Enter seleciona 'public'."""
        result = cli_menu.run_interactive_menu()
        self.assertEqual(result, "public")

    @patch("sys.stdin.isatty", return_value=True)
    @patch("app.core.cli_menu.get_key", side_effect=["up", "enter"])
    def test_interactive_navigate_up_wraparound(self, mock_get_key, mock_isatty):
        """Navegar para cima a partir do topo dá a volta para 'exit'."""
        result = cli_menu.run_interactive_menu()
        self.assertEqual(result, "exit")

    @patch("sys.stdin.isatty", return_value=True)
    @patch("app.core.cli_menu.get_key", side_effect=["3"])
    def test_direct_numeric_shortcut(self, mock_get_key, mock_isatty):
        """Pressionar o dígito '3' deve selecionar imediatamente 'tunnel'."""
        result = cli_menu.run_interactive_menu()
        self.assertEqual(result, "tunnel")

    @patch("sys.stdin.isatty", return_value=True)
    @patch("app.core.cli_menu.get_key", side_effect=["escape"])
    def test_escape_cancels_and_exits(self, mock_get_key, mock_isatty):
        """Pressionar Escape deve selecionar 'exit'."""
        result = cli_menu.run_interactive_menu()
        self.assertEqual(result, "exit")

    @patch("sys.stdin.isatty", return_value=True)
    @patch("app.core.cli_menu.get_key", side_effect=KeyboardInterrupt)
    def test_keyboard_interrupt_exits(self, mock_get_key, mock_isatty):
        """Ctrl+C deve finalizar selecionando 'exit' de forma limpa."""
        result = cli_menu.run_interactive_menu()
        self.assertEqual(result, "exit")




    def test_render_menu_narrow_terminal(self):
        """Verifica se o menu renderiza corretamente e adapta dicas em terminais estreitos."""
        with patch("shutil.get_terminal_size", return_value=MagicMock(columns=50, lines=20)):
            lines = cli_menu._render_menu(0, first_render=True)
            self.assertGreater(lines, 0)

    @patch("builtins.input", side_effect=["2"])
    def test_run_fallback_menu_selection(self, mock_input):
        """Verifica seleção válida no menu de fallback."""
        result = cli_menu._run_fallback_menu()
        self.assertEqual(result, "public")

    @patch("builtins.input", side_effect=EOFError)
    def test_run_fallback_menu_eof(self, mock_input):
        """EOF no fallback deve retornar 'exit' de forma segura."""
        result = cli_menu._run_fallback_menu()
        self.assertEqual(result, "exit")

    def test_get_key_windows_mappings(self):
        """Verifica o mapeamento de teclas na função do Windows."""
        with patch.dict("sys.modules", {"msvcrt": MagicMock()}):
            import msvcrt
            msvcrt.getwch.side_effect = ["\xe0", "H"]
            self.assertEqual(cli_menu._get_key_windows(), "up")

            msvcrt.getwch.side_effect = ["\xe0", "P"]
            self.assertEqual(cli_menu._get_key_windows(), "down")

            msvcrt.getwch.side_effect = ["\r"]
            self.assertEqual(cli_menu._get_key_windows(), "enter")

            msvcrt.getwch.side_effect = ["\x1b"]
            self.assertEqual(cli_menu._get_key_windows(), "escape")

            msvcrt.getwch.side_effect = ["2"]
            self.assertEqual(cli_menu._get_key_windows(), "2")

            msvcrt.getwch.side_effect = ["k"]
            self.assertEqual(cli_menu._get_key_windows(), "up")

            msvcrt.getwch.side_effect = ["\x03"]
            with self.assertRaises(KeyboardInterrupt):
                cli_menu._get_key_windows()

    def test_safe_av_open_fallback_behavior(self):
        """Verifica se o wrapper de av.open remove metadata_errors ao encontrar TypeError."""
        import av
        from app.engine.faster_whisper import _safe_av_open

        calls = []

        def mock_open(*args, **kwargs):
            calls.append(dict(kwargs))
            if "metadata_errors" in kwargs:
                raise TypeError("open() got an unexpected keyword argument 'metadata_errors'")
            return "success_container"

        with patch("app.engine.faster_whisper._orig_av_open", side_effect=mock_open):
            res = _safe_av_open("dummy.wav", mode="r", metadata_errors="ignore")
            self.assertEqual(res, "success_container")
            self.assertEqual(len(calls), 2)
            self.assertIn("metadata_errors", calls[0])
            self.assertNotIn("metadata_errors", calls[1])

        # Se o TypeError for por outro motivo, deve repassar
        def mock_open_other_error(*args, **kwargs):
            raise TypeError("unexpected error completely unrelated")

        with patch("app.engine.faster_whisper._orig_av_open", side_effect=mock_open_other_error):
            with self.assertRaises(TypeError):
                _safe_av_open("dummy.wav", mode="r")


    def test_get_key_posix_application_mode_and_escape(self):
        """Verifica captura de setas em modo de aplicação (SS3 / OA, OB) e timeout do Esc no POSIX."""
        mock_termios = MagicMock()
        mock_tty = MagicMock()
        with patch.dict("sys.modules", {"termios": mock_termios, "tty": mock_tty}):
            # Teste 1: Up arrow em application mode (\x1bOA)
            with patch("sys.stdin.fileno", return_value=0), \
                 patch("sys.stdin.read", side_effect=["\x1b", "O", "A"]), \
                 patch("select.select", side_effect=[([0], [], []), ([0], [], []), ([], [], [])]):
                self.assertEqual(cli_menu._get_key_posix(), "up")

            # Teste 2: Down arrow normal (\x1b[B)
            with patch("sys.stdin.fileno", return_value=0), \
                 patch("sys.stdin.read", side_effect=["\x1b", "[", "B"]), \
                 patch("select.select", side_effect=[([0], [], []), ([0], [], []), ([], [], [])]):
                self.assertEqual(cli_menu._get_key_posix(), "down")

            # Teste 3: Escape sozinho (timeout no select)
            with patch("sys.stdin.fileno", return_value=0), \
                 patch("sys.stdin.read", side_effect=["\x1b"]), \
                 patch("select.select", return_value=([], [], [])):
                self.assertEqual(cli_menu._get_key_posix(), "escape")


if __name__ == "__main__":
    unittest.main()
