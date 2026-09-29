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


if __name__ == "__main__":
    unittest.main()
