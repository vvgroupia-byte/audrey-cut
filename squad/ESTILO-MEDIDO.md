# Estilo medido das referencias

Todos os numeros abaixo saem de medicao direta dos ficheiros em `refs/`,
feita por `engine/probe.py` e `engine/transcribe.py`. Nada aqui e estimado.

## Por video

| Ref | Duracao | Formato | Cortes | Plano mediano | Planos <1s | Palavras/min | Fala entra | LUFS | Cama sonora |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ref01 | 128.3s | 720:1280 | 57 | 1.96s | 32.8% | 205.0 | 0.0s | -14.7 | sim |
| ref02 | 88.3s | 720:1280 | 16 | 2.88s | 11.8% | 212.0 | 0.0s | -14.2 | sim |
| ref03 | 95.9s | 720:1280 | 20 | 3.0s | 14.3% | 282.0 | 0.0s | -14.2 | sim |
| ref04 | 91.6s | 720:1280 (letterbox) | 21 | 3.48s | 4.5% | 176.0 | 5.9s | -14.2 | sim |
| ref05 | 161.3s | 720:1280 | 43 | 2.92s | 34.1% | 218.0 | 0.0s | -14.4 | sim |
| ref06 | 58.8s | 720:1280 | 49 | 0.77s | 62.0% | 261.0 | 0.0s | -14.2 | sim |
| ref07 | 80.5s | 720:1280 | 22 | 2.96s | 26.1% | 210.0 | 0.0s | -14.3 | sim |

## Denominador comum

| Metrica | Mediana | Minimo | Maximo |
| --- | --- | --- | --- |
| Duracao (s) | 91.6 | 58.8 | 161.3 |
| Plano mediano (s) | 2.92 | 0.77 | 3.48 |
| Cortes por minuto | 16.0 | 10.9 | 50.0 |
| Planos abaixo de 1s (%) | 26.1 | 4.5 | 62.0 |
| Palavras por minuto | 212.0 | 176.0 | 282.0 |
| Segundo em que a fala entra | 0.0 | 0.0 | 5.9 |
| Loudness integrado (LUFS) | -14.2 | -14.7 | -14.2 |

## O que e dito nos primeiros 3 segundos (hook literal)

- **ref01**: "Eu não quero meus desenhos misturados com inteligência artificial. Esse artista"
- **ref02**: "Acredita que a menina teve coragem de comentar isso aqui no meu vídeo? Olha aqui."
- **ref03**: "E é assim que eu crio um roteiro em 3 minutos. Eu sei que parece loucura, mas eu vou te"
- **ref04**: "(sem fala nos primeiros 3s, abre em imagem. Primeira palavra aos 5.9s)"
- **ref05**: "Relato de parto começa às 8h30 da manhã A bolsa estourou E"
- **ref06**: "Como se gravar sozinho em 15 minutos. Sem falar nenhuma palavra,"
- **ref07**: "Essa é a Hannah. E ela não tem vergonha de copiar"
