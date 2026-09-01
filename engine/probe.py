#!/usr/bin/env python3
"""Mede o que da para medir num video sem opinar: metadados, cortes e energia de audio.

Uso:
    python probe.py <video.mp4> [<video.mp4> ...] --out <dir>

Escreve um JSON por video em <dir>/<nome>.probe.json.
Nada aqui usa LLM. O julgamento vem depois, em cima destes numeros.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import av

# Esta maquina tem ffmpeg mas nao tem ffprobe, por isso os metadados saem do
# PyAV (libav embutido) e so os filtros passam pelo binario do ffmpeg.
FFMPEG = "ffmpeg"

# Limiar de mudanca de cena. 0.25 pega corte seco e transicao rapida sem
# disparar em movimento de camara.
SCENE_THRESHOLD = 0.25


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def metadata(video: Path) -> dict:
    with av.open(str(video)) as container:
        vs = container.streams.video[0]
        tem_audio = len(container.streams.audio) > 0
        width, height = vs.codec_context.width, vs.codec_context.height
        fps = float(vs.average_rate) if vs.average_rate else 0.0
        duracao = container.duration / av.time_base if container.duration else 0.0
        bitrate = container.bit_rate

    return {
        "duracao_s": round(duracao, 3),
        "largura": width,
        "altura": height,
        "aspect": f"{width}:{height}",
        "vertical": height > width,
        "fps": round(fps, 3),
        "tem_audio": tem_audio,
        "bitrate_kbps": round(bitrate / 1000) if bitrate else None,
    }


def area_ativa(video: Path) -> str | None:
    """Descobre a area util da imagem, ignorando barras pretas de letterbox.

    Sem isto, um video 16:9 dentro de um canvas 9:16 da falso negativo: as barras
    pretas ocupam metade do frame e nunca mudam, por isso afogam a metrica de cena
    e o detector devolve zero cortes num video que tem dezenas.
    """
    out = run([
        FFMPEG, "-i", str(video), "-t", "30",
        "-vf", "cropdetect=limit=24:round=2:reset=0", "-f", "null", "-",
    ])
    achados = re.findall(r"crop=(\d+:\d+:\d+:\d+)", out.stderr)
    if not achados:
        return None
    # O ultimo valor e o acumulado sobre a amostra inteira.
    crop = achados[-1]
    w, h, _, _ = (int(v) for v in crop.split(":"))
    with av.open(str(video)) as c:
        vs = c.streams.video[0]
        largura, altura = vs.codec_context.width, vs.codec_context.height
    # So vale a pena cortar se as barras comem mais de 5% do frame.
    if w * h < largura * altura * 0.95:
        return crop
    return None


def cortes(video: Path) -> tuple:
    """Deteta mudancas de cena via ffmpeg e devolve os timestamps e o crop usado."""
    crop = area_ativa(video)
    filtro = f"crop={crop}," if crop else ""
    out = run([
        FFMPEG, "-i", str(video),
        "-filter:v", f"{filtro}select='gt(scene,{SCENE_THRESHOLD})',showinfo",
        "-f", "null", "-",
    ])
    marcas = sorted(float(m) for m in re.findall(r"pts_time:([0-9.]+)", out.stderr))
    return marcas, crop


def estatistica_cortes(marcas: list, duracao: float) -> dict:
    # Fronteiras de todos os planos: inicio, cada corte, fim.
    fronteiras = [0.0] + marcas + [duracao]
    planos = [round(b - a, 3) for a, b in zip(fronteiras, fronteiras[1:]) if b > a]
    if not planos:
        return {"n_cortes": 0, "planos": []}

    ordenados = sorted(planos)
    meio = len(ordenados) // 2
    mediana = ordenados[meio] if len(ordenados) % 2 else (ordenados[meio - 1] + ordenados[meio]) / 2

    return {
        "n_cortes": len(marcas),
        "cortes_por_minuto": round(len(marcas) / (duracao / 60), 2) if duracao else 0,
        "plano_medio_s": round(sum(planos) / len(planos), 3),
        "plano_mediano_s": round(mediana, 3),
        "plano_mais_curto_s": min(planos),
        "plano_mais_longo_s": max(planos),
        "planos_abaixo_1s_pct": round(100 * sum(1 for p in planos if p < 1.0) / len(planos), 1),
        "planos": planos,
        "timestamps": [round(m, 3) for m in marcas],
    }


def audio(video: Path) -> dict:
    """Loudness integrado e pico. Serve para saber o alvo de mix das refs."""
    out = run([
        FFMPEG, "-i", str(video), "-af", "loudnorm=print_format=json",
        "-f", "null", "-",
    ])
    bloco = re.search(r"\{[^{]*\"input_i\"[^}]*\}", out.stderr, re.S)
    if not bloco:
        return {}
    d = json.loads(bloco.group(0))
    return {
        "lufs_integrado": float(d["input_i"]),
        "true_peak_db": float(d["input_tp"]),
        "faixa_dinamica_lu": float(d["input_lra"]),
    }


def energia_por_janela(video: Path, janela: float = 0.25) -> list:
    """Volume RMS por janela curta. Permite ver depois se ha musica por baixo da fala:
    se o audio nunca cai perto do silencio, ha cama sonora continua."""
    out = run([
        FFMPEG, "-i", str(video), "-af",
        f"astats=metadata=1:reset={max(1, int(janela * 44100 / 1024))},ametadata=print:key=lavfi.astats.Overall.RMS_level",
        "-f", "null", "-",
    ])
    valores = [float(v) for v in re.findall(r"RMS_level=(-?[0-9.]+)", out.stderr)]
    return valores


def analisar(video: Path) -> dict:
    meta = metadata(video)
    marcas, crop = cortes(video)
    meta["letterbox"] = crop is not None
    meta["area_ativa"] = crop
    resultado = {
        "ficheiro": video.name,
        "metadata": meta,
        "cortes": estatistica_cortes(marcas, meta["duracao_s"]),
    }
    if meta["tem_audio"]:
        resultado["audio"] = audio(video)
        rms = [v for v in energia_por_janela(video) if v > -120]
        if rms:
            ordenados = sorted(rms)
            p10 = ordenados[int(len(ordenados) * 0.10)]
            resultado["audio"]["rms_percentil10_db"] = round(p10, 2)
            resultado["audio"]["rms_mediano_db"] = round(ordenados[len(ordenados) // 2], 2)
            # Se nem o percentil 10 desce abaixo de -50 dB, praticamente nao ha
            # silencio real: sinal forte de trilha continua por baixo.
            resultado["audio"]["cama_sonora_continua"] = p10 > -50
    return resultado


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    for video in args.videos:
        print(f"[probe] {video.name}", file=sys.stderr)
        dados = analisar(video)
        destino = args.out / f"{video.stem}.probe.json"
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
        c = dados["cortes"]
        print(
            f"  {dados['metadata']['duracao_s']}s | {c['n_cortes']} cortes | "
            f"plano mediano {c.get('plano_mediano_s')}s",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
