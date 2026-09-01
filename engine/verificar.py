#!/usr/bin/env python3
"""Verifica se a maquina esta mesmo pronta para editar. Item a item, sem fingir.

Uso:
    python verificar.py

Devolve codigo 0 se estiver tudo bem, 1 se faltar alguma coisa essencial.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VERDE, VERM, AMAR, OFF = "\033[1;32m", "\033[1;31m", "\033[1;33m", "\033[0m"

essenciais_em_falta = []
avisos = []


def resultado(nome: str, passou: bool, detalhe: str = "", essencial: bool = True):
    if passou:
        print(f"  {VERDE}OK{OFF}      {nome}" + (f"  ({detalhe})" if detalhe else ""))
    elif essencial:
        print(f"  {VERM}FALTA{OFF}   {nome}" + (f"  {detalhe}" if detalhe else ""))
        essenciais_em_falta.append(nome)
    else:
        print(f"  {AMAR}ATENCAO{OFF} {nome}" + (f"  {detalhe}" if detalhe else ""))
        avisos.append(nome)


def verificar_python():
    v = sys.version_info
    resultado("Python 3.11+", v >= (3, 11), f"{v.major}.{v.minor}.{v.micro}")


def verificar_bibliotecas():
    for modulo, nome in (("av", "PyAV"), ("faster_whisper", "faster-whisper")):
        try:
            __import__(modulo)
            resultado(nome, True)
        except ImportError:
            resultado(nome, False, "corre o install.sh outra vez")


def verificar_ffmpeg():
    caminho = shutil.which("ffmpeg")
    if not caminho:
        resultado("ffmpeg", False, "sem ffmpeg nao ha corte. Instala com: brew install ffmpeg")
        return
    r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    versao = r.stdout.split("\n")[0].split(" ")[2] if r.returncode == 0 else "?"
    resultado("ffmpeg", True, versao)


def verificar_motor():
    for f in ("probe.py", "transcribe.py", "detect.py", "edl.py", "legendas.py",
              "render.py", "previa.py", "capcut_exec.py"):
        resultado(f"motor: {f}", (RAIZ / "engine" / f).exists())


def verificar_squad():
    destino = Path.home() / ".claude" / "commands" / "audrey-cut"
    resultado("squad instalado", (destino / "squad.yaml").exists(), str(destino))
    resultado("estilo medido", (destino / "ESTILO-MEDIDO.md").exists(),
              "sem isto o squad decide por achismo")


def verificar_pastas():
    cfg = RAIZ / "config.json"
    if not cfg.exists():
        resultado("config.json", False, "corre o install.sh")
        return
    dados = json.loads(cfg.read_text())
    trabalho = Path(dados.get("pasta_trabalho", ""))
    resultado("pasta de videos brutos", (trabalho / "1-videos-brutos").is_dir(), str(trabalho))


def verificar_capcut():
    app = Path("/Applications/CapCut.app")
    resultado("CapCut instalado", app.exists(),
              "descarrega em capcut.com e abre uma vez" if not app.exists() else "")

    drafts = Path.home() / "Movies" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
    resultado("pasta de projetos do CapCut", drafts.is_dir(),
              "abre o CapCut e cria um projeto vazio" if not drafts.is_dir() else "",
              essencial=False)


def porta_do_servidor():
    """Le a porta real gravada pelo instalador. Sem ficheiro, assume a 9077."""
    ficheiro = Path.home() / ".audrey-cut" / "porta.txt"
    try:
        return int(ficheiro.read_text().strip())
    except (OSError, ValueError):
        return 9077


def verificar_servidor_mcp():
    porta = porta_do_servidor()
    url = f"http://127.0.0.1:{porta}/docs"
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            responde = r.status == 200
    except (urllib.error.URLError, OSError):
        responde = False
    resultado("servidor MCP a responder", responde,
              f"porta {porta}" if responde else f"nada em {url}, corre mcp/instalar-servidor.sh",
              essencial=False)


def verificar_launchd_mcp():
    plist = Path.home() / "Library" / "LaunchAgents" / "com.audreycut.mcp.plist"
    resultado("servico launchd (plist)", plist.exists(),
              "" if plist.exists() else "corre mcp/instalar-servidor.sh",
              essencial=False)
    try:
        r = subprocess.run(
            ["launchctl", "print", f"gui/{os.getuid()}/com.audreycut.mcp"],
            capture_output=True, text=True)
        carregado = r.returncode == 0
    except OSError:
        carregado = False
    resultado("servico launchd carregado", carregado,
              "" if carregado else "o servidor nao arranca sozinho, corre mcp/instalar-servidor.sh",
              essencial=False)


def verificar_mcp():
    porta = porta_do_servidor()
    try:
        r = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True)
    except OSError:
        resultado("MCP do CapCut", False, "nao consegui correr 'claude mcp list'", essencial=False)
        return
    if r.returncode != 0:
        resultado("MCP do CapCut", False, "nao consegui correr 'claude mcp list'", essencial=False)
        return
    ligado = False
    for linha in r.stdout.splitlines():
        if "capcut" in linha.lower() and "connected" in linha.lower():
            ligado = True
            break
    resultado("MCP do CapCut", ligado,
              f"porta {porta}" if ligado else
              "sem isto o corte fica pronto mas nao entra sozinho no CapCut",
              essencial=False)


def main():
    print("\nAudrey Cut, verificacao\n")
    print(" Base")
    verificar_python()
    verificar_bibliotecas()
    verificar_ffmpeg()
    print("\n Motor")
    verificar_motor()
    print("\n Squad")
    verificar_squad()
    print("\n Pastas")
    verificar_pastas()
    print("\n CapCut")
    verificar_capcut()
    verificar_servidor_mcp()
    verificar_launchd_mcp()
    verificar_mcp()

    print()
    if essenciais_em_falta:
        n = len(essenciais_em_falta)
        print(f"{VERM}Falta{'m' if n > 1 else ''} {n} coisa{'s' if n > 1 else ''} essencia{'is' if n > 1 else 'l'}:{OFF}")
        for item in essenciais_em_falta:
            print(f"  - {item}")
        sys.exit(1)

    if avisos:
        print(f"{AMAR}Pronto para cortar, mas com {len(avisos)} pendencia(s):{OFF}")
        for item in avisos:
            print(f"  - {item}")
        print("\nO corte funciona. So a entrega automatica no CapCut e que fica de fora.")
        sys.exit(0)

    print(f"{VERDE}Tudo pronto.{OFF}\n")


if __name__ == "__main__":
    main()
