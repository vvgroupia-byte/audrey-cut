#!/usr/bin/env python3
"""Corta o bruto nos pedacos que o EDL manda e normaliza o audio.

Uso:
    python render.py <edl.json> --out <dir>

Cada clipe do EDL vira um ficheiro. E o ffmpeg que corta, com precisao de frame,
porque os servidores de CapCut da comunidade sao fragilissimos a fazer trim: e
mais seguro darmos-lhes clipes ja prontos e deixar so o trabalho de enfileirar.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from edl import FOLGA_S, carregar, validar

FFMPEG = "ffmpeg"

# Alvo de loudness. As sete referencias medidas estao todas entre -14,7 e -14,2,
# que e tambem o que as plataformas usam como referencia.
LUFS_ALVO = -14.0


def corrida(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def cortar(fonte: Path, inicio: float, fim: float, destino: Path, largura: int, altura: int) -> bool:
    """Corta um segmento e enquadra no formato final.

    O -ss vem depois do -i de proposito: e mais lento, mas corta no frame exato.
    Com -ss antes do -i o ffmpeg salta para o keyframe mais proximo e o corte
    escorrega ate meio segundo, o que estraga o sincronismo com a legenda.
    """
    duracao = round(fim - inicio, 3)
    filtro = (
        f"scale={largura}:{altura}:force_original_aspect_ratio=increase,"
        f"crop={largura}:{altura}"
    )
    r = corrida([
        FFMPEG, "-y", "-loglevel", "error",
        "-i", str(fonte),
        "-ss", f"{inicio:.3f}", "-t", f"{duracao:.3f}",
        "-vf", filtro,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-avoid_negative_ts", "make_zero",
        str(destino),
    ])
    if r.returncode != 0:
        print(f"  [erro] {destino.name}: {r.stderr.strip()[:200]}", file=sys.stderr)
        return False
    return True


def normalizar(entrada: Path, saida: Path, lufs: float) -> bool:
    """Passagem dupla de loudnorm. A primeira mede, a segunda corrige.

    Uma so passagem faz o ffmpeg adivinhar enquanto processa, e o resultado
    fica ate 2 LU fora do alvo. Em video curto isso da-se pelo ouvido.
    """
    medicao = corrida([
        FFMPEG, "-i", str(entrada),
        "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-",
    ])
    import re
    bloco = re.search(r"\{[^{]*\"input_i\"[^}]*\}", medicao.stderr, re.S)
    if not bloco:
        print(f"  [aviso] nao consegui medir o audio de {entrada.name}, fica sem normalizar",
              file=sys.stderr)
        return False

    m = json.loads(bloco.group(0))
    filtro = (
        f"loudnorm=I={lufs}:TP=-1.5:LRA=11:"
        f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
        f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
        f"offset={m['target_offset']}:linear=true"
    )
    r = corrida([
        FFMPEG, "-y", "-loglevel", "error", "-i", str(entrada),
        "-af", filtro, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(saida),
    ])
    return r.returncode == 0


def avisar_se_horizontal(fonte: Path, largura: int, altura: int):
    """Grita se o bruto nao for vertical.

    O enquadramento faz crop central para chegar ao 9:16. Num bruto horizontal
    isso corta as laterais e, pior, costuma cortar a cabeca de quem fala, porque
    numa gravacao 16:9 a pessoa raramente esta centrada na vertical. E um erro
    caro e silencioso: so se ve depois de o video estar montado.
    """
    import av
    with av.open(str(fonte)) as c:
        vs = c.streams.video[0]
        w, h = vs.codec_context.width, vs.codec_context.height

    if h > w:
        return
    print(f"\n  AVISO: o video de origem e {w}x{h}, que nao e vertical.", file=sys.stderr)
    print(f"  Para chegar a {largura}x{altura} vai ser cortado pelos lados, e isso", file=sys.stderr)
    print("  costuma cortar a cabeca de quem fala. Confere a previa antes de montar.\n",
          file=sys.stderr)


def renderizar(edl: dict, destino: Path, aplicar_folga: bool = True) -> dict:
    fonte = Path(edl["fonte"])
    if not fonte.exists():
        raise SystemExit(f"o ficheiro de origem nao existe: {fonte}")

    fmt = edl.get("formato", {})
    largura, altura = fmt.get("largura", 1080), fmt.get("altura", 1920)
    avisar_se_horizontal(fonte, largura, altura)
    lufs = edl.get("audio", {}).get("lufs_alvo", LUFS_ALVO)

    destino.mkdir(parents=True, exist_ok=True)
    produzidos = []

    for i, c in enumerate(edl["clipes"]):
        inicio, fim = c["inicio"], c["fim"]
        if aplicar_folga:
            # A folga evita o clique no corte e a consoante comida no arranque.
            inicio = max(0.0, inicio - FOLGA_S)
            fim = fim + FOLGA_S

        bruto = destino / f"clipe_{i:03d}_bruto.mp4"
        final = destino / f"clipe_{i:03d}.mp4"

        print(f"[render] clipe {i:03d}  {inicio:7.2f}s a {fim:7.2f}s  ({c.get('motivo', '')})",
              file=sys.stderr)
        if not cortar(fonte, inicio, fim, bruto, largura, altura):
            continue

        if normalizar(bruto, final, lufs):
            bruto.unlink()
        else:
            bruto.rename(final)

        produzidos.append({
            "indice": i,
            "ficheiro": str(final),
            "inicio_no_bruto": round(inicio, 3),
            "fim_no_bruto": round(fim, 3),
            "duracao": round(fim - inicio, 3),
            "motivo": c.get("motivo"),
        })

    manifesto = {
        "fonte": str(fonte),
        "formato": fmt,
        "lufs_alvo": lufs,
        "n_clipes": len(produzidos),
        "duracao_total_s": round(sum(p["duracao"] for p in produzidos), 3),
        "clipes": produzidos,
    }
    (destino / "manifesto.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2))
    return manifesto


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sem-folga", action="store_true",
                    help="corta exatamente no tempo do EDL, sem os 60ms de respiro")
    args = ap.parse_args()

    edl = carregar(args.edl)
    erros = validar(edl)
    if erros:
        print("nao renderizo um EDL invalido:", file=sys.stderr)
        for e in erros:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    m = renderizar(edl, args.out, aplicar_folga=not args.sem_folga)
    print(f"\n[render] {m['n_clipes']} clipes, {m['duracao_total_s']}s no total")
    print(f"[render] manifesto em {args.out / 'manifesto.json'}")


if __name__ == "__main__":
    main()
