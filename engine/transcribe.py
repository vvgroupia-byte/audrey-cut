#!/usr/bin/env python3
"""Transcreve com timestamp por palavra. Local, sem chave de API, sem upload.

Uso:
    python transcribe.py <video.mp4> [...] --out <dir> [--modelo large-v3] [--idioma pt]

Escreve <dir>/<nome>.transcricao.json com segmentos e palavras.
O timestamp por palavra e o que permite cortar no sitio exato depois.
"""
import argparse
import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel

_modelo_cache = {}


def carregar(nome: str) -> WhisperModel:
    if nome not in _modelo_cache:
        print(f"[whisper] a carregar {nome}...", file=sys.stderr)
        # int8 no CPU do Apple Silicon da a melhor relacao velocidade/precisao.
        _modelo_cache[nome] = WhisperModel(nome, device="cpu", compute_type="int8")
    return _modelo_cache[nome]


def transcrever(video: Path, modelo: str, idioma: str | None) -> dict:
    m = carregar(modelo)
    segmentos, info = m.transcribe(
        str(video),
        language=idioma,
        word_timestamps=True,
        vad_filter=True,
        # min_silence 300ms: nao queremos que o VAD engula as micro-pausas,
        # porque sao elas que o detector de cortes vai usar.
        vad_parameters={"min_silence_duration_ms": 300},
        beam_size=5,
    )

    saida_segmentos = []
    todas_palavras = []
    for seg in segmentos:
        palavras = [
            {
                "palavra": w.word.strip(),
                "inicio": round(w.start, 3),
                "fim": round(w.end, 3),
                "confianca": round(w.probability, 3),
            }
            for w in (seg.words or [])
        ]
        todas_palavras.extend(palavras)
        saida_segmentos.append({
            "inicio": round(seg.start, 3),
            "fim": round(seg.end, 3),
            "texto": seg.text.strip(),
            "palavras": palavras,
        })
        print(f"  [{seg.start:7.2f}] {seg.text.strip()[:80]}", file=sys.stderr)

    return {
        "ficheiro": video.name,
        "idioma": info.language,
        "idioma_confianca": round(info.language_probability, 3),
        "modelo": modelo,
        "duracao_s": round(info.duration, 3),
        "texto_completo": " ".join(s["texto"] for s in saida_segmentos),
        "n_palavras": len(todas_palavras),
        "palavras_por_minuto": round(len(todas_palavras) / (info.duration / 60), 1) if info.duration else 0,
        "segmentos": saida_segmentos,
        "palavras": todas_palavras,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    # Medido nesta maquina, num video de 58,8s:
    #   large-v3-turbo  55,3s  (1,1x tempo real)
    #   large-v3       147,9s  (0,4x tempo real)
    # O turbo e 2,7x mais rapido e a transcricao e equivalente. Onde diferiram, o
    # turbo escreveu a fala como ela sai ("os dias tao dificeis") e o large-v3
    # corrigiu a gramatica ("estao dificeis"). Para legenda, o turbo esta certo:
    # a legenda transcreve, nao corrige.
    ap.add_argument("--modelo", default="large-v3-turbo",
                    help="large-v3-turbo (defeito, rapido) ou large-v3 (mais lento)")
    ap.add_argument("--idioma", default="pt", help="codigo ISO, ou 'auto' para detetar")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    idioma = None if args.idioma == "auto" else args.idioma

    for video in args.videos:
        destino = args.out / f"{video.stem}.transcricao.json"
        if destino.exists():
            print(f"[skip] {video.name} ja transcrito", file=sys.stderr)
            continue
        print(f"[transcribe] {video.name}", file=sys.stderr)
        dados = transcrever(video, args.modelo, idioma)
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
        print(f"  {dados['n_palavras']} palavras, {dados['palavras_por_minuto']} ppm", file=sys.stderr)


if __name__ == "__main__":
    main()
