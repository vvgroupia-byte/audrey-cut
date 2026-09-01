# Auditoria

## Segunda rodada, 01/set/2026 (tarde): a receita do funil e a prova real

O Kaiky trouxe os 18 passos do tutorial que ensina a ligar o Claude ao CapCut,
com prints. O tutorial usa um servidor diferente do que eu tinha escolhido, e o
autor dele validou a ligacao de verdade. Engoli o orgulho e troquei.

### O que a segunda engenharia reversa encontrou

**1. O servidor escolhido na v1 nunca tinha sido testado por ninguem que eu
pudesse verificar.** O do tutorial (`fancyboi999/capcut-mcp`) vinha com uma
receita comprovada: SSE na porta 9077, `mcp==1.13.1` fixado, Python 3.12.
Troquei, clonei, e li o codigo fonte dele inteiro em vez de confiar em README.

**2. Os "campos incertos" da v1 morreram.** Com o codigo do servidor aberto
(app/schemas/*.py), os tres pontos por confirmar ficaram confirmados:
`transform_y` e normalizado (0 = centro, -0.8 = fundo), `track_name` existe em
todas as ferramentas, e `font_size` esta na unidade propria do CapCut (legenda
tipica = 5). O executor usa os valores certos e os testes verificam-nos.

**3. O agente a despachar chamadas MCP era a arquitetura errada.** A sequencia
de chamadas e 100% deterministica a partir do EDL. Virou codigo
(`engine/capcut_exec.py`): fala com a API REST do mesmo servidor, executa em
segundos, e e testavel. O MCP continua registado para conversas avulsas com o
CapCut. O `capcut_build.py` da v1 foi removido: dois caminhos para o mesmo
destino divergem sempre.

**4. Duas descobertas no codigo do servidor que melhoraram o resultado:**
- `add_subtitle` aceita o conteudo SRT inline: a legenda base inteira
  (33 blocos no teste) vai numa UNICA chamada, em vez de 33 `add_text`.
- `add_video` separa o recorte na origem (`start`/`end`) da posicao na
  timeline (`target_start`), que e exatamente o que o EDL precisa.

**5. O `draft_folder` do save_draft nao copia nada.** So reescreve os caminhos
internos dos assets para onde o draft VAI estar. A copia fisica (o passo 6
manual do tutorial) e responsabilidade nossa: o executor faz `copytree` da pasta
do servidor para a pasta de drafts do CapCut e verifica que o `draft_info.json`
chegou. O passo manual morreu.

**6. O servidor exige ffprobe e esta maquina so tinha ffmpeg.** Ficou um shim
(`~/.local/bin/ffprobe`, Python + PyAV) que responde ao subconjunto de flags que
o servidor usa. Na maquina dela, o `brew install ffmpeg` traz o ffprobe real.

**7. Zero-terminal a serio.** O tutorial manda deixar uma janela do Terminal
aberta com o servidor. Um agente DevOps montou: launchd (liga no login, revive
se cair), escolha de porta com fallback 9077 a 9099, registo MCP com
`--scope user` (sem isso o registo fica preso a pasta onde correu, erro que eu
proprio cometi ao testar), e um `desinstalar.sh`.

### A prova que faltava

Executado nesta maquina, contra o servidor real, com video real:

```
create_draft -> add_video x3 -> add_video_keyframe -> add_subtitle (SRT, 33
blocos) -> add_text x2 -> save_draft -> copia para a pasta de drafts
```

O draft gerado foi inspecionado por dentro (`draft_info.json`): 3 videos na
track video_main com os mp4 em assets/, 33 legendas na track subtitle, enfase e
texto fixo, 4 keyframes de zoom, duracao 18.340s exata, e os caminhos internos a
apontar para a pasta de destino. **So falta abrir no app**, que nao existe nesta
maquina; o formato do ficheiro e o que o CapCut le, gerado pela mesma biblioteca
(pyJianYingDraft) que o tutorial validou visualmente.

## Primeira rodada, 01/set/2026 (manha)

Revisao critica de tudo o que foi construido. Cada item diz o que estava errado,
como se percebeu, e o que ficou feito.

## Falhas graves, corrigidas

### 1. Os nomes dos parametros do CapCut estavam inventados

**O erro:** o `capcut_build.py` gerava 62 chamadas com nomes que eu nunca tinha
verificado contra o servidor. Estavam errados em quatro sitios:

| Escrevia | Correto |
| --- | --- |
| `duration` no add_video | `end`, que e um instante e nao uma duracao |
| `cor`, `tamanho_px` | `font_color`, `font_size` |
| `keyframes: [{time, scale}]` | `property_types`, `times`, `values`, tres listas paralelas |
| `track: "principal"` | `track_name`, e so no keyframe |

**Como se percebeu:** fui ler o `MCP_Documentation_English.md` do VectCutAPI, que
e o upstream do servidor escolhido, e comparei com o que estava gerado.

**Consequencia se tivesse passado:** as 62 chamadas falhavam, ou pior, passavam e
montavam o texto no sitio errado. Como o CapCut nao esta instalado aqui, isto so
apareceria na maquina dela.

**Feito:** reescrito com os nomes documentados, e ha agora 8 testes so sobre isto.

### 2. Adivinhava o que a documentacao nao diz

Tres coisas continuam por confirmar: o sistema de coordenadas de `transform_x/y`,
se `add_video` e `add_text` aceitam `track_name`, e a unidade de `font_size`.

Antes eu escolhia um valor e seguia. Agora saem em `campos_incertos`, com as duas
leituras possiveis, e o plano manda o agente ler o schema real antes de enviar.
No teste real, 35 das 40 chamadas vem marcadas assim. E menos bonito e e honesto.

### 3. Palavras desapareciam da legenda

**O erro:** duas causas distintas, ambas a fazer perder palavras.

A primeira: o whisper devolve, de vez em quando, uma palavra com inicio igual ao
fim. O filtro descartava-a.

A segunda: quando duas palavras vem muito coladas, o ajuste que evita sobreposicao
deixava o fim antes do inicio, e o grupo inteiro era deitado fora.

**Como se percebeu:** a cobertura dava 98,5% e o checklist exige 100%. Em vez de
baixar a exigencia, fui ver que palavra faltava. Era a palavra "uma", aos 25,66s,
com duracao zero na transcricao.

**Feito:** os dois casos passam a dar uma duracao minima de 50ms em vez de
descartar. Uma sobreposicao de 50ms nao se ve, uma palavra sem legenda ve-se.
Cobertura passou a 100%, com dois testes de regressao.

### 4. A cobertura era medida da maneira errada

Media-se por tempo de ecra, o que nunca poderia dar 100%: entre uma palavra e a
seguinte ha silencio. O checklist exigia uma coisa impossivel.

Agora mede-se por palavra: das que sobreviveram ao corte, quantas aparecem
escritas. E isso que interessa, porque metade das pessoas assiste sem som.

### 5. O instalador mandava usar um ficheiro que nao existe

O `install.sh` dizia "No Windows usa install.ps1". Esse ficheiro nunca foi
escrito. Agora diz a verdade: so foi feito e testado em Mac, e manda falar com o
Kaiky antes de tentar noutro sistema. Prefiro isso a entregar um script que nunca
correu.

### 6. O passo de instalacao do MCP ia falhar

O `INSTALAR.md` mandava correr `python3 install.py`. No macOS o `python3` do
sistema e o 3.9, e esse servidor exige 3.10 ou superior. Passou a usar `uv run`,
que garante a versao certa sem tocar no Python do sistema.

## Melhorias

### 7. A transcricao era 2,7x mais lenta do que precisava

Media, no mesmo video de 58,8s:

| Modelo | Tempo | Velocidade |
| --- | --- | --- |
| large-v3-turbo | 55,3s | 1,1x tempo real |
| large-v3 | 147,9s | 0,4x tempo real |

Onde as duas transcricoes diferiram, o turbo escreveu a fala como ela sai
("os dias tao dificeis") e o large-v3 corrigiu a gramatica ("estao dificeis").
Para legenda o turbo esta certo: legenda transcreve, nao corrige.

Ou seja, o turbo ganhou nos dois eixos. Passou a ser o defeito, e a espera dela
por video cai de cerca de 6 minutos para cerca de 2.

### 8. Nao havia um unico teste

Havia zero. Num repositorio que vai para outra pessoa usar, isso nao se defende.
Sao agora **40 testes** sobre a parte onde os erros sao silenciosos: aritmetica de
tempos depois de reordenar clipes, validacao do EDL, deteccao de candidatos, e os
nomes dos parametros do CapCut.

O `install.sh` corre-os no fim e recusa dar-se por concluido se falharem.

### 9. O crop podia cortar a cabeca dela sem avisar

Se ela gravar na horizontal, o enquadramento para 9:16 faz crop central, e numa
gravacao 16:9 a pessoa raramente esta centrada na vertical. O `render.py` passa a
avisar antes de cortar.

### 10. Integracao continua e licenca

Adicionado GitHub Actions que corre os testes e falha o build se aparecer um traco
longo em qualquer ficheiro. Adicionada licenca fechada, de proposito: o valor esta
no metodo, nao no codigo. Se um dia quiser abrir, troca-se por MIT.

## O que continua por fazer, e nao da para esconder

### A montagem no CapCut nunca foi executada

E a pendencia principal. O CapCut nao esta instalado nesta maquina, o `.dmg` do
iCloud e so um downloader que precisa de rede que o shell aqui nao alcanca, e por
isso as chamadas foram **calculadas mas nunca enviadas**. Tudo o resto da cadeia
foi corrido com video real: medicao, transcricao, deteccao, EDL, legendas, corte,
normalizacao de audio e previa.

Traduzindo: da montagem para tras, esta provado. Da montagem para a frente, esta
por provar, e o primeiro teste real vai ser na maquina dela.

### Falta o video bruto dela

Tudo foi validado com referencias ja editadas. Num bruto verdadeiro, com pausas,
gaguejos e takes repetidos, o detector vai ter muito mais trabalho e e ai que se
vai ver se os limiares estao bem escolhidos.

### O link do funil

O `app.automateflow.chat` foi bloqueado pelo classificador de seguranca por trazer
token de sessao e parametros de tracking na URL. Nao contornei. Se o conteudo for
util, cola-se aqui e entra no `INSTALAR.md`.

### O servidor do CapCut e comunitario

Nao ha API oficial. Quando a CapCut mudar o formato do projeto, aquilo parte. Foi
por isso que o `EDL.json` ficou no centro da arquitetura: se partir, o corte
continua em `clipes/`, a previa continua a ser gerada, e o plano de montagem
continua legivel para se fazer a mao.
