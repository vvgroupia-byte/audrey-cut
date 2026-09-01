#!/usr/bin/env bash
# Instalador do Audrey Cut. Deixa a maquina pronta para editar video com o squad.
# Pode correr as vezes que forem precisas: o que ja esta instalado e saltado.
set -uo pipefail

AZUL='\033[1;34m'; VERDE='\033[1;32m'; AMARELO='\033[1;33m'; VERM='\033[1;31m'; OFF='\033[0m'
passo() { echo -e "\n${AZUL}==> $1${OFF}"; }
ok()    { echo -e "${VERDE}  OK${OFF} $1"; }
aviso() { echo -e "${AMARELO}  ATENCAO${OFF} $1"; }
erro()  { echo -e "${VERM}  ERRO${OFF} $1"; }

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"
export PATH="$BIN:$PATH"
FALHAS=0

echo -e "${AZUL}"
echo "  Audrey Cut, instalacao"
echo "  Edicao de video com squad, saida direta para o CapCut"
echo -e "${OFF}"

# ---------------------------------------------------------------- 1. sistema
passo "1/7  A verificar o sistema"
SO="$(uname -s)"
if [ "$SO" != "Darwin" ]; then
  erro "Este instalador so foi feito e testado em Mac."
  echo "  O motor em si e multiplataforma (Python e ffmpeg), mas os caminhos do"
  echo "  CapCut no Windows sao outros e nada disso foi testado la."
  echo "  Fala com o Kaiky antes de continuar."
  exit 1
fi
ok "macOS $(sw_vers -productVersion), $(uname -m)"
mkdir -p "$BIN"

# ---------------------------------------------------------------- 2. uv
passo "2/7  Python isolado (uv)"
if command -v uv >/dev/null 2>&1; then
  ok "uv ja instalado ($(uv --version))"
else
  echo "  a instalar uv..."
  if curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; then
    ok "uv instalado"
  else
    erro "nao consegui instalar o uv. Verifica a ligacao a internet."
    exit 1
  fi
fi

passo "3/7  Ambiente Python 3.11"
uv python install 3.11 >/dev/null 2>&1
if uv venv --python 3.11 "$RAIZ/.venv" >/dev/null 2>&1 || [ -d "$RAIZ/.venv" ]; then
  ok "ambiente criado em .venv"
else
  erro "falhou a criacao do ambiente Python"
  exit 1
fi
echo "  a instalar bibliotecas (pode demorar alguns minutos)..."
if uv pip install --python "$RAIZ/.venv/bin/python" -r "$RAIZ/requirements.txt" >/dev/null 2>&1; then
  ok "bibliotecas instaladas"
else
  erro "falhou a instalacao das bibliotecas"
  exit 1
fi

# ---------------------------------------------------------------- 4. ffmpeg
passo "4/7  ffmpeg (corta e trata o video)"
if command -v ffmpeg >/dev/null 2>&1; then
  ok "ffmpeg ja instalado ($(ffmpeg -version 2>/dev/null | head -1 | cut -d' ' -f3))"
elif command -v brew >/dev/null 2>&1; then
  echo "  a instalar via Homebrew..."
  brew install ffmpeg >/dev/null 2>&1 && ok "ffmpeg instalado" || { erro "falhou"; FALHAS=1; }
else
  aviso "ffmpeg nao encontrado e nao ha Homebrew nesta maquina."
  echo "  O motor usa o PyAV como alternativa para ler os videos, mas o corte"
  echo "  final precisa mesmo do ffmpeg. Instala o Homebrew e corre outra vez:"
  echo "    /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  FALHAS=1
fi

# ---------------------------------------------------------------- 5. squad
passo "5/7  Squad de edicao"
DESTINO="$HOME/.claude/commands/audrey-cut"
mkdir -p "$DESTINO"
if cp -R "$RAIZ/squad/." "$DESTINO/" 2>/dev/null; then
  ok "squad instalado em ~/.claude/commands/audrey-cut"
else
  erro "nao consegui copiar o squad"
  FALHAS=1
fi

# O comando tem de ficar na raiz dos comandos, se nao o Claude Code chama-lhe
# /audrey-cut:editar, que ninguem se lembra. Na raiz, e so /editar.
if cp "$RAIZ/squad/editar.md" "$HOME/.claude/commands/editar.md" 2>/dev/null; then
  ok "comando /editar disponivel"
else
  erro "nao consegui instalar o comando /editar"
  FALHAS=1
fi

# O motor vive na pasta do projeto, mas o comando precisa de saber onde ela esta.
echo "$RAIZ" > "$DESTINO/CAMINHO-DO-MOTOR.txt"

# Pastas de trabalho, na Secretaria para ela encontrar sem procurar.
TRABALHO="$HOME/Desktop/Audrey Cut"
mkdir -p "$TRABALHO/1-videos-brutos" "$TRABALHO/2-prontos"
ok "pastas criadas na Secretaria: 'Audrey Cut'"

# ---------------------------------------------------------------- 6. CapCut
passo "6/7  Ligacao ao CapCut"
if [ -d "/Applications/CapCut.app" ]; then
  ok "CapCut encontrado"
else
  aviso "o CapCut nao esta instalado nesta maquina."
  echo "  Descarrega em https://www.capcut.com/pt-br/ e corre este instalador outra vez."
  FALHAS=1
fi

DRAFTS="$HOME/Movies/CapCut/User Data/Projects/com.lveditor.draft"
if [ -d "$DRAFTS" ]; then
  ok "pasta de projetos do CapCut encontrada"
else
  aviso "ainda nao ha pasta de projetos do CapCut."
  echo "  Abre o CapCut uma vez, cria um projeto qualquer, e corre isto outra vez."
  FALHAS=1
fi

passo "7/7  Auto-teste do motor"
if "$RAIZ/.venv/bin/python" "$RAIZ/tests/test_motor.py" >/dev/null 2>&1; then
  ok "os testes do motor passam"
else
  erro "os testes do motor falham. Nao uses isto antes de resolver:"
  "$RAIZ/.venv/bin/python" "$RAIZ/tests/test_motor.py" 2>&1 | grep -A2 FALHA | head -20
  FALHAS=1
fi

cat > "$RAIZ/config.json" <<EOF
{
  "raiz": "$RAIZ",
  "python": "$RAIZ/.venv/bin/python",
  "pasta_trabalho": "$TRABALHO",
  "drafts_capcut": "$DRAFTS",
  "instalado_em": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
ok "configuracao gravada"

echo
if [ "$FALHAS" -eq 0 ]; then
  echo -e "${VERDE}Tudo pronto.${OFF}"
else
  echo -e "${AMARELO}Instalado, mas com pendencias acima.${OFF}"
fi
cat <<'EOF'

Como usar:
  1. Poe o video na pasta  Secretaria > Audrey Cut > 1-videos-brutos
  2. Abre o Claude Code e escreve:  /editar
  3. Quando terminar, abre o CapCut: o projeto ja la esta montado.

EOF
