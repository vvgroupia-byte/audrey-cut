#!/usr/bin/env bash
# Desinstala o Audrey Cut: para o servidor, remove o servico e limpa os comandos.
# Use --sim para pular a pergunta de confirmacao.
set -uo pipefail

AZUL='\033[1;34m'; VERDE='\033[1;32m'; AMARELO='\033[1;33m'; VERM='\033[1;31m'; OFF='\033[0m'
passo() { echo -e "\n${AZUL}==> $1${OFF}"; }
ok()    { echo -e "${VERDE}  OK${OFF} $1"; }
aviso() { echo -e "${AMARELO}  ATENCAO${OFF} $1"; }

BASE="$HOME/.audrey-cut"
PLIST="$HOME/Library/LaunchAgents/com.audreycut.mcp.plist"
ROTULO="com.audreycut.mcp"
GUI="gui/$(id -u)"

echo -e "${AZUL}"
echo "  Audrey Cut, desinstalacao"
echo -e "${OFF}"
echo "Isto vai remover:"
echo "  1. O servico do servidor CapCut MCP (launchd) e o ficheiro $PLIST"
echo "  2. A pasta $BASE (servidor, porta e logs)"
echo "  3. O registo 'capcut' no Claude Code"
echo "  4. O squad em ~/.claude/commands/audrey-cut e o comando ~/.claude/commands/editar.md"
echo
echo "O que NAO vai ser removido:"
echo "  - Esta pasta do projeto (o repo clonado fica intacto)"
echo "  - O aplicativo CapCut e os projetos dele"
echo "  - Os videos da Audrey (Secretaria > Audrey Cut)"
echo

if [ "${1:-}" != "--sim" ]; then
  printf "Continuar? (escreva sim para confirmar) "
  read -r RESPOSTA
  case "$RESPOSTA" in
    sim|SIM|Sim|s|S) ;;
    *) echo "Cancelado. Nada foi removido."; exit 0 ;;
  esac
fi

passo "A parar o servidor"
if launchctl print "$GUI/$ROTULO" >/dev/null 2>&1; then
  launchctl bootout "$GUI/$ROTULO" >/dev/null 2>&1
  ok "servico parado"
else
  ok "servico ja nao estava a correr"
fi
if [ -f "$PLIST" ]; then
  rm -f "$PLIST"
  ok "ficheiro do servico removido"
fi

passo "A remover a pasta $BASE"
if [ -d "$BASE" ]; then
  rm -rf "$BASE"
  ok "pasta removida"
else
  ok "pasta ja nao existia"
fi

passo "A remover o registo no Claude Code"
if command -v claude >/dev/null 2>&1; then
  claude mcp remove --scope user capcut >/dev/null 2>&1
  claude mcp remove capcut >/dev/null 2>&1
  ok "registo 'capcut' removido (se existia)"
else
  aviso "o comando 'claude' nao esta disponivel, o registo MCP fica por remover"
fi

passo "A remover o squad e o comando /editar"
rm -rf "$HOME/.claude/commands/audrey-cut"
rm -f "$HOME/.claude/commands/editar.md"
ok "comandos removidos"

echo
echo -e "${VERDE}Desinstalado.${OFF}"
echo "Ficaram intactos: o repo clonado, o CapCut e os videos da Audrey."
echo "Para instalar de novo, e so correr o install.sh outra vez."
