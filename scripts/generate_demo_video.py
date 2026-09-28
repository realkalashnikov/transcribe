import os
import sys
import math
import wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import av

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_FILE = BASE_DIR / "meu_audio.wav"
OUTPUT_VIDEO = BASE_DIR / "demo_reels.mp4"
DOCS_VIDEO = BASE_DIR / "docs" / "demo_reels.mp4"

# Cores do Tema Moderno Glassmorphism
BG_TOP = (11, 15, 25)
BG_BOTTOM = (15, 23, 42)
CARD_BG = (22, 30, 49, 230)
CARD_BORDER = (45, 55, 78)
PRIMARY = (99, 102, 241)        # Indigo #6366f1
PRIMARY_LIGHT = (165, 180, 252)
ACCENT = (56, 189, 248)         # Sky Blue #38bdf8
SUCCESS = (16, 185, 129)        # Emerald #10b981
TEXT_WHITE = (248, 250, 252)
TEXT_MUTED = (148, 163, 184)
TEXT_DIM = (100, 116, 139)

def load_fonts():
    font_bold = r"C:\Windows\Fonts\segoeuib.ttf"
    font_reg = r"C:\Windows\Fonts\segoeui.ttf"
    if not os.path.exists(font_bold):
        font_bold = r"C:\Windows\Fonts\arialbd.ttf"
        font_reg = r"C:\Windows\Fonts\arial.ttf"

    return {
        "title": ImageFont.truetype(font_bold, 48),
        "subtitle": ImageFont.truetype(font_reg, 24),
        "card_title": ImageFont.truetype(font_bold, 30),
        "text": ImageFont.truetype(font_reg, 28),
        "text_bold": ImageFont.truetype(font_bold, 28),
        "transcript": ImageFont.truetype(font_bold, 38),
        "badge": ImageFont.truetype(font_bold, 20),
        "time": ImageFont.truetype(font_bold, 26),
        "small": ImageFont.truetype(font_reg, 20),
        "cta": ImageFont.truetype(font_bold, 26)
    }

def get_audio_data():
    with wave.open(str(AUDIO_FILE), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_data = wf.readframes(n_frames)

    dtype = np.int16 if sampwidth == 2 else np.uint8
    audio_arr = np.frombuffer(raw_data, dtype=dtype)
    if n_channels == 2:
        audio_mono = audio_arr.reshape(-1, 2).mean(axis=1).astype(np.int16)
    else:
        audio_mono = audio_arr

    duration = n_frames / float(framerate)
    return audio_mono, framerate, duration

# Timestamps das palavras faladas por Rafael (extraídas com Faster-Whisper base)
WORDS = [
    {"word": "Olá,", "start": 0.00, "end": 0.50},
    {"word": "meu", "start": 0.84, "end": 1.16},
    {"word": "nome", "start": 1.16, "end": 1.50},
    {"word": "é", "start": 1.50, "end": 1.82},
    {"word": "Rafael", "start": 1.82, "end": 2.40},
    {"word": "da", "start": 2.40, "end": 2.70},
    {"word": "Silva,", "start": 2.70, "end": 3.30},
    {"word": "eu", "start": 3.76, "end": 3.90},
    {"word": "tenho", "start": 3.90, "end": 4.15},
    {"word": "18", "start": 4.15, "end": 4.60},
    {"word": "anos", "start": 4.60, "end": 5.10},
    {"word": "e", "start": 5.10, "end": 5.34},
    {"word": "desenvolvi", "start": 5.34, "end": 6.10},
    {"word": "o", "start": 6.10, "end": 6.25},
    {"word": "transcribe.", "start": 6.25, "end": 7.15}
]

def create_background():
    w, h = 1080, 1920
    # Gradiente vertical suave
    base = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(base)
    for y in range(h):
        ratio = y / h
        r = int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio)
        g = int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio)
        b = int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Glow sutil no topo e centro
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([(-200, -200), (600, 600)], fill=(99, 102, 241, 35))
    glow_draw.ellipse([(600, 800), (1300, 1500)], fill=(56, 189, 248, 25))
    
    return Image.alpha_composite(base, glow).convert("RGB")

def render_frame(bg_image, fonts, t_video, audio_samples, sample_rate, total_audio_dur):
    # Dimensões 1080x1920
    img = bg_image.copy()
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Tempos
    INTRO_DUR = 0.8
    t_audio = max(0.0, min(total_audio_dur, t_video - INTRO_DUR))
    is_playing = (INTRO_DUR <= t_video < (INTRO_DUR + total_audio_dur))
    is_finished = (t_video >= INTRO_DUR + total_audio_dur)

    # ==========================
    # 1. HEADER DO APP
    # ==========================
    header_y = 120
    # Ícone do App (Mic dentro de círculo gradiente)
    draw.rounded_rectangle([70, header_y, 160, header_y + 90], radius=24, fill=(99, 102, 241, 180), outline=(129, 140, 248), width=2)
    # Mic shape
    draw.rounded_rectangle([103, header_y + 24, 127, header_y + 54], radius=10, fill=TEXT_WHITE)
    draw.arc([97, header_y + 35, 133, header_y + 65], start=0, end=180, fill=TEXT_WHITE, width=3)
    draw.line([(115, header_y + 65), (115, header_y + 74)], fill=TEXT_WHITE, width=3)

    # Título
    draw.text((180, header_y + 8), "Transcribe Studio", font=fonts["title"], fill=TEXT_WHITE)
    draw.text((180, header_y + 62), "Transcrição Rápida & Precisa • 100% Offline", font=fonts["subtitle"], fill=TEXT_MUTED)

    # Hardware Badge
    badge_x, badge_y = 70, header_y + 120
    draw.rounded_rectangle([badge_x, badge_y, badge_x + 360, badge_y + 44], radius=22, fill=(16, 185, 129, 30), outline=(16, 185, 129, 120), width=1)
    draw.ellipse([badge_x + 16, badge_y + 16, badge_x + 28, badge_y + 28], fill=SUCCESS)
    draw.text((badge_x + 40, badge_y + 10), "Modo CPU (Faster-Whisper int8)", font=fonts["badge"], fill=SUCCESS)

    # ==========================
    # 2. CARD DO ARQUIVO
    # ==========================
    card1_y = 320
    draw.rounded_rectangle([70, card1_y, 1010, card1_y + 160], radius=28, fill=CARD_BG, outline=CARD_BORDER, width=2)
    # Ícone de áudio
    draw.rounded_rectangle([105, card1_y + 35, 185, card1_y + 115], radius=18, fill=(99, 102, 241, 40), outline=(99, 102, 241, 80), width=1)
    # Onda de som no ícone
    draw.line([(130, card1_y + 65), (130, card1_y + 85)], fill=PRIMARY_LIGHT, width=3)
    draw.line([(145, card1_y + 50), (145, card1_y + 100)], fill=PRIMARY_LIGHT, width=3)
    draw.line([(160, card1_y + 60), (160, card1_y + 90)], fill=PRIMARY_LIGHT, width=3)

    draw.text((210, card1_y + 35), "meu_audio.wav", font=fonts["card_title"], fill=TEXT_WHITE)
    draw.text((210, card1_y + 85), "7.6s  •  Português (PT-BR)  •  faster-whisper", font=fonts["subtitle"], fill=TEXT_MUTED)

    # Status Pill
    status_text = "Concluído em 0.6s" if (t_video >= 0.5) else "Transcrevendo..."
    status_color = SUCCESS if (t_video >= 0.5) else ACCENT
    draw.rounded_rectangle([770, card1_y + 38, 975, card1_y + 80], radius=18, fill=(status_color[0], status_color[1], status_color[2], 30), outline=(status_color[0], status_color[1], status_color[2], 120), width=1)
    draw.text((795, card1_y + 46), status_text, font=fonts["badge"], fill=status_color)

    # ==========================
    # 3. PLAYER DE ÁUDIO & ESPECTRO
    # ==========================
    player_y = 515
    draw.rounded_rectangle([70, player_y, 1010, player_y + 360], radius=28, fill=CARD_BG, outline=CARD_BORDER, width=2)

    # Play/Pause Botão
    btn_cx, btn_cy, btn_r = 150, player_y + 110, 48
    draw.ellipse([btn_cx - btn_r, btn_cy - btn_r, btn_cx + btn_r, btn_cy + btn_r], fill=PRIMARY, outline=(129, 140, 248), width=2)
    if is_playing:
        # Pause bars
        draw.rounded_rectangle([btn_cx - 14, btn_cy - 18, btn_cx - 4, btn_cy + 18], radius=3, fill=TEXT_WHITE)
        draw.rounded_rectangle([btn_cx + 4, btn_cy - 18, btn_cx + 14, btn_cy + 18], radius=3, fill=TEXT_WHITE)
    else:
        # Play triangle
        draw.polygon([(btn_cx - 8, btn_cy - 18), (btn_cx - 8, btn_cy + 18), (btn_cx + 16, btn_cy)], fill=TEXT_WHITE)

    # Timer display
    cur_mins, cur_secs = divmod(int(t_audio), 60)
    tot_mins, tot_secs = divmod(int(total_audio_dur), 60)
    time_str = f"{cur_mins:02d}:{cur_secs:02d} / {tot_mins:02d}:{tot_secs:02d}"
    draw.text((230, player_y + 95), time_str, font=fonts["time"], fill=TEXT_WHITE)
    draw.text((230, player_y + 130), "Áudio Original Integrado com Minutagem", font=fonts["small"], fill=TEXT_MUTED)

    # Visualizador de Espectro / Equalizador (36 barras animadas)
    eq_x_start = 110
    eq_width = 830
    eq_bars = 36
    bar_w = 14
    bar_gap = (eq_width - (eq_bars * bar_w)) // (eq_bars - 1)
    eq_base_y = player_y + 245

    # Calcula volume no instante t_audio
    sample_idx = int(t_audio * sample_rate)
    window_samples = audio_samples[max(0, sample_idx - 1000):min(len(audio_samples), sample_idx + 1000)]
    local_volume = np.max(np.abs(window_samples)) / 32768.0 if len(window_samples) > 0 else 0.0

    for i in range(eq_bars):
        bx = eq_x_start + i * (bar_w + bar_gap)
        if is_playing and local_volume > 0.04:
            # Variação senoidal dinâmica somada ao volume
            phase = i * 0.4 + t_audio * 12.0
            height_factor = math.sin(phase) * 0.4 + 0.6
            bar_h = int(12 + (height_factor * local_volume * 90))
        else:
            bar_h = 10

        bar_h = max(8, min(80, bar_h))
        # Cor das barras (gradiente de ciano para índigo)
        prog_bar = i / eq_bars
        col_r = int(56 * (1 - prog_bar) + 99 * prog_bar)
        col_g = int(189 * (1 - prog_bar) + 102 * prog_bar)
        col_b = int(248 * (1 - prog_bar) + 241 * prog_bar)

        draw.rounded_rectangle([bx, eq_base_y - bar_h, bx + bar_w, eq_base_y], radius=4, fill=(col_r, col_g, col_b))

    # Barra de Progresso do Scrubber
    scrub_y = player_y + 295
    scrub_w = 830
    draw.rounded_rectangle([110, scrub_y, 110 + scrub_w, scrub_y + 12], radius=6, fill=(30, 41, 59))
    prog_pct = t_audio / total_audio_dur if total_audio_dur > 0 else 0.0
    fill_w = int(scrub_w * min(1.0, max(0.0, prog_pct)))
    if fill_w > 0:
        draw.rounded_rectangle([110, scrub_y, 110 + fill_w, scrub_y + 12], radius=6, fill=ACCENT)
        # Handle do cursor
        cursor_x = 110 + fill_w
        draw.ellipse([cursor_x - 10, scrub_y - 4, cursor_x + 10, scrub_y + 16], fill=TEXT_WHITE, outline=ACCENT, width=3)

    # ==========================
    # 4. CARD DE TRANSCRIÇÃO (O DESTAQUE PRINCIPAL!)
    # ==========================
    trans_y = 910
    draw.rounded_rectangle([70, trans_y, 1010, trans_y + 620], radius=28, fill=CARD_BG, outline=CARD_BORDER, width=2)

    # Cabeçalho do Card de Transcrição
    draw.text((115, trans_y + 35), "Resultado da Transcrição", font=fonts["card_title"], fill=TEXT_WHITE)

    # Botões de Exportação no canto
    exp_badges = ["TXT", "SRT", "VTT", "JSON"]
    exp_x = 550
    for eb in exp_badges:
        draw.rounded_rectangle([exp_x, trans_y + 35, exp_x + 95, trans_y + 75], radius=10, fill=(30, 41, 59), outline=CARD_BORDER, width=1)
        draw.text((exp_x + 22, trans_y + 44), eb, font=fonts["badge"], fill=PRIMARY_LIGHT)
        exp_x += 105

    # Bloco de Minutagem Interativa
    block_y = trans_y + 120
    draw.rounded_rectangle([110, block_y, 970, trans_y + 575], radius=20, fill=(15, 23, 42, 200), outline=(99, 102, 241, 70), width=1)

    # Timestamp badge clicável
    time_badge_y = block_y + 24
    draw.rounded_rectangle([140, time_badge_y, 340, time_badge_y + 44], radius=12, fill=(56, 189, 248, 25), outline=(56, 189, 248, 120), width=1)
    draw.text((165, time_badge_y + 8), "00:00 - 00:07", font=fonts["badge"], fill=ACCENT)

    # Renderiza as palavras com Efeito Karaokê em tempo real!
    # Linha 1: "Olá, meu nome é Rafael da Silva,"
    # Linha 2: "eu tenho 18 anos e desenvolvi"
    # Linha 3: "o transcribe."
    line1 = WORDS[0:7]
    line2 = WORDS[7:13]
    line3 = WORDS[13:15]

    lines = [
        (line1, block_y + 90),
        (line2, block_y + 195),
        (line3, block_y + 300)
    ]

    for word_list, line_y in lines:
        cur_x = 140
        for w_data in word_list:
            word = w_data["word"]
            w_start = w_data["start"]
            w_end = w_data["end"]

            # Mede largura da palavra
            bbox = fonts["transcript"].getbbox(word)
            word_w = bbox[2] - bbox[0]
            word_h = bbox[3] - bbox[1]

            is_word_active = (w_start <= t_audio <= w_end + 0.15)
            is_word_past = (t_audio > w_end + 0.15)

            if is_word_active:
                # Palavra sendo falada no segundo exato: Pill azul brilhante com texto branco
                pad_x, pad_y = 10, 8
                draw.rounded_rectangle([cur_x - pad_x, line_y - pad_y, cur_x + word_w + pad_x, line_y + word_h + pad_y + 6], radius=10, fill=(56, 189, 248, 70), outline=ACCENT, width=2)
                draw.text((cur_x, line_y), word, font=fonts["transcript"], fill=TEXT_WHITE)
            elif is_word_past:
                # Palavra já falada: branco nítido
                draw.text((cur_x, line_y), word, font=fonts["transcript"], fill=(226, 232, 240))
            else:
                # Palavra futura: acinzentada suave
                draw.text((cur_x, line_y), word, font=fonts["transcript"], fill=(100, 116, 139))

            cur_x += word_w + 18

    # ==========================
    # 5. STRIP DE ESTATÍSTICAS
    # ==========================
    stats_y = trans_y + 480
    draw.line([(140, stats_y), (940, stats_y)], fill=(30, 41, 59), width=1)
    stat_items = [
        ("DURAÇÃO", "7.6s"),
        ("PALAVRAS", "15"),
        ("CARACTERES", "73"),
        ("PRECISÃO", "100%")
    ]
    sx = 150
    for label, val in stat_items:
        draw.text((sx, stats_y + 15), label, font=fonts["small"], fill=TEXT_DIM)
        draw.text((sx, stats_y + 42), val, font=fonts["badge"], fill=PRIMARY_LIGHT)
        sx += 205

    # ==========================
    # 6. BANNER / CTA INFERIOR
    # ==========================
    cta_y = 1560
    draw.rounded_rectangle([70, cta_y, 1010, cta_y + 240], radius=28, fill=(15, 23, 42, 240), outline=(99, 102, 241, 100), width=2)

    # Estrela do GitHub
    draw.text((115, cta_y + 35), "⭐️ Projeto 100% Aberto e Open Source", font=fonts["card_title"], fill=TEXT_WHITE)
    draw.text((115, cta_y + 85), "Desenvolvido por Rafael da Silva • 18 anos", font=fonts["text_bold"], fill=ACCENT)
    draw.text((115, cta_y + 130), "Python  •  FastAPI  •  Faster-Whisper  •  Whisper.cpp", font=fonts["subtitle"], fill=TEXT_MUTED)

    # Link Pill
    draw.rounded_rectangle([115, cta_y + 175, 780, cta_y + 220], radius=12, fill=(99, 102, 241, 35), outline=(99, 102, 241, 120), width=1)
    draw.text((135, cta_y + 184), "github.com/realkalashnikov/transcribe", font=fonts["cta"], fill=PRIMARY_LIGHT)

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

def main():
    print("=" * 60)
    print("GERADOR DE VÍDEO DEMO (INSTAGRAM REELS / STORIES / TIKTOK)")
    print("=" * 60)

    if not AUDIO_FILE.exists():
        print(f"Erro: Arquivo {AUDIO_FILE} não encontrado!")
        sys.exit(1)

    print("[1/4] Carregando áudio e calculando amplitudes...")
    audio_samples, sample_rate, total_audio_dur = get_audio_data()
    print(f" -> Duração detectada: {total_audio_dur:.2f}s | Taxa de amostragem: {sample_rate}Hz")

    # Configuração de Tempo do Vídeo
    INTRO_DUR = 0.8
    OUTRO_DUR = 1.6
    TOTAL_VIDEO_DUR = INTRO_DUR + total_audio_dur + OUTRO_DUR
    FPS = 30
    TOTAL_FRAMES = int(TOTAL_VIDEO_DUR * FPS)

    print(f"[2/4] Preparando container de vídeo (1080x1920 @ {FPS}fps, {TOTAL_FRAMES} frames)...")
    fonts = load_fonts()
    bg_image = create_background()

    # Prepara container PyAV
    container = av.open(str(OUTPUT_VIDEO), mode="w")

    # Stream de Vídeo H.264
    v_stream = container.add_stream("libx264", rate=FPS)
    v_stream.width = 1080
    v_stream.height = 1920
    v_stream.pix_fmt = "yuv420p"
    v_stream.options = {"crf": "20", "preset": "fast"}

    # Stream de Áudio AAC 48kHz Stereo
    a_stream = container.add_stream("aac", rate=sample_rate)
    a_stream.layout = "stereo"

    # Prepara áudio completo com padding de silêncio na intro e outro
    intro_samples = int(INTRO_DUR * sample_rate)
    outro_samples = int(OUTRO_DUR * sample_rate)
    full_audio = np.concatenate([
        np.zeros(intro_samples, dtype=np.int16),
        audio_samples,
        np.zeros(outro_samples, dtype=np.int16)
    ])
    stereo_audio = np.stack([full_audio, full_audio], axis=0) # shape (2, N)

    print("[3/4] Renderizando frames com animação de áudio e karaokê...")
    frame_pct_step = TOTAL_FRAMES // 10

    for f_idx in range(TOTAL_FRAMES):
        t_video = f_idx / float(FPS)
        frame_img = render_frame(bg_image, fonts, t_video, audio_samples, sample_rate, total_audio_dur)

        # Converte para frame de vídeo
        v_frame = av.VideoFrame.from_image(frame_img)
        v_frame.pts = f_idx
        for packet in v_stream.encode(v_frame):
            container.mux(packet)

        if f_idx % frame_pct_step == 0 or f_idx == TOTAL_FRAMES - 1:
            pct = int((f_idx + 1) / TOTAL_FRAMES * 100)
            print(f" -> Progresso: {pct}% ({f_idx + 1}/{TOTAL_FRAMES} frames)")

    # Encerra stream de vídeo
    for packet in v_stream.encode():
        container.mux(packet)

    print("[4/4] Muxing da trilha sonora sincronizada (AAC Stereo)...")
    chunk_size = 1024
    total_audio_len = stereo_audio.shape[1]
    audio_pts = 0

    for i in range(0, total_audio_len, chunk_size):
        chunk = stereo_audio[:, i:i+chunk_size]
        if chunk.shape[1] < chunk_size:
            pad = np.zeros((2, chunk_size - chunk.shape[1]), dtype=np.int16)
            chunk = np.hstack([chunk, pad])
        a_frame = av.AudioFrame.from_ndarray(chunk, format="s16p", layout="stereo")
        a_frame.rate = sample_rate
        a_frame.pts = audio_pts
        audio_pts += chunk_size
        for packet in a_stream.encode(a_frame):
            container.mux(packet)

    for packet in a_stream.encode():
        container.mux(packet)

    container.close()

    # Copia para pasta docs
    DOCS_VIDEO.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(OUTPUT_VIDEO, DOCS_VIDEO)

    print("\n" + "=" * 60)
    print(f"[SUCESSO] Vídeo gerado com sucesso!")
    print(f" -> Arquivo pronto para postar: {OUTPUT_VIDEO}")
    print(f" -> Cópia salva em docs: {DOCS_VIDEO}")
    print(f" -> Resolução: 1080x1920 (Formato 9:16 - Reels / Stories / TikTok)")
    print(f" -> Duração total: {TOTAL_VIDEO_DUR:.1f} segundos")
    print("=" * 60)

if __name__ == "__main__":
    main()
