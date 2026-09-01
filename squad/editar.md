---
description: Edita um video bruto e entrega o projeto montado no CapCut
---

# /editar

Corta um video gravado em bruto e entrega o projeto pronto no CapCut.

## O que fazer

Executa a task `tasks/editar-video.md` desta pasta, do inicio ao fim, sem pular
passos e sem pedir confirmacao a cada etapa. Para apenas se:

- nao houver nenhum video em `~/Desktop/Audrey Cut/1-videos-brutos/`
- houver mais do que um video e nao for obvio qual e (pergunta qual)
- o `retention-qa` reprovar tres vezes seguidas o mesmo ponto
- faltar o `ESTILO-MEDIDO.md`

## Carregamento obrigatorio

1. `~/.claude/commands/audrey-cut/squad.yaml`
2. `~/.claude/commands/audrey-cut/ESTILO-MEDIDO.md`
3. `~/.claude/commands/audrey-cut/checklists/retencao.md`
4. `~/.claude/commands/audrey-cut/tasks/editar-video.md`

## Como falar com ela

Portugues do Brasil, direto, sem jargao tecnico. Ela nao quer saber de EDL, de
LUFS nem de MCP. Ela quer saber: ficou bom, quanto tempo tem, e o que conferir
antes de postar.

Avisa-a **antes** de comecar a transcricao que essa parte demora alguns minutos,
para nao parecer que travou.

## Regras que nao se quebram

- A marca e sempre a da Audrey. Nunca menciones VV Group nem agencia no video.
- Nunca uses traco longo em legenda ou copy.
- Nenhum numero de estilo e inventado: sai do `ESTILO-MEDIDO.md`.
- Nada e montado sem o `retention-qa` aprovar.
- Se o MCP do CapCut nao estiver ligado, di-lo. Nunca finjas que montaste.
