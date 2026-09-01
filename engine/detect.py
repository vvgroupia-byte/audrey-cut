#!/usr/bin/env python3
"""Encontra o que sobra num take: silencios, muletas e tomadas repetidas.

Uso:
    python detect.py <transcricao.json> --out <candidatos.json>

Nao decide nada sozinho. Marca candidatos com o motivo, e o squad decide o que
cortar de facto. Cortar por conta propria e como o editor apagar a melhor pausa
dramatica do video porque tinha 1,2 segundos.
"""
import argparse
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

# Silencio a partir do qual vale a pena propor corte. Abaixo disto e respiracao
# normal de fala e cortar deixa o audio atropelado.
SILENCIO_MIN_S = 0.45

# Muletas de fala em pt-BR e pt-PT. So sao propostas quando aparecem isoladas,
# nunca dentro de uma frase onde carregam sentido.
MULETAS = {
    "hmm", "hum", "ahn", "ah", "eh", "ehh", "uh", "tipo", "ne", "entao",
    "assim", "sabe", "pronto", "ora", "bem", "olha", "quer dizer",
}

# Duas falas acima disto contam como o mesmo take repetido.
SIMILARIDADE_TAKE = 0.82


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", " ", texto).strip()


def silencios(palavras: list) -> list:
    achados = []
    for anterior, seguinte in zip(palavras, palavras[1:]):
        vao = seguinte["inicio"] - anterior["fim"]
        if vao >= SILENCIO_MIN_S:
            achados.append({
                "tipo": "silencio",
                "inicio": round(anterior["fim"], 3),
                "fim": round(seguinte["inicio"], 3),
                "duracao": round(vao, 3),
                "motivo": f"pausa de {vao:.2f}s entre '{anterior['palavra']}' e '{seguinte['palavra']}'",
            })
    return achados


def muletas(palavras: list) -> list:
    achados = []
    for p in palavras:
        limpa = normalizar(p["palavra"])
        if limpa in MULETAS:
            achados.append({
                "tipo": "muleta",
                "inicio": p["inicio"],
                "fim": p["fim"],
                "duracao": round(p["fim"] - p["inicio"], 3),
                "texto": p["palavra"],
                "confianca_asr": p.get("confianca"),
                "motivo": f"muleta de fala: '{p['palavra']}'",
            })
    return achados


def takes_repetidos(segmentos: list) -> list:
    """Compara cada frase com as seguintes. Quando ela se repete, a ultima versao
    e a boa: e a tomada em que a pessoa finalmente acertou."""
    achados = []
    normalizados = [normalizar(s["texto"]) for s in segmentos]

    for i, atual in enumerate(normalizados):
        if len(atual.split()) < 4:
            continue  # frases curtas repetem por acaso, nao por erro de take
        for j in range(i + 1, min(i + 5, len(normalizados))):
            razao = SequenceMatcher(None, atual, normalizados[j]).ratio()
            if razao >= SIMILARIDADE_TAKE:
                achados.append({
                    "tipo": "take_repetido",
                    "inicio": segmentos[i]["inicio"],
                    "fim": segmentos[i]["fim"],
                    "duracao": round(segmentos[i]["fim"] - segmentos[i]["inicio"], 3),
                    "texto": segmentos[i]["texto"],
                    "repete_em": segmentos[j]["inicio"],
                    "texto_final": segmentos[j]["texto"],
                    "similaridade": round(razao, 3),
                    "motivo": f"repetido aos {segmentos[j]['inicio']:.1f}s, manter a versao de la",
                })
                break
    return achados


def baixa_confianca(palavras: list, limiar: float = 0.5) -> list:
    """Palavras que o ASR mal entendeu. Costumam ser gaguejo ou palavra cortada."""
    return [
        {
            "tipo": "baixa_confianca",
            "inicio": p["inicio"],
            "fim": p["fim"],
            "duracao": round(p["fim"] - p["inicio"], 3),
            "texto": p["palavra"],
            "confianca_asr": p["confianca"],
            "motivo": f"ASR inseguro ({p['confianca']:.2f}), possivel gaguejo ou palavra cortada",
        }
        for p in palavras
        if p.get("confianca") is not None and p["confianca"] < limiar
    ]


def analisar(transcricao: dict) -> dict:
    palavras = transcricao.get("palavras", [])
    segmentos = transcricao.get("segmentos", [])

    candidatos = (
        silencios(palavras) + muletas(palavras)
        + takes_repetidos(segmentos) + baixa_confianca(palavras)
    )
    candidatos.sort(key=lambda c: c["inicio"])

    tempo_por_tipo = {}
    for c in candidatos:
        tempo_por_tipo[c["tipo"]] = round(tempo_por_tipo.get(c["tipo"], 0) + c["duracao"], 2)

    duracao = transcricao.get("duracao_s", 0)
    total_removivel = round(sum(tempo_por_tipo.values()), 2)

    return {
        "ficheiro": transcricao.get("ficheiro"),
        "duracao_original_s": duracao,
        "resumo": {
            "n_candidatos": len(candidatos),
            "por_tipo": {t: sum(1 for c in candidatos if c["tipo"] == t) for t in tempo_por_tipo},
            "segundos_por_tipo": tempo_por_tipo,
            "total_removivel_s": total_removivel,
            "duracao_se_cortar_tudo_s": round(duracao - total_removivel, 2),
            "reducao_pct": round(100 * total_removivel / duracao, 1) if duracao else 0,
        },
        "candidatos": candidatos,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcricoes", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    for caminho in args.transcricoes:
        dados = analisar(json.loads(caminho.read_text()))
        nome = caminho.name.replace(".transcricao.json", "")
        destino = args.out / f"{nome}.candidatos.json"
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
        r = dados["resumo"]
        print(f"[detect] {nome}: {r['n_candidatos']} candidatos, "
              f"{r['total_removivel_s']}s removiveis ({r['reducao_pct']}%)")


if __name__ == "__main__":
    main()
