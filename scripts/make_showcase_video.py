import subprocess
from pathlib import Path
import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "docs" / "screenshots"

def make_video():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    output_mp4 = SCREENSHOTS_DIR / "showcase_demo.mp4"
    
    # Imagens do showcase ordenadas estrategicamente
    candidate_images = [
        SCREENSHOTS_DIR / "preview.png",
        SCREENSHOTS_DIR / "linkedin" / "1_motores_local.png",
        SCREENSHOTS_DIR / "linkedin" / "1b_motores_nuvem.png",
        SCREENSHOTS_DIR / "linkedin" / "1c_gerenciador_conexoes.png",
        SCREENSHOTS_DIR / "url_ingestion.png",
        SCREENSHOTS_DIR / "transcription_view.png",
        SCREENSHOTS_DIR / "linkedin" / "4_acoes_ia_resumo.png",
        SCREENSHOTS_DIR / "remote_modal.png",
        SCREENSHOTS_DIR / "cli_menu.png"
    ]
    
    # Filtra as imagens que existem
    images = [img for img in candidate_images if img.exists()]
    if not images:
        print("Nenhuma imagem encontrada para compor o vídeo.")
        return

    # Cria arquivo de lista para concat no FFmpeg
    concat_file = BASE_DIR / "scripts" / "_concat_list.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for img in images:
            f.write(f"file '{img.as_posix()}'\n")
            f.write("duration 3.0\n")
        # repete a última para o player não cortar o frame final
        f.write(f"file '{images[-1].as_posix()}'\n")
        f.write("duration 1.5\n")
        
    print(f"Gerando vídeo demo MP4 a 60 FPS em {output_mp4} ({len(images)} slides)...")
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-vf", "scale=1600:1200:force_original_aspect_ratio=decrease,pad=1600:1200:(ow-iw)/2:(oh-ih)/2:color=black,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-r", "60",
        "-pix_fmt", "yuv420p",
        str(output_mp4)
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f" -> showcase_demo.mp4 a 60 FPS gerado com sucesso! ({output_mp4.stat().st_size // 1024} KB)")
    else:
        print("Erro ao gerar vídeo:", res.stderr)
        
    if concat_file.exists():
        concat_file.unlink()

if __name__ == "__main__":
    make_video()
