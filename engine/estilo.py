#!/usr/bin/env python3
"""Junta os probes e as transcricoes num so relatorio de estilo medido.

Uso:
    python estilo.py --probes work/probe --transcricoes work/transcricoes --out refs/ESTILO-MEDIDO.md

So agrega numeros que ja foram medidos. Nao inventa nem estima nada: campo sem
dado aparece como "sem dado", nunca como palpite.
"""
import argparse
import json
from pathlib import Path

SEM_DADO = "sem dado"


def carregar(pasta: Path, sufixo: str) -> dict:
    saida = {}
    if not pasta.exists():
        return saida
    for f in sorted(pasta.glob(f"*{sufixo}")):
        nome = f.name.replace(sufixo, "")
        saida[nome] = json.loads(f.read_text())
    return saida


def mediana(valores: list):
    if not valores:
        return None
    v = sorted(valores)
    meio = len(v) // 2
    return v[meio] if len(v) % 2 else (v[meio - 1] + v[meio]) / 2


def fmt(v, casas=2, sufixo=""):
    return SEM_DADO if v is None else f"{round(v, casas)}{sufixo}"


def primeiros_segundos(transcricao: dict, limite: float = 3.0) -> str:
    palavras = [p["palavra"] for p in transcricao.get("palavras", []) if p["inicio"] < limite]
    if palavras:
        return " ".join(palavras).strip()
    # Nem toda referencia abre a falar. O formato cinematografico abre em imagem e
    # musica. Dizer so "sem dado" faria o QA reprovar essa abertura por engano.
    todas = transcricao.get("palavras", [])
    if todas:
        return f"(sem fala nos primeiros {limite:.0f}s, abre em imagem. Primeira palavra aos {todas[0]['inicio']:.1f}s)"
    return SEM_DADO


def entrada_da_fala(transcricao: dict):
    palavras = transcricao.get("palavras", [])
    return palavras[0]["inicio"] if palavras else None


def gerar(probes: dict, transcricoes: dict) -> str:
    nomes = sorted(set(probes) | set(transcricoes))
    linhas = [
        "# Estilo medido das referencias",
        "",
        "Todos os numeros abaixo saem de medicao direta dos ficheiros em `refs/`,",
        "feita por `engine/probe.py` e `engine/transcribe.py`. Nada aqui e estimado.",
        "",
        "## Por video",
        "",
        "| Ref | Duracao | Formato | Cortes | Plano mediano | Planos <1s | Palavras/min | Fala entra | LUFS | Cama sonora |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    agregado = {k: [] for k in ("dur", "plano", "cpm", "curtos", "ppm", "lufs", "entrada")}

    for nome in nomes:
        p = probes.get(nome, {})
        t = transcricoes.get(nome, {})
        meta, cortes, audio = p.get("metadata", {}), p.get("cortes", {}), p.get("audio", {})

        dur = meta.get("duracao_s")
        formato = meta.get("aspect", SEM_DADO)
        if meta.get("letterbox"):
            formato += " (letterbox)"
        plano = cortes.get("plano_mediano_s")
        curtos = cortes.get("planos_abaixo_1s_pct")
        ppm = t.get("palavras_por_minuto")
        lufs = audio.get("lufs_integrado")
        cama = audio.get("cama_sonora_continua")

        entrada = entrada_da_fala(t) if t else None

        for chave, valor in (("dur", dur), ("plano", plano), ("cpm", cortes.get("cortes_por_minuto")),
                             ("curtos", curtos), ("ppm", ppm), ("lufs", lufs), ("entrada", entrada)):
            if valor is not None:
                agregado[chave].append(valor)

        linhas.append(
            f"| {nome} | {fmt(dur, 1, 's')} | {formato} | {cortes.get('n_cortes', SEM_DADO)} | "
            f"{fmt(plano, 2, 's')} | {fmt(curtos, 1, '%')} | {fmt(ppm, 0)} | {fmt(entrada, 1, 's')} | "
            f"{fmt(lufs, 1)} | {'sim' if cama else 'nao' if cama is not None else SEM_DADO} |"
        )

    linhas += [
        "",
        "## Denominador comum",
        "",
        "| Metrica | Mediana | Minimo | Maximo |",
        "| --- | --- | --- | --- |",
    ]

    rotulos = [
        ("Duracao (s)", "dur", 1),
        ("Plano mediano (s)", "plano", 2),
        ("Cortes por minuto", "cpm", 1),
        ("Planos abaixo de 1s (%)", "curtos", 1),
        ("Palavras por minuto", "ppm", 0),
        ("Segundo em que a fala entra", "entrada", 1),
        ("Loudness integrado (LUFS)", "lufs", 1),
    ]
    for rotulo, chave, casas in rotulos:
        v = agregado[chave]
        if not v:
            linhas.append(f"| {rotulo} | {SEM_DADO} | {SEM_DADO} | {SEM_DADO} |")
            continue
        linhas.append(
            f"| {rotulo} | {fmt(mediana(v), casas)} | {fmt(min(v), casas)} | {fmt(max(v), casas)} |"
        )

    if transcricoes:
        linhas += ["", "## O que e dito nos primeiros 3 segundos (hook literal)", ""]
        for nome in sorted(transcricoes):
            linhas.append(f"- **{nome}**: \"{primeiros_segundos(transcricoes[nome])}\"")

    return "\n".join(linhas) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probes", type=Path, required=True)
    ap.add_argument("--transcricoes", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    probes = carregar(args.probes, ".probe.json")
    transcricoes = carregar(args.transcricoes, ".transcricao.json")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(gerar(probes, transcricoes))
    print(f"[estilo] {args.out} ({len(probes)} probes, {len(transcricoes)} transcricoes)")


if __name__ == "__main__":
    main()
