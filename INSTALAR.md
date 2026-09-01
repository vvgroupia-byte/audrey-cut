# Audrey Cut, instalacao

**Audrey: nao precisas de fazer nada aqui a nao ser abrir o Claude Code e
escrever isto:**

```
clona https://github.com/vvgroupia-byte/audrey-cut e instala pra mim
```

Se ja tens a pasta no computador, abre o Claude Code nela e escreve so
**instala isso pra mim**.

O resto e com ele. Quando acabar, ele diz o que fazer a seguir.

Se alguma coisa correr mal, manda print do erro ao Kaiky.

> Nota: o repositorio e privado. Se der erro de acesso, e porque a tua conta do
> GitHub ainda nao foi convidada. Pede ao Kaiky.

---

## Daqui para baixo e instrucao para o Claude Code

Nao mostres estes passos a utilizadora. Executa-os e no fim da um resumo curto do
que ficou pronto e do que falta.

### Contexto

Isto instala o **Audrey Cut**, um sistema que pega num video gravado em bruto e
devolve um projeto ja montado no CapCut: cortes feitos, legendas sincronizadas,
enfases na tela e audio normalizado. Quem usa nao sabe usar terminal, por isso
nada pode exigir que ela escreva comandos.

### Passo 1: correr o instalador

```bash
cd "<pasta deste ficheiro>"
chmod +x install.sh
./install.sh
```

O script e idempotente: podes corre-lo outra vez sem estragar nada. Ele instala o
`uv`, cria o ambiente Python 3.11, instala as bibliotecas, copia o squad para
`~/.claude/commands/audrey-cut/`, cria as pastas de trabalho na Secretaria e
escreve o `config.json`.

Le o que ele imprime. Se avisar que falta o ffmpeg, o CapCut ou a pasta de
projetos do CapCut, resolve isso antes de continuar (ver Passo 3).

### Passo 2: instalar o MCP do CapCut

O CapCut nao tem API oficial. O que existe sao servidores da comunidade que
escrevem o ficheiro de projeto diretamente na pasta do app. Usa este, que corre
tudo localmente e nao faz chamadas para fora:

```bash
git clone https://github.com/Rajbagus/rabbitorial-capcut-mcp.git ~/.audrey-cut-mcp
cd ~/.audrey-cut-mcp
uv python install 3.11
uv run --python 3.11 install.py
```

**Nao uses `python3 install.py`.** O Python do sistema no macOS costuma ser o 3.9,
e este servidor exige 3.10 ou superior. Com `uv run` garante-se a versao certa sem
mexer no Python do sistema.

O `install.py` do projeto cria o ambiente dele, encontra a pasta de projetos do
CapCut e regista-se sozinho no Claude Code. Confirma no fim com:

```bash
claude mcp list
```

Tem de aparecer uma linha do CapCut com estado ligado. Se nao aparecer, regista a
mao seguindo o README desse repositorio.

### Passo 2b: confirmar os nomes reais dos parametros

Depois de o MCP estar ligado, **le o schema real das ferramentas** `add_video`,
`add_text` e `add_video_keyframe` e compara com o que esta em
`engine/capcut_build.py`, na seccao "Sobre os nomes dos parametros".

Os nomes que la estao vieram da documentacao publica do VectCutAPI, que e o
upstream, e nao de uma execucao real. Tres campos ficaram por confirmar e saem
marcados como `campos_incertos` no plano gerado:

- o sistema de coordenadas de `transform_x` e `transform_y` (pixel ou -1 a 1)
- se `add_video` e `add_text` aceitam `track_name`
- a unidade de `font_size`

Se algum nome divergir, corrige no `capcut_build.py` e corre `tests/test_motor.py`
outra vez. Nao adivinhes: uma chamada com nome errado falha em silencio ou monta
o texto no sitio errado.

**Diz claramente a utilizadora que este servidor e comunitario e nao oficial:**
quando a CapCut atualizar o formato do projeto, ele pode deixar de funcionar. Se
isso acontecer, o trabalho do squad nao se perde, porque fica todo no `EDL.json`
e pode ser montado a mao ou exportado para outro editor.

### Passo 3: pre-requisitos que podem faltar

| Falta | O que fazer |
| --- | --- |
| **ffmpeg** | Se houver Homebrew: `brew install ffmpeg`. Se nao houver, instala primeiro o Homebrew |
| **CapCut** | Descarregar em https://www.capcut.com/pt-br/ , instalar, e **abrir uma vez** |
| **Pasta de projetos do CapCut** | So existe depois de ela criar um projeto qualquer no app. Pede-lhe para abrir o CapCut e criar um projeto vazio, depois corre `./install.sh` outra vez |

O CapCut tem de ser aberto pelo menos uma vez antes de o sistema conseguir
escrever nele. Nao saltes este passo.

### Passo 4: verificar que ficou tudo bem

Corre esta verificacao e mostra o resultado:

```bash
cd "<pasta deste ficheiro>"
.venv/bin/python tests/test_motor.py
.venv/bin/python engine/verificar.py
```

O primeiro comando testa a aritmetica do motor: conversao de tempos depois de
reordenar clipes, validacao do EDL e os nomes dos parametros do CapCut. Tem de
dizer que todos passaram.

O segundo diz o que falta na maquina. Se algum item falhar, resolve antes de dizer
que esta pronto.

### Passo 5: o que dizer a utilizadora no fim

Em portugues do Brasil, curto, sem jargao. Algo assim:

> Prontinho. Pra editar um video:
>
> 1. Poe o video na pasta **Audrey Cut > 1-videos-brutos** (ta na tua Area de Trabalho)
> 2. Aqui no Claude Code, escreve **/editar**
> 3. Espera. Ele transcreve, decide os cortes e monta tudo
> 4. Abre o CapCut: o projeto ja ta la, montado. So revisar e exportar
>
> A primeira vez demora mais, porque ele baixa o modelo de transcricao (uns 3 GB).

Se ficou alguma pendencia, di-la nesta mesma mensagem, com o que ela precisa de
fazer para resolver.

### Regras que valem para sempre neste projeto

- O conteudo e **sempre da marca da Audrey**. Nunca menciones VV Group nem
  qualquer agencia dentro de um video.
- Nunca uses traco longo em legenda ou copy.
- Nenhum numero de estilo e inventado: sai do `squad/ESTILO-MEDIDO.md`, que foi
  medido nos videos de referencia reais.
