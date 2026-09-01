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

### Passo 2: instalar o servidor do CapCut

O CapCut nao tem API oficial. O que existe e um servidor da comunidade
(`fancyboi999/capcut-mcp`) que escreve o ficheiro de projeto do CapCut. O
`install.sh` do passo 1 ja chama o instalador dele, mas se precisares de o correr
ou reparar em separado:

```bash
./mcp/instalar-servidor.sh
```

Esse script faz tudo: clona o servidor para `~/.audrey-cut/capcut-mcp`, cria o
ambiente Python 3.12 isolado com a versao exata do SDK que funciona
(`mcp==1.13.1`), escolhe uma porta livre (9077, com fallback ate 9099), instala
um servico do sistema (launchd) para o servidor **ligar sozinho no login e reviver
se cair**, e regista no Claude Code com:

```
claude mcp add --transport sse --scope user capcut http://127.0.0.1:PORTA/mcp
```

O `--scope user` importa: sem ele o registo fica preso a pasta onde correu.

Confirma no fim com `claude mcp list`: a linha do capcut tem de terminar em
**Connected**. Se disser Failed, o servidor nao esta a correr ou a porta diverge;
corre o `instalar-servidor.sh` outra vez, ele e idempotente.

Privacidade: o `config.json` do servidor fica com `is_upload_draft: false`. O
material dela nunca sai do computador.

Nota tecnica: a montagem quente do `/editar` nem usa o MCP, usa a API REST do
mesmo servidor via `engine/capcut_exec.py`, que e deterministico e testado. O
registo MCP serve para conversar com o CapCut fora do fluxo (por exemplo,
"acrescenta um texto ao draft X").

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
