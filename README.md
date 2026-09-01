# Audrey Cut

Pega num video gravado em bruto e devolve um projeto ja montado no CapCut:
cortes feitos, legendas sincronizadas, enfases na tela e audio normalizado.

Feito para o perfil **@audreydoanne**. O conteudo e sempre da marca dela.

## Para instalar

Abre o Claude Code nesta pasta e escreve: **instala isso pra mim**.

Se preferires a mao: `./install.sh` e depois le o `INSTALAR.md`.

## Para usar

1. Poe o video em `Area de Trabalho > Audrey Cut > 1-videos-brutos`
2. No Claude Code, escreve `/editar`
3. Abre o CapCut. O projeto ja la esta.

## Como funciona

O principio e simples: **o que da para medir e feito por codigo, e o modelo so
decide o que exige julgamento.** Isso torna o resultado repetivel e barato.

```
video bruto
   |
   +-- [codigo]  ffmpeg tira o audio
   +-- [codigo]  whisper transcreve com tempo por palavra
   +-- [codigo]  detector acha silencios, muletas e takes repetidos
   |
   +-- [SQUAD]   decide: qual e o hook, que ordem contar, o que sobra,
   |             onde entra enfase, zoom e imagem de apoio
   |
   +-- EDL.json  (a lista de decisoes, e a fonte de verdade)
   |
   +-- [codigo]  ffmpeg corta e normaliza o audio
   +-- [MCP]     monta a sequencia no CapCut
```

O `EDL.json` e a peca central de proposito. Ele desacopla o trabalho do squad do
editor: se o servidor do CapCut deixar de funcionar num update, o EDL continua a
valer como plano de edicao e pode ser montado a mao ou noutro editor. Nenhum
trabalho se perde.

## O squad

| Agente | Decide |
| --- | --- |
| `hanah-franklin` | o formato e os 3 primeiros segundos |
| `finch-editor` | ritmo de corte, B-roll, zoom, audio |
| `giu-beckers` | legendas, enfases, texto fixo |
| `retention-qa` | veta o que nao passa no checklist |
| `viral-chief` | monta o EDL e manda para o CapCut |

Nenhum deles inventa numeros. Tudo o que e estilo sai do `squad/ESTILO-MEDIDO.md`,
que foi medido em 7 videos de referencia reais: duracao de cada plano, densidade
de fala, loudness, cor e posicao das legendas.

## O motor

| Ficheiro | Faz |
| --- | --- |
| `engine/probe.py` | duracao, formato, deteta os cortes, mede o audio |
| `engine/transcribe.py` | transcreve com tempo por palavra (local, sem chave de API) |
| `engine/detect.py` | marca silencios, muletas, takes repetidos |
| `engine/edl.py` | define e valida o EDL |
| `engine/legendas.py` | converte a fala para legenda no tempo do video montado |
| `engine/render.py` | corta os clipes e normaliza para -14 LUFS |
| `engine/previa.py` | junta os clipes num ficheiro so, para ver o ritmo |
| `engine/capcut_build.py` | traduz o EDL em chamadas do MCP do CapCut |
| `engine/estilo.py` | gera o ESTILO-MEDIDO.md a partir das medicoes |
| `engine/frames.py` | folha de contacto de um video, para inspecao visual |
| `engine/verificar.py` | diz o que falta na maquina |

Tudo corre localmente. O video dela nunca sai do computador.

## Testes

```bash
.venv/bin/python tests/test_motor.py
```

40 testes sobre a parte onde os erros sao silenciosos: a conversao de tempos
depois de o squad reordenar os clipes, a validacao do EDL, a deteccao de
candidatos a corte, e os nomes dos parametros que vao para o CapCut.

O `install.sh` corre-os no fim e recusa dar-se por concluido se falharem. O CI do
GitHub corre-os a cada push, e falha tambem se aparecer um traco longo em
qualquer ficheiro.

## Limitacoes, ditas de frente

Ha uma auditoria completa em [AUDITORIA.md](AUDITORIA.md), com o que estava errado
e foi corrigido, e com o que continua por provar.

- **A montagem no CapCut nunca foi executada de verdade.** Toda a cadeia ate ao
  corte foi corrida com video real, mas as chamadas para o CapCut foram
  calculadas e nunca enviadas, porque a maquina onde isto foi feito nao tem o app
  instalado. O primeiro teste real vai ser na maquina dela.
- **O CapCut nao tem API oficial.** O servidor que escreve o projeto e da
  comunidade. Quando a CapCut mudar o formato do ficheiro, pode partir. Nesse
  caso o corte continua a existir em `clipes/` e o plano em `EDL.json`.
- **Tres parametros do CapCut continuam por confirmar** contra o servidor real.
  Saem marcados como `campos_incertos` no plano, para o agente ler o schema em vez
  de adivinhar.
- **So foi feito e testado em macOS.**
- **A transcricao e lenta.** Varios minutos por video, e mais na primeira vez,
  porque descarrega um modelo de cerca de 3 GB.
- **O squad propoe, ela decide.** O projeto chega montado ao CapCut, mas quem
  aprova antes de publicar e ela.
