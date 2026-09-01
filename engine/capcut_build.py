#!/usr/bin/env python3
"""Traduz o EDL para a sequencia de chamadas do MCP do CapCut.

Uso:
    python capcut_build.py <edl.json> --manifesto <dir_render>/manifesto.json --out <plano.json>

Este ficheiro nao chama o MCP. Produz o plano de chamadas, por ordem, com os
argumentos ja calculados. Quem executa e o agente, que tem o MCP ligado.

A separacao e util: o calculo de tempos, posicoes e estilos fica deterministico e
testavel aqui, e o agente so despacha. Se o servidor mudar o nome de uma
ferramenta, muda-se num sitio so.

## Sobre os nomes dos parametros

Os nomes abaixo seguem a documentacao do VectCutAPI (o upstream do servidor
rabbitorial-capcut-mcp), em MCP_Documentation_English.md. Confirmados a partir dos
exemplos publicados:

    add_video          -> video_url, draft_id, start, end, volume
    add_text           -> text, draft_id, font_size, font_color, shadow_enabled,
                          shadow_color, shadow_alpha, background_color,
                          background_alpha, background_round_radius
    add_video_keyframe -> draft_id, track_name, property_types, times, values
    add_audio          -> audio_url, draft_id, volume, speed
    save_draft         -> draft_id

Atencao a dois pormenores que custam caro se forem assumidos ao contrario:

1. `add_video` usa **start e end**, nao start e duration. Sao instantes na linha
   do tempo, nao uma duracao.
2. `add_video_keyframe` recebe **tres listas paralelas** (property_types, times,
   values), nao uma lista de objetos com tempo e valor. E `values` vai em texto.

O que a documentacao publica **nao** esclarece, e por isso nao e assumido aqui:
o sistema de coordenadas de transform_x/transform_y (pixel ou normalizado), se
add_video e add_text aceitam track_name, e a unidade de font_size. Esses campos
saem em `campos_incertos`, para o agente confirmar contra o servidor antes de
enviar, em vez de irem silenciosamente errados no meio do plano.
"""
import argparse
import json
from pathlib import Path

from edl import carregar, validar

LARGURA_PADRAO, ALTURA_PADRAO = 1080, 1920

# Estilos medidos nos frames das referencias. Ver squad/agents/giu-beckers.md.
# tamanho_rel e y_rel sao fracoes da altura do ecra, convertidas no fim.
ESTILOS = {
    "base": {
        "font_color": "#FFFFFF",
        "tamanho_rel": 0.045,
        "y_rel": 0.62,
        "shadow_enabled": True,
        "shadow_color": "#000000",
        "shadow_alpha": 0.8,
        "background_color": None,
    },
    "gigante": {
        "font_color": "#F5E63D",   # amarelo neon, a cor dominante nas referencias
        "tamanho_rel": 0.19,
        "y_rel": 0.38,
        "shadow_enabled": True,
        "shadow_color": "#000000",
        "shadow_alpha": 0.9,
        "background_color": None,
    },
    "loop_aberto": {
        "font_color": "#F5E63D",
        "tamanho_rel": 0.035,
        "y_rel": 0.08,
        "shadow_enabled": True,
        "shadow_color": "#000000",
        "shadow_alpha": 1.0,
        "background_color": None,
    },
}

# Acima de 1,15 comeca a ver-se o ruido de compressao do telemovel.
ZOOM_MAX = 1.15
ZOOM_DURACAO_S = 0.4


def texto_para_chamada(t: dict, largura: int, altura: int) -> tuple:
    """Devolve (argumentos confirmados, campos incertos) para uma entrada de texto."""
    estilo = ESTILOS.get(t.get("estilo", "base"), ESTILOS["base"])

    argumentos = {
        "draft_id": "{draft_id}",
        "text": t["texto"],
        "start": round(t["inicio"], 3),
        "end": round(t["fim"], 3),
        "font_size": round(altura * estilo["tamanho_rel"]),
        "font_color": estilo["font_color"],
        "shadow_enabled": estilo["shadow_enabled"],
        "shadow_color": estilo["shadow_color"],
        "shadow_alpha": estilo["shadow_alpha"],
    }
    if estilo["background_color"]:
        argumentos["background_color"] = estilo["background_color"]

    # A posicao vertical e essencial ao estilo, mas o sistema de coordenadas nao
    # esta documentado. Vai como incerto, com as duas leituras possiveis, para o
    # agente escolher depois de ver o schema real da ferramenta.
    incertos = {
        "transform_y": {
            "se_normalizado": round((t.get("y_rel", estilo["y_rel"]) - 0.5) * 2, 3),
            "se_pixel": round(altura * estilo["y_rel"]),
            "nota": "posicao vertical. Confirmar se a ferramenta espera -1..1 ou pixel",
        }
    }
    return argumentos, incertos


def construir(edl: dict, manifesto: dict) -> dict:
    fmt = edl.get("formato", {})
    largura = fmt.get("largura", LARGURA_PADRAO)
    altura = fmt.get("altura", ALTURA_PADRAO)

    chamadas = []

    chamadas.append({
        "ferramenta": "create_draft",
        "argumentos": {"width": largura, "height": altura},
        "guardar_resultado_como": "draft_id",
        "nota": "cria o projeto vazio e devolve o id usado por todas as chamadas seguintes",
    })

    # Os clipes ja vem cortados e normalizados do render, por isso entram inteiros.
    # O MCP so os enfileira, que e a operacao em que estes servidores sao fiaveis.
    posicao = 0.0
    mapa_tempo = []
    for clipe in manifesto["clipes"]:
        duracao = clipe["duracao"]
        inicio, fim = round(posicao, 3), round(posicao + duracao, 3)
        chamadas.append({
            "ferramenta": "add_video",
            "argumentos": {
                "draft_id": "{draft_id}",
                "video_url": clipe["ficheiro"],
                "start": inicio,
                "end": fim,
            },
            "nota": f"clipe {clipe['indice']:03d}: {clipe.get('motivo', '')}",
        })
        mapa_tempo.append({
            "indice": clipe["indice"],
            "inicio_montado": inicio,
            "fim_montado": fim,
            "inicio_no_bruto": clipe["inicio_no_bruto"],
        })
        posicao += duracao

    duracao_final = round(posicao, 3)

    # Zoom: tres listas paralelas, e os valores vao em texto.
    for clipe_edl, tempo in zip(edl["clipes"], mapa_tempo):
        if not clipe_edl.get("zoom"):
            continue
        alvo = min(float(clipe_edl["zoom"]), ZOOM_MAX)
        t0 = tempo["inicio_montado"]
        t1 = round(min(t0 + ZOOM_DURACAO_S, tempo["fim_montado"]), 3)
        chamadas.append({
            "ferramenta": "add_video_keyframe",
            "argumentos": {
                "draft_id": "{draft_id}",
                "property_types": ["scale_x", "scale_y"],
                "times": [t0, t1],
                "values": ["1.0", f"{alvo:.2f}"],
            },
            "campos_incertos": {
                "track_name": {
                    "valor_provavel": "video_main",
                    "nota": "nome da pista de video. Confirmar como o servidor chama a pista principal",
                }
            },
            "nota": f"zoom ate {alvo:.2f}x no clipe {tempo['indice']:03d}",
        })

    for camada in ("legendas", "enfases", "fixos"):
        for t in edl.get(camada, []):
            if t["inicio"] >= duracao_final:
                continue  # texto fora do video montado nunca apareceria
            entrada = dict(t)
            entrada["fim"] = duracao_final if camada == "fixos" else min(t["fim"], duracao_final)
            argumentos, incertos = texto_para_chamada(entrada, largura, altura)
            chamadas.append({
                "ferramenta": "add_text",
                "argumentos": argumentos,
                "campos_incertos": incertos,
                "nota": f"{camada}: {t['texto'][:40]}",
            })

    musica = edl.get("audio", {}).get("cama_sonora_ficheiro")
    if musica:
        chamadas.append({
            "ferramenta": "add_audio",
            "argumentos": {
                "draft_id": "{draft_id}",
                "audio_url": musica,
                "start": 0,
                "end": duracao_final,
                "volume": 0.12,
            },
            "nota": "cama sonora, baixa o suficiente para nao disputar com a voz",
        })

    chamadas.append({
        "ferramenta": "save_draft",
        "argumentos": {"draft_id": "{draft_id}"},
        "nota": "grava o projeto na pasta do CapCut. Depois disto ele aparece no app",
    })

    com_incerteza = sum(1 for c in chamadas if c.get("campos_incertos"))

    return {
        "fonte": edl["fonte"],
        "formato": {"largura": largura, "altura": altura},
        "duracao_final_s": duracao_final,
        "n_chamadas": len(chamadas),
        "chamadas_com_campos_incertos": com_incerteza,
        "instrucoes_para_o_agente": [
            "Executa as chamadas por ordem.",
            "A primeira devolve um id: substitui {draft_id} em todas as seguintes.",
            "Antes de enviar uma chamada com 'campos_incertos', le o schema real da "
            "ferramenta no MCP e escolhe o valor certo. Nao adivinhes.",
            "Se uma chamada falhar, para e diz qual foi. Nao continues a montar por cima de um erro.",
        ],
        "mapa_tempo": mapa_tempo,
        "chamadas": chamadas,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl", type=Path)
    ap.add_argument("--manifesto", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    edl = carregar(args.edl)
    erros = validar(edl)
    if erros:
        raise SystemExit("EDL invalido: " + "; ".join(erros))

    manifesto = json.loads(args.manifesto.read_text())
    plano = construir(edl, manifesto)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plano, ensure_ascii=False, indent=2))

    print(f"[capcut] {plano['n_chamadas']} chamadas, video final de {plano['duracao_final_s']}s")
    if plano["chamadas_com_campos_incertos"]:
        print(f"[capcut] {plano['chamadas_com_campos_incertos']} chamadas tem campos por confirmar "
              f"contra o schema real do servidor")
    print(f"[capcut] plano em {args.out}")


if __name__ == "__main__":
    main()
