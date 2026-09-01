#!/usr/bin/env python3
"""Gera a legenda base a partir do EDL e da transcricao, ja no tempo do montado.

Uso:
    python legendas.py <edl.json> <transcricao.json> [--por-grupo 2]

Escreve as legendas de volta no EDL, no campo "legendas".

Isto e trabalho de contas, nao de julgamento: as palavras e os tempos ja existem
na transcricao, e o que falta e reposiciona-los no tempo do video montado, que
mudou porque houve cortes. Deixar um modelo fazer esta conversao seria caro e,
pior, sujeito a erro de aritmetica silencioso.
"""
import argparse
import json
import sys
from pathlib import Path

from edl import carregar

# Quantas palavras aparecem de cada vez. Medido nas referencias: 1 a 3.
PALAVRAS_POR_GRUPO = 2

# Tempo minimo que um grupo fica no ecra, mesmo que a fala seja mais rapida.
# Abaixo disto o olho nao le e a legenda vira ruido.
DURACAO_MINIMA_S = 0.25


def mapa_de_tempo(clipes: list) -> list:
    """Para cada clipe, onde ele comeca no video montado.

    O corte muda a linha do tempo: uma palavra dita aos 40s do bruto pode cair aos
    12s do montado. Sem este mapa a legenda dessincroniza.
    """
    mapa = []
    posicao = 0.0
    for c in clipes:
        duracao = c["fim"] - c["inicio"]
        mapa.append({
            "bruto_inicio": c["inicio"],
            "bruto_fim": c["fim"],
            "montado_inicio": posicao,
            "deslocamento": posicao - c["inicio"],
        })
        posicao += duracao
    return mapa


def converter(tempo_bruto: float, mapa: list):
    """Converte um instante do bruto para o instante correspondente no montado.
    Devolve None se esse instante foi cortado fora."""
    for m in mapa:
        if m["bruto_inicio"] <= tempo_bruto < m["bruto_fim"]:
            return round(tempo_bruto + m["deslocamento"], 3)
    return None


def gerar(edl: dict, transcricao: dict, por_grupo: int = PALAVRAS_POR_GRUPO) -> list:
    mapa = mapa_de_tempo(edl["clipes"])
    palavras = transcricao.get("palavras", [])

    # So interessam as palavras que sobreviveram ao corte.
    sobreviventes = []
    for p in palavras:
        inicio = converter(p["inicio"], mapa)
        fim = converter(p["fim"], mapa)
        if inicio is None:
            continue
        if fim is None:
            # A palavra ficou a cavalo do corte. Mantem-se, mas termina no limite
            # do clipe para nao invadir o clipe seguinte.
            for m in mapa:
                if m["bruto_inicio"] <= p["inicio"] < m["bruto_fim"]:
                    fim = round(m["bruto_fim"] + m["deslocamento"], 3)
                    break
        if fim is None:
            continue
        if fim <= inicio:
            # O reconhecedor devolve, de vez em quando, uma palavra com duracao
            # zero. Descartar seria deixar uma palavra dita sem legenda no ecra,
            # por isso da-se-lhe uma duracao minima e segue.
            fim = inicio + 0.05
        sobreviventes.append({"palavra": p["palavra"], "inicio": inicio, "fim": fim})

    # Reordenar pelo tempo do montado e nao pelo do bruto.
    # O squad reordena blocos de proposito: o hook costuma vir do meio do material.
    # Sem esta ordenacao, o agrupamento junta palavras de clipes diferentes e as
    # legendas saem trocadas, mesmo com cada tempo individual correto.
    sobreviventes.sort(key=lambda p: p["inicio"])

    legendas = []
    for i in range(0, len(sobreviventes), por_grupo):
        grupo = sobreviventes[i:i + por_grupo]
        inicio = grupo[0]["inicio"]
        fim = max(grupo[-1]["fim"], inicio + DURACAO_MINIMA_S)

        # Nao deixar um grupo pisar o seguinte: a legenda sairia por cima da outra.
        if i + por_grupo < len(sobreviventes):
            proximo = sobreviventes[i + por_grupo]["inicio"]
            fim = min(fim, proximo)

        # Quando as palavras vem muito coladas, o corte acima pode deixar o fim
        # antes do inicio. Nesse caso da-se ao grupo um piscar minimo em vez de o
        # deitar fora: uma sobreposicao de 50ms nao se ve, uma palavra dita que
        # nunca aparece escrita ve-se logo.
        if fim <= inicio:
            fim = inicio + 0.05

        legendas.append({
            "inicio": round(inicio, 3),
            "fim": round(fim, 3),
            "texto": " ".join(g["palavra"] for g in grupo),
            "estilo": "base",
        })

    return legendas


def cobertura(legendas: list, palavras_no_corte: int) -> float:
    """Quantas das palavras que sobreviveram ao corte aparecem escritas.

    Mede-se por palavra e nao por tempo. Por tempo daria sempre abaixo de 100%,
    porque entre uma palavra e a seguinte ha silencio, e o checklist exigiria uma
    coisa impossivel: legenda no ecra durante as pausas da respiracao.

    O que importa e o que o checklist quer mesmo garantir: nenhuma palavra dita
    fica sem estar escrita, porque metade das pessoas assiste sem som.
    """
    if not palavras_no_corte:
        return 0.0
    escritas = sum(len(l["texto"].split()) for l in legendas)
    return round(100 * min(escritas, palavras_no_corte) / palavras_no_corte, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl", type=Path)
    ap.add_argument("transcricao", type=Path)
    ap.add_argument("--por-grupo", type=int, default=PALAVRAS_POR_GRUPO)
    args = ap.parse_args()

    edl = carregar(args.edl)
    transcricao = json.loads(args.transcricao.read_text())

    legendas = gerar(edl, transcricao, args.por_grupo)
    edl["legendas"] = legendas

    duracao = round(sum(c["fim"] - c["inicio"] for c in edl["clipes"]), 3)
    edl["duracao_final_s"] = duracao

    args.edl.write_text(json.dumps(edl, ensure_ascii=False, indent=2))

    mapa = mapa_de_tempo(edl["clipes"])
    no_corte = sum(1 for p in transcricao.get("palavras", [])
                   if converter(p["inicio"], mapa) is not None)
    pct = cobertura(legendas, no_corte)

    print(f"[legendas] {len(legendas)} grupos de ate {args.por_grupo} palavra(s)")
    print(f"[legendas] {no_corte} palavras sobreviveram ao corte, cobertura {pct}%")
    if pct < 100:
        print(f"[legendas] ATENCAO: ha palavra dita sem legenda no ecra", file=sys.stderr)
    for l in legendas[:5]:
        print(f"  {l['inicio']:6.2f}-{l['fim']:6.2f}  {l['texto']}")


if __name__ == "__main__":
    main()
