#!/usr/bin/env bash
# Instala o servidor CapCut MCP como servico do macOS (launchd).
# Depois disto, o servidor liga sozinho quando a maquina liga. Sem terminal aberto.
# Pode correr as vezes que forem precisas: reinstala por cima sem estragar nada.
set -uo pipefail

AZUL='\033[1;34m'; VERDE='\033[1;32m'; AMARELO='\033[1;33m'; VERM='\033[1;31m'; OFF='\033[0m'
passo() { echo -e "\n${AZUL}==> $1${OFF}"; }
ok()    { echo -e "${VERDE}  OK${OFF} $1"; }
aviso() { echo -e "${AMARELO}  ATENCAO${OFF} $1"; }
erro()  { echo -e "${VERM}  ERRO${OFF} $1"; }

BASE="$HOME/.audrey-cut"
SERVIDOR="$BASE/capcut-mcp"
LOGS="$BASE/logs"
PLIST="$HOME/Library/LaunchAgents/com.audreycut.mcp.plist"
ROTULO="com.audreycut.mcp"
GUI="gui/$(id -u)"

UV="$HOME/.local/bin/uv"
if ! [ -x "$UV" ] && command -v uv >/dev/null 2>&1; then
  UV="$(command -v uv)"
fi
if ! [ -x "$UV" ]; then
  erro "uv nao encontrado. Corre primeiro o install.sh do Audrey Cut."
  exit 1
fi

mkdir -p "$BASE" "$LOGS" "$HOME/Library/LaunchAgents"

passo "Servidor CapCut MCP (entrega automatica no CapCut)"

# ------------------------------------------------- 1. parar servico anterior
# Se ja havia um servico nosso a correr, paramos antes de mexer (idempotencia).
if launchctl print "$GUI/$ROTULO" >/dev/null 2>&1; then
  launchctl bootout "$GUI/$ROTULO" >/dev/null 2>&1
  sleep 2
  ok "servico anterior parado para reinstalar por cima"
fi

# ------------------------------------------------- 2. descarregar o servidor
if [ -f "$SERVIDOR/main.py" ]; then
  ok "servidor ja descarregado em $SERVIDOR"
else
  echo "  a descarregar o servidor capcut-mcp..."
  if git clone --depth 1 https://github.com/fancyboi999/capcut-mcp.git "$SERVIDOR" >/dev/null 2>&1; then
    ok "servidor descarregado"
  else
    erro "nao consegui descarregar o capcut-mcp. Verifica a ligacao a internet."
    exit 1
  fi
fi

# ------------------------------------------------- 3. ambiente Python 3.12
if [ -x "$SERVIDOR/.venv/bin/python" ]; then
  ok "ambiente Python do servidor ja existe"
else
  echo "  a preparar Python 3.12 do servidor..."
  if "$UV" venv -p 3.12 "$SERVIDOR/.venv" >/dev/null 2>&1; then
    ok "ambiente Python 3.12 criado"
  else
    erro "falhou a criacao do ambiente Python do servidor"
    exit 1
  fi
fi
echo "  a instalar bibliotecas do servidor (pode demorar uns minutos)..."
if "$UV" pip install --python "$SERVIDOR/.venv/bin/python" -r "$SERVIDOR/requirements.txt" "mcp==1.13.1" >/dev/null 2>&1; then
  ok "bibliotecas do servidor instaladas"
else
  erro "falhou a instalacao das bibliotecas do servidor"
  exit 1
fi

# ------------------------------------------------- 4. escolher a porta
porta_livre() { ! lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

PORTA=9077
if ! porta_livre "$PORTA"; then
  aviso "a porta 9077 esta ocupada por outro programa, a procurar outra"
  PORTA=""
  for p in $(seq 9078 9099); do
    if porta_livre "$p"; then PORTA="$p"; break; fi
  done
  if [ -z "$PORTA" ]; then
    erro "nao encontrei nenhuma porta livre entre 9077 e 9099"
    exit 1
  fi
fi
echo "$PORTA" > "$BASE/porta.txt"
ok "porta escolhida: $PORTA (guardada em $BASE/porta.txt)"

# ------------------------------------------------- 5. config.json do servidor
if [ ! -f "$SERVIDOR/config.json" ]; then
  cp "$SERVIDOR/config.json.example" "$SERVIDOR/config.json"
fi
"$SERVIDOR/.venv/bin/python" - "$SERVIDOR/config.json" "$PORTA" <<'PY'
import json
import sys

caminho, porta = sys.argv[1], int(sys.argv[2])
with open(caminho, encoding="utf-8") as f:
    cfg = json.load(f)
cfg["port"] = porta
# Privacidade: nunca subir material da Audrey para nenhuma nuvem.
cfg["is_upload_draft"] = False
with open(caminho, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
if [ $? -eq 0 ]; then
  ok "config.json afinado (porta $PORTA, nada sobe para a nuvem)"
else
  erro "nao consegui editar o config.json do servidor"
  exit 1
fi

# ------------------------------------------------- 6. servico launchd
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$ROTULO</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SERVIDOR/.venv/bin/python</string>
        <string>main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SERVIDOR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOGS/mcp.log</string>
    <key>StandardErrorPath</key>
    <string>$LOGS/mcp.log</string>
</dict>
</plist>
EOF
ok "servico gravado em $PLIST"

if launchctl bootstrap "$GUI" "$PLIST" >/dev/null 2>&1; then
  ok "servico ligado (launchctl bootstrap)"
elif launchctl load -w "$PLIST" >/dev/null 2>&1; then
  ok "servico ligado (launchctl load)"
else
  erro "nao consegui ligar o servico no launchd"
  exit 1
fi

# ------------------------------------------------- 7. esperar pelo servidor
echo "  a esperar o servidor responder (ate 30 segundos)..."
RESPONDEU=0
for _ in $(seq 1 30); do
  CODIGO="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:$PORTA/docs" 2>/dev/null)"
  if [ "$CODIGO" = "200" ]; then RESPONDEU=1; break; fi
  sleep 1
done
if [ "$RESPONDEU" -eq 1 ]; then
  ok "servidor a responder em http://127.0.0.1:$PORTA"
else
  erro "o servidor nao respondeu em 30 segundos. Ve o log em $LOGS/mcp.log"
  exit 1
fi

# ------------------------------------------------- 8. registar no Claude Code
if ! command -v claude >/dev/null 2>&1; then
  erro "o comando 'claude' nao esta disponivel. Instala o Claude Code e corre isto outra vez."
  exit 1
fi
# Remover registos antigos primeiro (idempotencia); erros aqui nao interessam.
claude mcp remove --scope user capcut >/dev/null 2>&1
claude mcp remove capcut >/dev/null 2>&1
if claude mcp add --transport sse --scope user capcut "http://127.0.0.1:$PORTA/mcp" >/dev/null 2>&1; then
  ok "registado no Claude Code (capcut, para qualquer pasta)"
else
  erro "falhou o registo no Claude Code"
  exit 1
fi

echo "  a confirmar a ligacao..."
LISTA="$(claude mcp list 2>/dev/null)"
if echo "$LISTA" | grep -i "capcut" | grep -q "Connected"; then
  ok "Claude Code confirma: capcut Connected"
else
  aviso "o Claude Code ainda nao confirma a ligacao. Detalhe:"
  echo "$LISTA" | grep -i "capcut" || echo "  (capcut nao aparece na lista)"
  exit 1
fi

echo
echo -e "${VERDE}Servidor CapCut MCP pronto.${OFF} Liga sozinho sempre que a maquina arranca."
