# Checklist de retencao

Usado pelo `retention-qa` antes de qualquer montagem. Cada item passa ou falha,
com o valor medido ao lado. Nao existe "esta razoavel".

## Bloco 1: segundos 0 a 3 (peso maximo)

| # | Item | Como medir | Passa se |
| --- | --- | --- | --- |
| 1.1 | A abertura e a melhor frase do material | comparar com as alternativas da Hanah | a escolhida e claramente mais forte, ou empata e ha razao escrita |
| 1.2 | Sem cumprimento nem preambulo | ler a primeira legenda | nao comeca por "oi", "fala", "hoje eu vim", "antes de mais" |
| 1.3 | Ha movimento nos primeiros 2s | ver o primeiro clipe | ha corte, zoom ou movimento antes do segundo 2 |
| 1.4 | Legenda desde o frame 1 | primeira entrada em `legendas` | inicio <= 0,1s |
| 1.5 | A promessa esta dita, nao insinuada | ler a transcricao dos 3s | da para dizer em voz alta o que o video vai entregar |
| 1.6 | A fala entra imediatamente | segundo da primeira palavra | 0,0s |

Sobre o 1.6: em 6 das 7 referencias a primeira palavra cai no segundo **0,0**. Nao
ha respiro, nao ha vinheta, nao ha um plano de estabelecimento. A unica excecao e
a referencia em formato **cinematografico**, que abre 5,9s so com imagem e musica
antes de alguem falar.

Ou seja: abertura sem fala e permitida **apenas** no formato cinematografico, e
so se houver imagem que segure sozinha. Em qualquer outro formato, atrasar a fala
e falha.

Falha em 1.1 ou 1.2 reprova o video inteiro. As outras voltam ao especialista.

## Bloco 2: segundos 3 a 10

| # | Item | Como medir | Passa se |
| --- | --- | --- | --- |
| 2.1 | Existe razao explicita para ficar | procurar loop, promessa numerada ou pergunta em aberto | ha pelo menos uma |
| 2.2 | A entrega comeca cedo | primeiro segundo com informacao util | antes do segundo 15 |
| 2.3 | Nao ha contexto desnecessario | ler o trecho | nada que possa sair sem o video perder sentido |

## Bloco 3: o corpo

| # | Item | Como medir | Passa se |
| --- | --- | --- | --- |
| 3.1 | Sem vales | procurar trechos > 6s sem corte, zoom, enfase ou B-roll | nenhum vale encontrado |
| 3.2 | Ritmo dentro do formato | `edl.py resumir`, comparar com a tabela do formato | plano mediano dentro da faixa, ou justificado |
| 3.3 | Enfases nao saturam | `enfases_por_minuto` do resumo | entre 2,7 e 4,7 (faixa das referencias) |
| 3.4 | Legenda cobre a fala toda | cobertura calculada | 100% |
| 3.5 | Nenhum corte no meio de uma palavra | fronteiras contra a transcricao | todo corte cai entre palavras |

## Bloco 4: o fim

| # | Item | Como medir | Passa se |
| --- | --- | --- | --- |
| 4.1 | O loop fechou | comparar a promessa de abertura com o fim | fechou, ou nunca foi aberto |
| 4.2 | Sem cauda morta | ultimos 3s | acaba na ultima palavra util |
| 4.3 | CTA depois da entrega | posicao do CTA, se houver | vem depois de a entrega estar completa |

## Bloco 5: tecnico

| # | Item | Como medir | Passa se |
| --- | --- | --- | --- |
| 5.1 | Vertical | `formato` do EDL | altura > largura |
| 5.2 | Loudness | medicao do render | entre -15 e -13 LUFS |
| 5.3 | Cama sonora presente | campo `audio` do EDL | presente (7 de 7 referencias tem) |
| 5.4 | Duracao dentro da faixa | duracao final | entre 59 e 161s, ou justificada |
| 5.5 | Sem traco longo | validacao do `edl.py` | nenhuma ocorrencia |
| 5.6 | Sem mencao a agencia | procurar nos textos | nenhuma. A marca e da Audrey |

## Formato do veredito

```
VEREDITO: aprovado | reprovado

| # | item | medido | alvo | passa | volta para |

VALES: <segundos, ou nenhum>
JUSTIFICACOES ACEITES: <o que saiu da faixa e porque>
```
