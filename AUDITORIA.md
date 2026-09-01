# Auditoria, 01/set/2026

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
