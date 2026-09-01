#!/usr/bin/env python3
"""Testes do motor. Corre com: .venv/bin/python tests/test_motor.py

Sem dependencias de teste: o objetivo e que isto corra em qualquer maquina onde o
sistema esteja instalado, sem instalar mais nada.

Cobre a aritmetica, que e onde os erros sao silenciosos e caros: conversao de
tempos depois de reordenar clipes, validacao do EDL, e os nomes dos parametros
que vao para o CapCut.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))

import capcut_build
import detect
import edl as edl_mod
import legendas

falhas = []
passou = 0


def verificar(condicao, descricao, detalhe=""):
    global passou
    if condicao:
        passou += 1
        print(f"  ok    {descricao}")
    else:
        falhas.append(descricao)
        print(f"  FALHA {descricao}" + (f"\n        {detalhe}" if detalhe else ""))


def edl_exemplo():
    """Um EDL com os clipes fora de ordem cronologica, de proposito: o hook vem do
    meio do material, que e como o squad monta na pratica."""
    return {
        "fonte": "video.mp4",
        "formato": {"largura": 1080, "altura": 1920, "fps": 30},
        "clipes": [
            {"inicio": 30.0, "fim": 33.0, "motivo": "hook", "zoom": 1.12},
            {"inicio": 10.0, "fim": 14.0, "motivo": "prova"},
            {"inicio": 50.0, "fim": 52.0, "motivo": "fecho"},
        ],
        "legendas": [],
        "enfases": [{"inicio": 0.5, "fim": 2.0, "texto": "SEGREDO", "estilo": "gigante"}],
        "fixos": [],
        "audio": {"lufs_alvo": -14, "cama_sonora": True},
    }


def transcricao_exemplo():
    """Palavras espalhadas: algumas dentro dos clipes, outras no material cortado."""
    palavras = []
    for inicio, texto in [
        (10.0, "esta"), (10.5, "e"), (11.0, "a"), (11.5, "prova"),      # clipe 1
        (20.0, "isto"), (20.5, "sai"),                                  # cortado fora
        (30.0, "o"), (30.5, "grande"), (31.0, "segredo"), (31.5, "e"),  # clipe 0, o hook
        (50.0, "fim"), (50.5, "disto"),                                 # clipe 2
    ]:
        palavras.append({"palavra": texto, "inicio": inicio, "fim": inicio + 0.4, "confianca": 0.9})
    return {"ficheiro": "video.mp4", "duracao_s": 60.0, "palavras": palavras, "segmentos": []}


print("\nEDL: validacao\n")

bom = edl_exemplo()
bom["duracao_final_s"] = 9.0
verificar(edl_mod.validar(bom) == [], "um EDL correto passa sem erros",
          str(edl_mod.validar(bom)))

mau = edl_exemplo()
mau["clipes"][0]["fim"] = 20.0  # fim antes do inicio nao faz sentido
verificar(any("nao e maior que inicio" in e for e in edl_mod.validar(mau)),
          "apanha clipe com fim antes do inicio")

mau = edl_exemplo()
mau["duracao_final_s"] = 99.0
verificar(any("nao bate" in e for e in edl_mod.validar(mau)),
          "apanha duracao declarada que nao bate com a soma dos clipes")

mau = edl_exemplo()
mau["clipes"][1].pop("motivo")
verificar(any("sem motivo" in e for e in edl_mod.validar(mau)),
          "exige motivo em todo corte")

mau = edl_exemplo()
mau["enfases"][0]["texto"] = "com " + chr(0x2014) + " traco"
verificar(any("traco longo" in e for e in edl_mod.validar(mau)),
          "apanha traco longo na copy")

mau = edl_exemplo()
mau["formato"] = {"largura": 1920, "altura": 1080}
verificar(any("nao e vertical" in e for e in edl_mod.validar(mau)),
          "recusa formato horizontal")

mau = edl_exemplo()
verificar(any("passa a duracao da fonte" in e for e in edl_mod.validar(mau, duracao_fonte=40.0)),
          "apanha clipe que passa do fim do ficheiro de origem")

vazio = edl_exemplo()
vazio["clipes"] = []
verificar(any("nenhum clipe" in e for e in edl_mod.validar(vazio)),
          "recusa EDL sem clipes")


print("\nEDL: estatisticas\n")

e = edl_exemplo()
stats = edl_mod.estatisticas(e)
verificar(stats["n_clipes"] == 3, "conta os clipes")
verificar(abs(stats["duracao_final_s"] - 9.0) < 0.001,
          "soma a duracao certa", f"deu {stats['duracao_final_s']}")
verificar(abs(stats["plano_mediano_s"] - 3.0) < 0.001,
          "plano mediano certo", f"deu {stats['plano_mediano_s']}")


print("\nLegendas: conversao do tempo do bruto para o montado\n")

e = edl_exemplo()
t = transcricao_exemplo()
saida = legendas.gerar(e, t, por_grupo=1)

verificar(len(saida) > 0, "produz legendas")
verificar(abs(saida[0]["inicio"]) < 0.001,
          "a primeira legenda comeca no segundo zero", f"deu {saida[0]['inicio']}")
verificar(saida[0]["texto"] == "o",
          "a primeira legenda e a primeira palavra do hook, nao a do bruto",
          f"deu '{saida[0]['texto']}'")

tempos = [l["inicio"] for l in saida]
verificar(tempos == sorted(tempos),
          "as legendas saem por ordem crescente de tempo", str(tempos))

textos = [l["texto"] for l in saida]
verificar("isto" not in textos and "sai" not in textos,
          "as palavras cortadas fora nao aparecem", str(textos))

verificar(all(l["fim"] > l["inicio"] for l in saida),
          "nenhuma legenda tem duracao zero ou negativa")

for a, b in zip(saida, saida[1:]):
    if a["fim"] > b["inicio"] + 0.001:
        break
else:
    verificar(True, "nenhuma legenda se sobrepoe a seguinte")

ultimo = max(l["fim"] for l in saida)
verificar(ultimo <= 9.0 + 0.1,
          "nenhuma legenda passa do fim do video montado", f"maior fim: {ultimo}")

# Regressao: com palavras muito coladas, o corte que evita sobreposicao chegava a
# deixar o fim antes do inicio e o grupo era deitado fora, perdendo a palavra.
coladas = {
    "duracao_s": 10.0,
    "palavras": [
        {"palavra": "uma", "inicio": 1.00, "fim": 1.40, "confianca": 0.9},
        {"palavra": "duas", "inicio": 1.02, "fim": 1.45, "confianca": 0.9},
        {"palavra": "tres", "inicio": 1.03, "fim": 1.50, "confianca": 0.9},
        {"palavra": "quatro", "inicio": 1.04, "fim": 1.60, "confianca": 0.9},
    ],
    "segmentos": [],
}
simples = {
    "fonte": "v.mp4", "formato": {"largura": 1080, "altura": 1920},
    "clipes": [{"inicio": 0.0, "fim": 5.0, "motivo": "tudo"}],
    "legendas": [], "enfases": [], "fixos": [], "audio": {},
}
r = legendas.gerar(simples, coladas, por_grupo=1)
escritas = [p for l in r for p in l["texto"].split()]
verificar(len(escritas) == 4,
          "nenhuma palavra se perde quando a fala vem muito colada",
          f"escreveu {escritas}")

# Regressao real: o whisper devolve, de vez em quando, uma palavra com inicio
# igual ao fim. Isso descartava a palavra e deixava fala sem legenda no ecra.
duracao_zero = {
    "duracao_s": 10.0,
    "palavras": [
        {"palavra": "antes", "inicio": 1.0, "fim": 1.4, "confianca": 0.9},
        {"palavra": "uma", "inicio": 2.0, "fim": 2.0, "confianca": 0.9},
        {"palavra": "depois", "inicio": 3.0, "fim": 3.4, "confianca": 0.9},
    ],
    "segmentos": [],
}
r = legendas.gerar(simples, duracao_zero, por_grupo=1)
escritas = [p for l in r for p in l["texto"].split()]
verificar("uma" in escritas,
          "palavra com duracao zero na transcricao continua a receber legenda",
          f"escreveu {escritas}")
verificar(all(l["fim"] > l["inicio"] for l in r),
          "mesmo coladas, nenhuma legenda fica com duracao nao positiva")


print("\nDeteccao de candidatos\n")

t = {
    "ficheiro": "x.mp4",
    "duracao_s": 20.0,
    "palavras": [
        {"palavra": "entao", "inicio": 1.0, "fim": 1.3, "confianca": 0.9},
        {"palavra": "vamos", "inicio": 1.3, "fim": 1.7, "confianca": 0.95},
        {"palavra": "la", "inicio": 3.0, "fim": 3.3, "confianca": 0.2},
    ],
    "segmentos": [
        {"inicio": 0.0, "fim": 2.0, "texto": "entao vamos falar sobre isto agora"},
        {"inicio": 5.0, "fim": 7.0, "texto": "entao vamos falar sobre isto agora"},
    ],
}
r = detect.analisar(t)
tipos = {c["tipo"] for c in r["candidatos"]}
verificar("muleta" in tipos, "apanha muleta de fala")
verificar("silencio" in tipos, "apanha silencio entre palavras")
verificar("baixa_confianca" in tipos, "apanha palavra de baixa confianca do ASR")
verificar("take_repetido" in tipos, "apanha take repetido")

repetido = next(c for c in r["candidatos"] if c["tipo"] == "take_repetido")
verificar(repetido["inicio"] == 0.0,
          "no take repetido marca a primeira versao, nao a ultima",
          f"marcou aos {repetido['inicio']}s")


print("\nCapCut: nomes dos parametros\n")

e = edl_exemplo()
manifesto = {
    "clipes": [
        {"indice": 0, "ficheiro": "/tmp/c0.mp4", "duracao": 3.0, "inicio_no_bruto": 30.0, "motivo": "hook"},
        {"indice": 1, "ficheiro": "/tmp/c1.mp4", "duracao": 4.0, "inicio_no_bruto": 10.0, "motivo": "prova"},
        {"indice": 2, "ficheiro": "/tmp/c2.mp4", "duracao": 2.0, "inicio_no_bruto": 50.0, "motivo": "fecho"},
    ]
}
plano = capcut_build.construir(e, manifesto)
por_ferramenta = {}
for c in plano["chamadas"]:
    por_ferramenta.setdefault(c["ferramenta"], []).append(c)

verificar(plano["chamadas"][0]["ferramenta"] == "create_draft",
          "o plano comeca por criar o rascunho")
verificar(plano["chamadas"][-1]["ferramenta"] == "save_draft",
          "o plano acaba por gravar o rascunho")

video = por_ferramenta["add_video"][0]["argumentos"]
verificar("end" in video and "duration" not in video,
          "add_video usa 'end' e nao 'duration'", str(sorted(video)))
verificar("video_url" in video, "add_video usa 'video_url'")

texto = por_ferramenta["add_text"][0]["argumentos"]
verificar("font_size" in texto and "font_color" in texto,
          "add_text usa 'font_size' e 'font_color'", str(sorted(texto)))
verificar("cor" not in texto and "tamanho_px" not in texto,
          "add_text nao leva nomes inventados em portugues")

kf = por_ferramenta["add_video_keyframe"][0]["argumentos"]
verificar(isinstance(kf.get("property_types"), list)
          and isinstance(kf.get("times"), list)
          and isinstance(kf.get("values"), list),
          "add_video_keyframe usa tres listas paralelas")
verificar(len(kf["times"]) == len(kf["values"]),
          "times e values tem o mesmo comprimento")
verificar(all(isinstance(v, str) for v in kf["values"]),
          "os valores do keyframe vao em texto, como na documentacao")

verificar(plano["chamadas_com_campos_incertos"] > 0,
          "os campos nao documentados sao marcados como incertos em vez de adivinhados")

soma = sum(c["duracao"] for c in manifesto["clipes"])
verificar(abs(plano["duracao_final_s"] - soma) < 0.001,
          "a duracao final bate com a soma dos clipes")

videos = por_ferramenta["add_video"]
fins = [v["argumentos"]["end"] for v in videos]
inicios = [v["argumentos"]["start"] for v in videos]
verificar(inicios[0] == 0 and all(abs(f - i) < 0.001 for f, i in zip(fins, inicios[1:])),
          "os clipes ficam encostados, sem buracos nem sobreposicao",
          f"inicios {inicios} fins {fins}")


print("\nZoom: limite\n")

e = edl_exemplo()
e["clipes"][0]["zoom"] = 3.0  # exagero de proposito
plano = capcut_build.construir(e, manifesto)
kf = next(c for c in plano["chamadas"] if c["ferramenta"] == "add_video_keyframe")
verificar(float(kf["argumentos"]["values"][-1]) <= capcut_build.ZOOM_MAX + 0.001,
          "o zoom e limitado ao maximo, mesmo que o EDL peca mais",
          f"deu {kf['argumentos']['values'][-1]}")


print(f"\n{'=' * 50}")
if falhas:
    print(f"{passou} passaram, {len(falhas)} FALHARAM:")
    for f in falhas:
        print(f"  - {f}")
    sys.exit(1)
print(f"{passou} testes passaram.")
