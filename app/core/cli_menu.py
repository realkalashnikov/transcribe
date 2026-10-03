"""
Menu Interativo de Terminal (CLI Moderna) para Transcribe Studio.
Navegação por setas (↑/↓), atalhos numéricos (1-4) e cores ANSI nativas.
Inspirado na interface moderna com fundo azul ativo e ícones diamante.
"""

import sys
import os
import shutil

MENU_ITEMS = [
    {
        "key": "1",
        "action": "local",
        "label": "1. Iniciar Local com Navegador (Padrão)",
        "icon": "◈",
        "color": "\033[92m",  # Bright green
    },
    {
        "key": "2",
        "action": "local_no_browser",
        "label": "2. Iniciar Local sem abrir Navegador",
        "icon": "◈",
        "color": "\033[92m",  # Bright green
    },
    {
        "key": "3",
        "action": "background",
        "label": "3. Executar em Segundo Plano (Bandeja / Tray no relógio)",
        "icon": "◈",
        "color": "\033[95m",  # Bright magenta
    },
    {
        "key": "4",
        "action": "public",
        "label": "4. Instância Pública / Amigos (Rede ou VPS)",
        "icon": "◈",
        "color": "\033[92m",  # Bright green
    },
    {
        "key": "5",
        "action": "tunnel",
        "label": "5. Túnel Cloudflare (Acesso remoto / Celular)",
        "icon": "◈",
        "color": "\033[96m",  # Bright cyan
    },
    {
        "key": "6",
        "action": "open_browser",
        "label": "6. Abrir Transcribe no Navegador",
        "icon": "◈",
        "color": "\033[94m",  # Bright blue
    },
    {
        "key": "7",
        "action": "stop_background",
        "label": "7. Parar Servidor em Segundo Plano",
        "icon": "◈",
        "color": "\033[93m",  # Bright yellow
    },
    {
        "key": "8",
        "action": "exit",
        "label": "8. Sair",
        "icon": "✕",
        "color": "\033[91m",  # Bright red
    },
]


def _init_terminal():
    """Habilita sequências de escape ANSI e encoding UTF-8 no console."""
    if sys.platform == "win32":
        try:
            os.system("")  # Ativa VT100 virtual terminal no Windows 10/11 CMD
        except Exception:
            pass

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Inicializa console na importação
_init_terminal()


def _safe_str(text: str) -> str:
    """Garante que a string seja compatível com a codificação do terminal."""
    encoding = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
    try:
        text.encode(encoding)
        return text
    except (UnicodeEncodeError, LookupError):
        cleaned = (
            text.replace("🗂", "[*]")
            .replace("◈", ">")
            .replace("✕", "x")
            .replace("↑", "^")
            .replace("↓", "v")
            .replace("✔", "[OK]")
            .replace("—", "-")
        )
        try:
            return cleaned.encode(encoding, errors="replace").decode(encoding)
        except Exception:
            return cleaned


def _safe_write(text: str):
    """Escreve com segurança no stdout tratando possíveis falhas de codificação."""
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        sys.stdout.write(_safe_str(text))


def _get_key_windows():
    """Captura teclas no Windows usando msvcrt nativo."""
    import msvcrt

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        ch2 = msvcrt.getwch()
        if ch2 == "H":
            return "up"
        elif ch2 == "P":
            return "down"
        elif ch2 == "K":
            return "left"
        elif ch2 == "M":
            return "right"
        return None
    elif ch in ("\r", "\n"):
        return "enter"
    elif ch == "\x03":  # Ctrl+C
        raise KeyboardInterrupt()
    elif ch == "\x1b":  # Escape
        return "escape"
    elif ch in ("1", "2", "3", "4", "5", "6", "7", "8"):
        return ch
    elif ch in ("w", "W", "k", "K"):
        return "up"
    elif ch in ("s", "S", "j", "J"):
        return "down"
    elif ch in ("q", "Q"):
        return "escape"
    return None


def _get_key_posix():
    """Captura teclas no Linux/macOS usando termios e modo raw."""
    import tty
    import termios
    import select

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            r, _, _ = select.select([sys.stdin], [], [], 0.05)
            if r:
                seq = [sys.stdin.read(1)]
                # Drena bytes restantes da sequência de escape de forma não-bloqueante
                while True:
                    r2, _, _ = select.select([sys.stdin], [], [], 0.01)
                    if r2:
                        seq.append(sys.stdin.read(1))
                    else:
                        break
                code = "".join(seq)
                if code in ("[A", "OA", "[1;5A", "[1;2A"):
                    return "up"
                elif code in ("[B", "OB", "[1;5B", "[1;2B"):
                    return "down"
                elif code in ("[C", "OC"):
                    return "right"
                elif code in ("[D", "OD"):
                    return "left"
                return None  # Sequência desconhecida (F-keys, PageUp, etc.), ignora com segurança
            return "escape"
        elif ch in ("\r", "\n"):
            return "enter"
        elif ch == "\x03":
            raise KeyboardInterrupt()
        elif ch in ("1", "2", "3", "4", "5", "6", "7", "8"):
            return ch
        elif ch in ("w", "W", "k", "K"):
            return "up"
        elif ch in ("s", "S", "j", "J"):
            return "down"
        elif ch in ("q", "Q"):
            return "escape"
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def get_key():
    """Lê tecla de forma multiplataforma."""
    if sys.platform == "win32":
        return _get_key_windows()
    else:
        return _get_key_posix()


def _render_menu(selected_idx: int, first_render: bool = False) -> int:
    """Renderiza a interface do menu no console e retorna a quantidade de linhas."""
    term_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    max_label_len = max(len(f" {item['icon']} {item['label']}") for item in MENU_ITEMS)
    content_width = min(max_label_len + 2, max(20, term_width - 2))

    lines = []
    # Cabeçalho ciano com sublinhado
    lines.append("\033[1;4;36m🗂 Transcribe Studio — Menu Principal\033[0m")
    lines.append("")

    for idx, item in enumerate(MENU_ITEMS):
        is_selected = idx == selected_idx
        icon = item["icon"]
        label = item["label"]

        if is_selected:
            # Barra azul ativa com texto destacado
            if item["action"] == "exit":
                text_color = "\033[44;1;91m"
            elif item["action"] == "tunnel":
                text_color = "\033[44;1;96m"
            elif item["action"] == "background":
                text_color = "\033[44;1;95m"
            elif item["action"] == "open_browser":
                text_color = "\033[44;1;94m"
            elif item["action"] == "stop_background":
                text_color = "\033[44;1;93m"
            else:
                text_color = "\033[44;1;92m"
            raw_text = f" {icon} {label}"
            padded_text = f"{raw_text:<{content_width}}"
            lines.append(f"{text_color}{padded_text}\033[0m")
        else:
            lines.append(f" {item['color']}{icon} {label}\033[0m")

    lines.append("")
    # Dica de atalhos e navegação adaptável ao tamanho do terminal para não quebrar linha
    hint = "(Use as setas ↑/↓ para navegar, Enter para confirmar ou 1-8 para atalho)"
    if term_width < len(hint) + 2:
        hint = "(↑/↓ Navegar  •  Enter Confirmar  •  1-8 Atalho  •  Esc Sair)"
    if term_width < len(hint) + 2:
        hint = "(↑/↓: Mover | Enter: OK | 1-8: Atalho)"
    lines.append(f"\033[90m{hint}\033[0m")

    if not first_render:
        _safe_write(f"\033[{len(lines)}F")

    for line in lines:
        _safe_write(f"\033[2K{line}\n")
    sys.stdout.flush()

    return len(lines)


def _run_fallback_menu():
    """Fallback limpo em caso de terminal não-TTY ou incompatibilidade de raw mode."""
    print("\n--- Transcribe Studio — Menu Principal ---")
    for item in MENU_ITEMS:
        print(f"  [{item['key']}] {item['label']}")
    print()
    try:
        choice = input("Escolha uma opção [1-8] (Padrão: 1): ").strip()
    except (KeyboardInterrupt, EOFError):
        return "exit"

    for item in MENU_ITEMS:
        if choice == item["key"]:
            return item["action"]
    return "local"


def run_interactive_menu():
    """
    Exibe o menu interativo no terminal.
    Retorna uma das strings: 'local', 'local_no_browser', 'background', 'public', 'tunnel', 'open_browser', 'stop_background', 'exit'.
    """
    _init_terminal()

    if not sys.stdin.isatty():
        return "local"

    exit_idx = next(
        (i for i, it in enumerate(MENU_ITEMS) if it.get("action") == "exit"),
        len(MENU_ITEMS) - 1,
    )
    selected_idx = 0

    try:
        # Esconde cursor do terminal
        _safe_write("\033[?25l")
        sys.stdout.flush()

        # Primeira renderização
        _render_menu(selected_idx, first_render=True)

        while True:
            try:
                key = get_key()
            except KeyboardInterrupt:
                selected_idx = exit_idx
                break

            if key == "up":
                selected_idx = (selected_idx - 1) % len(MENU_ITEMS)
                _render_menu(selected_idx)
            elif key == "down":
                selected_idx = (selected_idx + 1) % len(MENU_ITEMS)
                _render_menu(selected_idx)
            elif key in ("1", "2", "3", "4", "5", "6", "7", "8"):
                selected_idx = int(key) - 1
                _render_menu(selected_idx)
                break
            elif key == "enter":
                break
            elif key == "escape":
                selected_idx = exit_idx
                break

    except Exception:
        # Fallback de segurança se falhar leitura crua de teclas
        return _run_fallback_menu()
    finally:
        # Restaura cursor do terminal e reseta cores
        _safe_write("\033[?25h\033[0m")
        sys.stdout.flush()

    chosen_item = MENU_ITEMS[selected_idx]
    chosen_action = chosen_item["action"]

    # Mensagem de confirmação visual
    if chosen_action == "exit":
        _safe_write("\n\033[91m✕ Operação cancelada pelo usuário.\033[0m\n\n")
    elif chosen_action == "local_no_browser":
        _safe_write("\n\033[92m✔ Modo Local (sem abrir navegador) selecionado.\033[0m\n\n")
    elif chosen_action == "background":
        _safe_write("\n\033[95m✔ Executando em segundo plano (veja o ícone na bandeja do relógio).\033[0m\n\n")
    elif chosen_action == "public":
        _safe_write("\n\033[92m✔ Modo Instância Pública / Amigos selecionado.\033[0m\n\n")
    elif chosen_action == "tunnel":
        _safe_write("\n\033[96m✔ Modo Túnel Cloudflare selecionado.\033[0m\n\n")
    elif chosen_action == "open_browser":
        _safe_write("\n\033[94m✔ Abrindo Transcribe Studio no navegador...\033[0m\n\n")
    elif chosen_action == "stop_background":
        _safe_write("\n\033[93m✔ Parando servidor em segundo plano...\033[0m\n\n")
    else:
        _safe_write("\n\033[92m✔ Modo Local com Navegador selecionado.\033[0m\n\n")
    sys.stdout.flush()

    return chosen_action
