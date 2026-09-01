# Task: editar um video do zero

Fluxo completo, do ficheiro bruto ao projeto montado no CapCut. E este o fluxo
que o comando `/editar` executa.

## Antes de comecar

Carrega, por esta ordem:

1. `squad.yaml`
2. `ESTILO-MEDIDO.md`
3. `checklists/retencao.md`

Se o `ESTILO-MEDIDO.md` nao existir, para e diz que falta. Sem ele o squad decide
por achismo, e achismo e exatamente o que este sistema existe para evitar.

## Passo 0: encontrar o video

Procura em `~/Desktop/Audrey Cut/1-videos-brutos/`. Se houver mais do que um,
pergunta qual. Se nao houver nenhum, diz-lhe para arrastar o video para la.

Define `PROJ="$HOME/Desktop/Audrey Cut/2-prontos/<nome-do-video>"` e cria a pasta.

## Passo 1: medir e transcrever (codigo, nao julgamento)

```bash
cd <raiz do audrey-cut>
.venv/bin/python engine/probe.py "<video>" --out "$PROJ/work"
.venv/bin/python engine/transcribe.py "<video>" --out "$PROJ/work" --idioma pt
.venv/bin/python engine/detect.py "$PROJ/work/<nome>.transcricao.json" --out "$PROJ/work"
```

A transcricao e a parte lenta: conta com varios minutos por video, e bastante mais
na primeira vez, porque descarrega o modelo. Avisa-a antes de comecar, para nao
parecer que travou.

## Passo 2: o squad decide

Sempre nesta ordem. Cada um recebe o que o anterior entregou.

| Ordem | Agente | Recebe | Entrega |
| --- | --- | --- | --- |
| 1 | `hanah-franklin` | transcricao, probe | formato, hook, ordem, loop, o que sai |
| 2 | `finch-editor` | tudo acima, candidatos | lista de cortes, B-roll, zooms, audio |
| 3 | `giu-beckers` | tudo acima | legendas, enfases, texto fixo |
| 4 | `retention-qa` | o EDL proposto | aprovado, ou o que corrigir e para quem volta |

Se o `retention-qa` reprovar, volta ao agente indicado e repete. No maximo duas
voltas: se a terceira ainda reprovar, mostra a ela o que esta em conflito e
pergunta.

## Passo 3: montar o EDL

O `viral-chief` escreve `$PROJ/EDL.json` com o que os quatro decidiram. Valida:

```bash
.venv/bin/python engine/edl.py validar "$PROJ/EDL.json" --duracao-fonte <duracao>
.venv/bin/python engine/edl.py resumir "$PROJ/EDL.json"
```

Um EDL que nao valida nao avanca. Corrige e valida outra vez.

Compara o resumo com a faixa do formato escolhido. Se o plano mediano saiu fora,
ou corriges, ou escreves a justificacao no EDL.

## Passo 3b: gerar as legendas (codigo, nao julgamento)

As palavras e os tempos ja existem na transcricao. O que falta e converte-los para
o tempo do video montado, que mudou por causa dos cortes. Isso e aritmetica, nao
escrita:

```bash
.venv/bin/python engine/legendas.py "$PROJ/EDL.json" "$PROJ/work/<nome>.transcricao.json"
```

Escreve as legendas de volta no EDL e imprime a cobertura da fala, que tem de ser
alta. A `giu-beckers` nao escreve a legenda base a mao: ela decide **as enfases**,
que e onde ha julgamento.

## Passo 4: cortar

```bash
.venv/bin/python engine/render.py "$PROJ/EDL.json" --out "$PROJ/clipes"
```

Cada clipe sai cortado no frame certo, enquadrado em 1080x1920 e normalizado a
-14 LUFS.

## Passo 4b: ver o corte antes de montar

```bash
.venv/bin/python engine/previa.py "$PROJ/clipes/manifesto.json" --out "$PROJ/previa.mp4"
```

Junta os clipes num ficheiro so, sem legendas, para responder a pergunta que
importa: o ritmo ficou bom? Se a duracao nao bater com a soma dos clipes, o script
avisa e para.

Se o CapCut nao estiver disponivel, esta previa e o que ela recebe, e ainda assim
e um resultado util.

## Passo 5: montar no CapCut

```bash
.venv/bin/python engine/capcut_build.py "$PROJ/EDL.json" \
  --manifesto "$PROJ/clipes/manifesto.json" --out "$PROJ/plano-capcut.json"
```

Depois executa o plano: le `plano-capcut.json` e chama as ferramentas do MCP do
CapCut pela ordem em que la estao. O `create_draft` devolve um id: substitui-o em
todas as chamadas seguintes onde aparece `{draft_id}`.

Se o MCP do CapCut nao estiver ligado, nao inventes: diz que o corte esta pronto
em `$PROJ/clipes/` e que o plano de montagem esta no `EDL.json`, e explica que
falta ligar o MCP.

## Passo 6: contar a ela o que foi feito

Em portugues do Brasil, curto. Diz:

- O formato escolhido e por que.
- O hook escolhido, com a frase literal.
- Quantos cortes, quanto tempo de material saiu e a duracao final.
- O que o `retention-qa` reprovou pelo caminho, se reprovou.
- O que ela deve conferir no CapCut antes de exportar.

Nao lhe mostres JSON, caminhos de ficheiro nem nomes de agente.

## Passo 7: registar

Escreve em `_memory/memories.md` o que aprendeste: que formato foi escolhido e
porque, o que ela mandou mudar depois, que decisao de ritmo se provou certa.
