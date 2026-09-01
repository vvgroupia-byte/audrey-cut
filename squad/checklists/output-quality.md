# Checklist de entrega

Corre antes de dizer que o video esta pronto. Se algum item falhar, nao esta.

| # | Item | Passa se |
| --- | --- | --- |
| 1 | O EDL valida | `edl.py validar` sai com codigo 0 |
| 2 | Todos os clipes existem | cada ficheiro do manifesto existe e tem tamanho maior que zero |
| 3 | A duracao fecha | soma dos clipes bate com a duracao declarada, com folga de 0,05s |
| 4 | Formato vertical | 1080x1920 em todos os clipes |
| 5 | Audio normalizado | entre -15 e -13 LUFS |
| 6 | Legenda cobre a fala | 100% da fala tem legenda |
| 7 | Sem traco longo | nenhuma ocorrencia em nenhum texto |
| 8 | Sem mencao a agencia | nenhuma mencao a VV Group ou a qualquer agencia |
| 9 | Retention QA aprovou | veredito escrito e aprovado |
| 10 | O draft abre no CapCut | verificado no app, nao presumido |

O item 10 e verificacao visual. Nunca o marques como feito sem ter aberto o
CapCut e visto a timeline montada.
