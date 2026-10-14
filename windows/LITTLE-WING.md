# Little Wing — aproximacao Hendrix para Stratocaster

Destino autorizado: posicao 137. Origem preservada: Belief na 142. Firmware informado V75, leitura e copia integral ja verificadas na unidade.

## Instalar e aplicar

Da nova versao do ZIP, copie `little_wing.py`, `little_wing.json` e `aplicar-little-wing.cmd` para a pasta `windows` que ja tem seu ambiente `.venv-midi`. Mantenha `copiar_teste.py` ao lado deles.

Feche M-EFCS/DAW e execute `aplicar-little-wing.cmd`. O programa confere se o preset salvo na 137 ainda se chama TESTE USB, se DS/MOD sao os modelos observados e se a regiao de controles corresponde ao ultimo relatorio enviado. Se voce nao salvou as atribuicoes na pedaleira, ele recusa a escrita.

Antes de gravar, o JSON local guarda a imagem completa da 137. A aplicacao modifica somente nome, volume/BPM/pan, ordem, modelos, parametros e ativacao de blocos conhecidos. Conserva todos os bytes de controles/expressao e demais campos desconhecidos. Grava apenas 137 e confere o retorno byte a byte. Nao carrega presets nem modifica globais ou arquivos AMP/IR.

Apos sucesso, selecione outro preset e volte a 137 para carregar a nova imagem. Caso o nome antigo persista no visor, o projeto documenta que algumas versoes so atualizam o nome apos reiniciar; isso nao substitui conferir o relatorio e os parametros. Se houver erro depois de iniciar a escrita, nao reexecute sem conferir a 137 e enviar o relatorio.

O aplicador recusa reexecucao sobre LITTLE WING para nao apagar ajustes posteriores sem uma nova revisao. O JSON e backup tecnico desse registro, nao backup completo ou preset M-EFCS importavel.

## Sons e botoes

- Base: Plexi em baixo ganho, caixa vintage, EQ moderado e Plate discreto.
- Ctrl A: liga/desliga MOD (Univibe), conforme a atribuicao feita pelo usuario.
- Ctrl B: liga/desliga DS (MW-FACE), conforme a atribuicao feita pelo usuario.
- Estado salvo: MOD e DS desligados. Compressor, gate e delay desligados.
- Expressao: atribuicoes existentes preservadas.

O relatorio mostra DS indice 47 e MOD indice 11 na unidade. O significado dos bytes de Ctrl nao foi inteiramente decodificado; preservamos exatamente a regiao fornecida apos o usuario configurar os botoes. O comportamento deve ser conferido na pedaleira. Nenhum longo pressionamento foi reprogramado.

## Valores iniciais sugeridos

| Bloco | Modelo | Parametros |
|---|---|---|
| AMP | 43DS-Mar59 | Gain 24; Level 70; Bass 45; Middle 55; Treble 48; Reso 10; Pres 40; Bright 35 |
| CAB | 43MarPlx | Level 70; Low Cut 80 Hz; High Cut 6,5 kHz (raw 65) |
| DS | MW-FACE | Fuzz 65; Level 50 |
| MOD | Univibe | Speed 1,6 (raw 16); Depth 40; Mix 35; Sync OFF |
| EQ | Normal EQ 10 | 31/62/125/250/500/1k/2k/4k/8k/16k: -6/-3/-1/0/+1/+1/0/-1/-3/-6 dB |
| REV | Plate | Decay 22; Mix 12; High Pass 60; Low Pass 50; Mod Depth 0 |

Preset Vol 80, BPM 72, panorama central. As unidades brutas seguem o protocolo/catálogo; confira a apresentacao de Speed e High Cut no visor. Os slots AMP43/CAB43 seguem a planilha fornecida, ainda sem leitura automatica de seus nomes na unidade.

Todos esses numeros sao pontos de partida propostos, nao regulagens historicas documentadas ou valores calibrados por audicao. Compare volume com a banda e refine por ouvido. Comece pelo captador do braco ou braco+meio, volume da guitarra 7–8; abra para 10 nas partes mais fortes. Ajuste os captadores de acordo com a sua Strat.

## Referencias e fidelidade

Referencia escolhida: Hendrix, gravacao de estudio. Eddie Kramer descreve um pequeno Leslie no solo: https://www.guitarworld.com/artists/watch-steve-vai-and-eric-johnson-play-little-wing . O Univibe e a aproximacao escolhida para o movimento, nao uma afirmacao de que esse pedal foi usado naquela gravacao.

Plexi/caixa: escolha pratica do banco descrito em `MK-300_M-VAVE_V73_PTBR.xlsx`, nao identificacao comprovada do amplificador exato da sessao. MW-FACE e opcao de saturacao adicional solicitada pelo usuario; nao e apresentado como pedal obrigatorio da gravacao.

Protocolo: https://github.com/jpfaria/mvave/blob/main/docs/protocol.md . Parametros dos novos DS: tabela oficial MK300 NEW DS LIST, no centro https://www.cuvave.com/download .

## Testes

Testes locais simulam preservacao dos controles, validacao das precondicoes, backup antes da escrita e verificacao integral. A aplicacao sonora e a operacao de Ctrl A/B ainda exigem o teste fisico. O programa roda localmente; o ChatGPT nao acessa diretamente o USB.
