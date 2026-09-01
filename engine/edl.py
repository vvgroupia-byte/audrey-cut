#!/usr/bin/env python3
"""O EDL: a lista de decisoes de edicao, e a unica fonte de verdade do corte.

Uso:
    python edl.py validar <edl.json>
    python edl.py resumir <edl.json>

O squad escreve o EDL, este ficheiro verifica se ele fecha, e so depois e que o
render e o CapCut o consomem. Um EDL que nao valida nunca chega ao editor.
"""
import argparse
import json
import sys
from pathlib import Path

# Folga que se deixa de cada lado de um corte de fala. Sem isto o audio estala e
# a primeira consoante da palavra desaparece.
FOLGA_S = 0.06

ESTILOS_LEGENDA = {"base", "gigante", "loop_aberto"}

# Tracos longos, proibidos em toda a copy do projeto. Construidos por codigo de
# caractere para o proprio ficheiro nao conter aquilo que proibe.
TRACOS_PROIBIDOS = (chr(0x2014), chr(0x2013))


class ErroEDL(Exception):
    pass


def _exigir(condicao, mensagem, erros: list):
    if not condicao:
        erros.append(mensagem)


def validar(edl: dict, duracao_fonte: float | None = None) -> list:
    """Devolve a lista de erros. Lista vazia significa EDL valido."""
    erros: list = []

    _exigir(edl.get("fonte"), "falta o campo 'fonte'", erros)

    fmt = edl.get("formato", {})
    _exigir(fmt.get("largura") and fmt.get("altura"), "formato sem largura ou altura", erros)
    if fmt.get("largura") and fmt.get("altura"):
        _exigir(fmt["altura"] > fmt["largura"],
                f"formato {fmt['largura']}x{fmt['altura']} nao e vertical", erros)

    clipes = edl.get("clipes", [])
    _exigir(clipes, "o EDL nao tem nenhum clipe", erros)

    duracao_total = 0.0
    for i, c in enumerate(clipes):
        rotulo = f"clipe {i}"
        if c.get("inicio") is None or c.get("fim") is None:
            erros.append(f"{rotulo}: falta inicio ou fim")
            continue
        if c["fim"] <= c["inicio"]:
            erros.append(f"{rotulo}: fim ({c['fim']}) nao e maior que inicio ({c['inicio']})")
            continue
        if c["inicio"] < 0:
            erros.append(f"{rotulo}: inicio negativo")
        if duracao_fonte and c["fim"] > duracao_fonte + 0.01:
            erros.append(f"{rotulo}: fim {c['fim']}s passa a duracao da fonte ({duracao_fonte}s)")
        if not c.get("motivo"):
            erros.append(f"{rotulo}: sem motivo. Todo corte tem de justificar-se")
        duracao_total += c["fim"] - c["inicio"]

    duracao_total = round(duracao_total, 3)
    declarada = edl.get("duracao_final_s")
    if declarada is not None and abs(declarada - duracao_total) > 0.05:
        erros.append(
            f"a duracao declarada ({declarada}s) nao bate com a soma dos clipes ({duracao_total}s)"
        )

    # As legendas correm no tempo do video montado, nao no tempo do bruto.
    for camada in ("legendas", "enfases", "fixos"):
        for i, t in enumerate(edl.get(camada, [])):
            rotulo = f"{camada}[{i}]"
            if t.get("inicio") is None or t.get("fim") is None:
                erros.append(f"{rotulo}: falta inicio ou fim")
                continue
            if t["fim"] <= t["inicio"]:
                erros.append(f"{rotulo}: fim nao e maior que inicio")
            texto = str(t.get("texto", ""))
            if not texto.strip():
                erros.append(f"{rotulo}: texto vazio")
            if any(traco in texto for traco in TRACOS_PROIBIDOS):
                erros.append(f"{rotulo}: contem traco longo, que e proibido na copy")
            estilo = t.get("estilo")
            if estilo and estilo not in ESTILOS_LEGENDA:
                erros.append(f"{rotulo}: estilo '{estilo}' desconhecido")
            # Um texto que comeca depois do fim do video montado nunca aparece.
            if duracao_total and t["inicio"] > duracao_total + 0.01 and camada != "fixos":
                erros.append(
                    f"{rotulo}: comeca aos {t['inicio']}s, depois do fim do video ({duracao_total}s)"
                )

    audio = edl.get("audio", {})
    if audio.get("lufs_alvo") is not None and not -30 <= audio["lufs_alvo"] <= -6:
        erros.append(f"lufs_alvo {audio['lufs_alvo']} fora de qualquer valor sensato")

    return erros


def estatisticas(edl: dict) -> dict:
    clipes = edl.get("clipes", [])
    duracoes = [round(c["fim"] - c["inicio"], 3) for c in clipes
                if c.get("inicio") is not None and c.get("fim") is not None]
    if not duracoes:
        return {}
    ordenados = sorted(duracoes)
    meio = len(ordenados) // 2
    mediana = ordenados[meio] if len(ordenados) % 2 else (ordenados[meio - 1] + ordenados[meio]) / 2
    total = round(sum(duracoes), 3)

    return {
        "n_clipes": len(duracoes),
        "duracao_final_s": total,
        "plano_medio_s": round(sum(duracoes) / len(duracoes), 3),
        "plano_mediano_s": round(mediana, 3),
        "planos_abaixo_1s_pct": round(100 * sum(1 for d in duracoes if d < 1) / len(duracoes), 1),
        "cortes_por_minuto": round((len(duracoes) - 1) / (total / 60), 1) if total else 0,
        "n_legendas": len(edl.get("legendas", [])),
        "n_enfases": len(edl.get("enfases", [])),
        "enfases_por_minuto": round(len(edl.get("enfases", [])) / (total / 60), 2) if total else 0,
    }


def carregar(caminho: Path) -> dict:
    return json.loads(Path(caminho).read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("acao", choices=["validar", "resumir"])
    ap.add_argument("edl", type=Path)
    ap.add_argument("--duracao-fonte", type=float, default=None)
    args = ap.parse_args()

    edl = carregar(args.edl)

    if args.acao == "validar":
        erros = validar(edl, args.duracao_fonte)
        if erros:
            print(f"EDL invalido, {len(erros)} problema(s):", file=sys.stderr)
            for e in erros:
                print(f"  - {e}", file=sys.stderr)
            sys.exit(1)
        print("EDL valido")
        return

    print(json.dumps(estatisticas(edl), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
