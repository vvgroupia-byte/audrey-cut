#!/usr/bin/env python3
"""Extrai uma folha de contacto de cada video, para inspecao visual do estilo.

Uso:
    python frames.py <video.mp4> [...] --out <dir> [--n 12]

Uma imagem por video, com N frames em grelha e o timestamp gravado em cada um.
Serve para ler legenda, tipografia, cor, posicao e enquadramento sem abrir o video.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import av

FFMPEG = "ffmpeg"


def duracao(video: Path) -> float:
    with av.open(str(video)) as c:
        return c.duration / av.time_base if c.duration else 0.0


def folha_de_contacto(video: Path, destino: Path, n: int, colunas: int = 4):
    total = duracao(video)
    if not total:
        print(f"[erro] duracao zero em {video.name}", file=sys.stderr)
        return

    # Evita o primeiro e o ultimo instante, onde costuma haver fade ou frame preto.
    passo = total / (n + 1)
    tempos = [round(passo * (i + 1), 3) for i in range(n)]

    temp = destino.parent / f"_{video.stem}_frames"
    temp.mkdir(parents=True, exist_ok=True)

    for i, t in enumerate(tempos):
        alvo = temp / f"{i:02d}.jpg"
        subprocess.run(
            [FFMPEG, "-y", "-loglevel", "error", "-ss", str(t), "-i", str(video),
             "-frames:v", "1",
             "-vf", f"scale=360:-1,drawtext=text='{t:.1f}s':x=8:y=8:fontsize=22:"
                    "fontcolor=yellow:box=1:boxcolor=black@0.6:boxborderw=4",
             str(alvo)],
            capture_output=True,
        )

    linhas = -(-n // colunas)
    subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", str(temp / "%02d.jpg"),
         "-filter_complex", f"tile={colunas}x{linhas}:margin=6:padding=6:color=white",
         "-frames:v", "1", str(destino)],
        capture_output=True,
    )

    for f in temp.iterdir():
        f.unlink()
    temp.rmdir()
    print(f"[frames] {destino.name} ({n} frames de {total:.1f}s)", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    for video in args.videos:
        folha_de_contacto(video, args.out / f"{video.stem}.jpg", args.n)


if __name__ == "__main__":
    main()
