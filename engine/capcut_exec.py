#!/usr/bin/env python3
"""Executa o EDL contra o servidor capcut-mcp e entrega o draft no CapCut.

Uso:
    python capcut_exec.py <edl.json> --manifesto <dir>/manifesto.json [opcoes]

Opcoes:
    --porta N          porta do servidor (defeito: le ~/.audrey-cut/porta.txt, senao 9077)
    --draft-folder D   pasta de drafts do CapCut (defeito: a padrao do macOS)
    --dry-run          mostra as chamadas sem executar nada
    --out plano.json   grava o plano de chamadas (sempre, mesmo sem dry-run)

Por que REST e nao o agente a despachar chamadas MCP: a sequencia de chamadas e
completamente deterministica a partir do EDL. Codigo executa em segundos, nao
erra um nome de campo e e testavel. O MCP continua registado no Claude Code para
a Audrey conversar com o CapCut, mas o caminho quente do /editar e este.

Os nomes e a semantica dos campos vem do codigo do proprio servidor
(fancyboi999/capcut-mcp, lido em app/schemas/ e nos *_impl.py):

    add_video          start/end = recorte NO FICHEIRO de origem;
                       target_start = onde entra na timeline; duration = duracao real
    add_subtitle       srt = conteudo SRT inline (tambem aceita caminho ou URL)
    add_text           start/end na timeline; transform_y normalizado
                       (0 = centro, -0.8 = perto do fundo); font_size em unidade
                       propria do CapCut (legenda tipica = 5)
    add_video_keyframe listas paralelas por indice: property_types[i], times[i],
                       values[i]; valores em texto
    save_draft         draft_folder = pasta de drafts do CapCut; corre em
                       background e devolve task_id para acompanhar
"""
import argparse
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

from edl import carregar, validar

DRAFT_FOLDER_MACOS = str(Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft")
PORTA_FICHEIRO = Path.home() / ".audrey-cut" / "porta.txt"

# Onde o servidor grava o dfd_. O instalador poe o servidor aqui; a segunda
# entrada cobre a instalacao de desenvolvimento.
PASTAS_SERVIDOR = (
    Path.home() / ".audrey-cut" / "capcut-mcp",
    Path.home() / "projetos" / "capcut-mcp",
)

# Conversao dos estilos medidos (fracoes da altura, ver giu-beckers.md) para o
# sistema do CapCut: transform_y normalizado com 0 no centro e -1 no fundo, e
# font_size na unidade propria do app (a legenda padrao do servidor usa 5).
#   62% da altura (legenda base)  -> (0.5 - 0.62) * 2 = -0.24
#   38% da altura (enfase)        -> +0.24
#    8% da altura (texto fixo)    -> +0.84
ESTILOS_TEXTO = {
    "base": {
        "font_color": "#FFFFFF", "font_size": 5.0, "transform_y": -0.24,
        "border_color": "#000000", "border_width": 12.0, "border_alpha": 0.8,
    },
    "gigante": {
        "font_color": "#F5E63D", "font_size": 15.0, "transform_y": 0.24,
        "border_color": "#000000", "border_width": 20.0, "border_alpha": 0.9,
    },
    "loop_aberto": {
        "font_color": "#F5E63D", "font_size": 4.0, "transform_y": 0.84,
        "border_color": "#000000", "border_width": 12.0, "border_alpha": 1.0,
    },
}

ZOOM_MAX = 1.15
ZOOM_DURACAO_S = 0.4


def porta_configurada() -> int:
    if PORTA_FICHEIRO.exists():
        try:
            return int(PORTA_FICHEIRO.read_text().strip())
        except ValueError:
            pass
    return 9077


def chamar(base: str, endpoint: str, corpo: dict) -> dict:
    dados = json.dumps(corpo).encode()
    pedido = urllib.request.Request(
        f"{base}{endpoint}", data=dados,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(pedido, timeout=120) as resposta:
        return json.loads(resposta.read())


def segundos_para_srt(t: float) -> str:
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = int(t % 60)
    ms = round((t - int(t)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def edl_para_srt(legendas: list) -> str:
    """A legenda base inteira vira um unico SRT: uma chamada em vez de dezenas."""
    blocos = []
    for i, l in enumerate(legendas, start=1):
        blocos.append(
            f"{i}\n{segundos_para_srt(l['inicio'])} --> {segundos_para_srt(l['fim'])}\n{l['texto']}\n"
        )
    return "\n".join(blocos)


def construir_chamadas(edl: dict, manifesto: dict, draft_folder: str) -> list:
    fmt = edl.get("formato", {})
    largura, altura = fmt.get("largura", 1080), fmt.get("altura", 1920)

    chamadas = [{
        "endpoint": "/create_draft",
        "corpo": {"width": largura, "height": altura},
        "nota": "cria o projeto e devolve o draft_id",
    }]

    # Clipes ja cortados pelo render: recorte na origem e o ficheiro inteiro
    # (start 0, end = duracao) e target_start posiciona na timeline.
    posicao = 0.0
    mapa_tempo = []
    for clipe in manifesto["clipes"]:
        duracao = clipe["duracao"]
        chamadas.append({
            "endpoint": "/add_video",
            "corpo": {
                "draft_id": "{draft_id}",
                "video_url": clipe["ficheiro"],
                "start": 0,
                "end": round(duracao, 3),
                "duration": round(duracao, 3),
                "target_start": round(posicao, 3),
                "track_name": "video_main",
                "width": largura,
                "height": altura,
                "volume": 1.0,
            },
            "nota": f"clipe {clipe['indice']:03d}: {clipe.get('motivo', '')}",
        })
        mapa_tempo.append({"indice": clipe["indice"], "inicio_montado": round(posicao, 3),
                           "fim_montado": round(posicao + duracao, 3)})
        posicao += duracao
    duracao_final = round(posicao, 3)

    # Zoom por keyframe: listas paralelas por indice, valores em texto.
    for clipe_edl, tempo in zip(edl["clipes"], mapa_tempo):
        if not clipe_edl.get("zoom"):
            continue
        alvo = f"{min(float(clipe_edl['zoom']), ZOOM_MAX):.2f}"
        t0 = tempo["inicio_montado"]
        t1 = round(min(t0 + ZOOM_DURACAO_S, tempo["fim_montado"]), 3)
        chamadas.append({
            "endpoint": "/add_video_keyframe",
            "corpo": {
                "draft_id": "{draft_id}",
                "track_name": "video_main",
                "property_types": ["scale_x", "scale_y", "scale_x", "scale_y"],
                "times": [t0, t0, t1, t1],
                "values": ["1.0", "1.0", alvo, alvo],
            },
            "nota": f"zoom ate {alvo}x no clipe {tempo['indice']:03d}",
        })

    legendas = edl.get("legendas", [])
    if legendas:
        estilo = ESTILOS_TEXTO["base"]
        chamadas.append({
            "endpoint": "/add_subtitle",
            "corpo": {
                "draft_id": "{draft_id}",
                "srt": edl_para_srt(legendas),
                "font_size": estilo["font_size"],
                "font_color": estilo["font_color"],
                "border_color": estilo["border_color"],
                "border_width": estilo["border_width"],
                "border_alpha": estilo["border_alpha"],
                "transform_y": estilo["transform_y"],
                "track_name": "subtitle",
                "width": largura,
                "height": altura,
            },
            "nota": f"legenda base inteira num SRT so ({len(legendas)} blocos)",
        })

    for camada in ("enfases", "fixos"):
        for t in edl.get(camada, []):
            if t["inicio"] >= duracao_final:
                continue
            estilo = ESTILOS_TEXTO.get(t.get("estilo", "gigante" if camada == "enfases" else "loop_aberto"),
                                       ESTILOS_TEXTO["gigante"])
            fim = duracao_final if camada == "fixos" else min(t["fim"], duracao_final)
            chamadas.append({
                "endpoint": "/add_text",
                "corpo": {
                    "draft_id": "{draft_id}",
                    "text": t["texto"],
                    "start": round(t["inicio"], 3),
                    "end": round(fim, 3),
                    "font_color": estilo["font_color"],
                    "font_size": estilo["font_size"],
                    "transform_y": estilo["transform_y"],
                    "border_color": estilo["border_color"],
                    "border_width": estilo["border_width"],
                    "border_alpha": estilo["border_alpha"],
                    "track_name": f"texto_{camada}",
                    "width": largura,
                    "height": altura,
                },
                "nota": f"{camada}: {t['texto'][:40]}",
            })

    chamadas.append({
        "endpoint": "/save_draft",
        "corpo": {"draft_id": "{draft_id}", "draft_folder": draft_folder},
        "nota": "grava o draft direto na pasta do CapCut (sem cp manual)",
    })
    return chamadas


def executar(chamadas: list, base: str) -> dict:
    draft_id = None
    for i, c in enumerate(chamadas):
        corpo = dict(c["corpo"])
        if corpo.get("draft_id") == "{draft_id}":
            corpo["draft_id"] = draft_id
        print(f"[exec] {i + 1}/{len(chamadas)} {c['endpoint']}  {c['nota'][:60]}", file=sys.stderr)
        resposta = chamar(base, c["endpoint"], corpo)
        if not resposta.get("success", False):
            raise SystemExit(
                f"o servidor recusou {c['endpoint']}: {resposta.get('error', resposta)}"
            )
        saida = resposta.get("output") or {}
        if c["endpoint"] == "/create_draft":
            draft_id = saida["draft_id"]
            print(f"[exec] draft_id: {draft_id}", file=sys.stderr)
        if c["endpoint"] == "/save_draft":
            task_id = saida.get("task_id") if isinstance(saida, dict) else None
            estado = acompanhar_gravacao(base, task_id) if task_id else saida
            return {"draft_id": draft_id, "gravacao": estado}
    return {"draft_id": draft_id}


def entregar_no_capcut(draft_id: str, draft_folder: str) -> Path:
    """Copia o dfd_ da pasta do servidor para a pasta de drafts do CapCut.

    O draft_folder no save_draft so reescreve os caminhos internos dos assets
    (o replace_path) para o sitio onde o draft VAI estar. A copia fisica e nossa:
    com o upload para nuvem desligado, o servidor deixa o dfd_ na propria pasta.
    E este passo que substitui o cp manual do tutorial.
    """
    origem = None
    for pasta in PASTAS_SERVIDOR:
        candidata = pasta / draft_id
        if candidata.is_dir():
            origem = candidata
            break
    if origem is None:
        raise SystemExit(
            f"o draft {draft_id} nao apareceu em nenhuma pasta do servidor "
            f"({', '.join(str(p) for p in PASTAS_SERVIDOR)})"
        )

    destino_pai = Path(draft_folder)
    destino_pai.mkdir(parents=True, exist_ok=True)
    destino = destino_pai / draft_id
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origem, destino)

    # Verificacao: o draft tem de levar o JSON principal e os assets.
    if not (destino / "draft_info.json").exists():
        raise SystemExit(f"a copia para {destino} ficou sem draft_info.json")
    return destino


def acompanhar_gravacao(base: str, task_id: str, limite_s: int = 180) -> dict:
    """O save_draft corre em background; fazemos polling ate concluir."""
    inicio = time.time()
    ultimo = {}
    while time.time() - inicio < limite_s:
        ultimo = chamar(base, "/query_draft_status", {"task_id": task_id}).get("output", {})
        estado = ultimo.get("status")
        print(f"[exec] gravacao: {estado} {ultimo.get('progress', '')}%", file=sys.stderr)
        if estado in ("completed", "success"):
            return ultimo
        if estado == "failed":
            raise SystemExit(f"a gravacao do draft falhou: {ultimo.get('message')}")
        time.sleep(2)
    raise SystemExit(f"a gravacao nao terminou em {limite_s}s: {ultimo}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl", type=Path)
    ap.add_argument("--manifesto", type=Path, required=True)
    ap.add_argument("--porta", type=int, default=None)
    ap.add_argument("--draft-folder", default=DRAFT_FOLDER_MACOS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    edl = carregar(args.edl)
    erros = validar(edl)
    if erros:
        raise SystemExit("EDL invalido: " + "; ".join(erros))
    manifesto = json.loads(args.manifesto.read_text())

    chamadas = construir_chamadas(edl, manifesto, args.draft_folder)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(
            {"n_chamadas": len(chamadas), "chamadas": chamadas}, ensure_ascii=False, indent=2))

    if args.dry_run:
        for c in chamadas:
            print(f"{c['endpoint']:22} {c['nota']}")
        print(f"\n{len(chamadas)} chamadas (nada foi executado)")
        return

    porta = args.porta or porta_configurada()
    base = f"http://127.0.0.1:{porta}"
    resultado = executar(chamadas, base)
    destino = entregar_no_capcut(resultado["draft_id"], args.draft_folder)
    print(f"\n[exec] draft {resultado['draft_id']} entregue em {destino}")
    print("[exec] abre (ou fecha e reabre) o CapCut: o projeto esta na lista")


if __name__ == "__main__":
    main()
