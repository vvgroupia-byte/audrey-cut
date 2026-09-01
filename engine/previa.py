#!/usr/bin/env python3
"""Junta os clipes cortados num unico ficheiro, para se ver o corte antes do CapCut.

Uso:
    python previa.py <dir_clipes>/manifesto.json --out <previa.mp4>

Nao substitui o CapCut: a previa nao leva legendas nem enfases, so o corte e o
audio. Serve para responder a uma pergunta so, que e a mais importante: o ritmo
ficou bom?

Nota sobre o metodo: aqui usa-se o **filtro** concat, nao o demuxer concat. O
demuxer copia os pacotes sem os decodificar, e com AAC isso deixa os timestamps
inconsistentes: a duracao final chega a aparecer para o dobro do que e. O filtro
decodifica e recodifica, e mais lento, mas devolve um ficheiro correto.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import av

FFMPEG = "ffmpeg"


def montar(manifesto: dict, destino: Path) -> bool:
    clipes = manifesto.get("clipes", [])
    if not clipes:
        print("[previa] o manifesto nao tem clipes", file=sys.stderr)
        return False

    ficheiros = [Path(c["ficheiro"]) for c in clipes]
    em_falta = [f for f in ficheiros if not f.exists()]
    if em_falta:
        for f in em_falta:
            print(f"[previa] falta o ficheiro {f}", file=sys.stderr)
        return False

    cmd = [FFMPEG, "-y", "-loglevel", "error"]
    for f in ficheiros:
        cmd += ["-i", str(f)]

    entradas = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(len(ficheiros)))
    cmd += [
        "-filter_complex", f"{entradas}concat=n={len(ficheiros)}:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        str(destino),
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[previa] o ffmpeg falhou: {r.stderr.strip()[:300]}", file=sys.stderr)
        return False
    return True


def conferir(destino: Path, esperado: float) -> bool:
    """A duracao tem de bater com a soma dos clipes. Se nao bater, a previa mente
    e nao serve para avaliar ritmo."""
    with av.open(str(destino)) as c:
        real = c.duration / av.time_base
        vs = c.streams.video[0]
        largura, altura = vs.codec_context.width, vs.codec_context.height
        tem_audio = len(c.streams.audio) > 0

    diferenca = abs(real - esperado)
    print(f"[previa] {destino.name}: {real:.2f}s, {largura}x{altura}, audio={'sim' if tem_audio else 'NAO'}")

    if diferenca > 0.5:
        print(f"[previa] ATENCAO: esperava {esperado:.2f}s e saiu {real:.2f}s "
              f"(diferenca de {diferenca:.2f}s)", file=sys.stderr)
        return False
    if not tem_audio:
        print("[previa] ATENCAO: a previa saiu sem audio", file=sys.stderr)
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifesto", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    manifesto = json.loads(args.manifesto.read_text())
    esperado = manifesto.get("duracao_total_s", 0)

    if not montar(manifesto, args.out):
        sys.exit(1)
    if not conferir(args.out, esperado):
        sys.exit(1)

    print(f"[previa] pronta em {args.out}")


if __name__ == "__main__":
    main()
