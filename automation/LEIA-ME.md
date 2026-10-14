# Pedir no ChatGPT e receber na MK-300

O objetivo do projeto é automatizar a criação de timbres. O editor manual é uma ferramenta auxiliar. O fluxo principal é:

**Pedido nesta conversa → pesquisa pelo ChatGPT → receita publicada no GitHub → Studio recebe → monta o preset → backup → gravação USB → conferência.**

## Usar no Windows

1. Atualize o projeto com o [ZIP completo](https://github.com/RickDiax/mvave/archive/refs/heads/main.zip), extraia e abra `ABRIR-STUDIO.cmd`.
2. Em **Conexão**, confira entrada `USB-Midi 0` e saída `USB-Midi 1`. Feche M-EFCS e DAW.
3. Em **Receber timbres automaticamente**, escolha a posição que ficará reservada. **137** é uma sugestão baseada nos testes anteriores. A escolha é sua: novos timbres substituirão essa posição, com backup.
4. Clique **Ativar recepção**, confira o nome atual do destino e confirme a reserva. Essa ativação apenas lê a pedaleira; não grava um timbre.
5. Com a recepção ativa, peça nesta conversa, por exemplo: **“Crie o timbre de [música/artista] para minha Strat e envie ao Studio.”**
6. O ChatGPT pesquisa, usa a planilha MK-300 fornecida, monta os parâmetros e atualiza a caixa de entrada. O programa recebe e grava sem download/importação manual ou confirmação por preset.
7. Aguarde **Recebido e verificado** no Studio. Para ouvir o preset salvo, selecione outra posição na pedaleira e volte à reservada. O receptor não envia o comando de carregamento do preset.

Pode fazer o pedido pelo ChatGPT no celular, desde que o Studio permaneça aberto no computador com internet e USB conectada. A janela do navegador pode ser fechada: o receptor continua na janela do programa. Ao encerrar/reiniciar o programa, é preciso ativar a recepção novamente. Para interromper, use **Pausar**, ou encerre o programa após concluir a escrita.

Não precisa de chave de API da OpenAI, token GitHub ou servidor público no computador. A inteligência continua nesta conversa com acesso ao GitHub; o programa local interpreta uma receita numérica, sem executar código vindo do pedido.

## O que é automático e o que é confirmado

O ChatGPT publica a receita em `RickDiax/mvave`, arquivo `automation/inbox.json`. O receptor consulta esse arquivo a cada 15 segundos, sujeito à conexão e ao cache do GitHub. A receita contém timbre, pesquisa/fontes e identificação do pedido; não contém portas MIDI, número de destino ou comandos arbitrários. O destino é sempre aquele reservado localmente.

O ChatGPT consegue confirmar a **publicação no GitHub**. A confirmação de **gravação física** aparece no Studio e nos relatórios locais. Não há retorno do computador para o ChatGPT nesta versão; não confundir publicação com confirmação da USB.

A caixa de entrada guarda **um pedido pendente, o mais recente**. Espere o Studio conferir um timbre antes de pedir o próximo. A gravação anterior fica em backup. Pedidos antigos à ativação, vencidos ou já processados são ignorados. Em caso de internet temporariamente indisponível, o programa repete somente a consulta. Se a escrita falhar, pausa e não repete o envio automaticamente.

Se você modificar a posição reservada por outro programa ou pelo salvamento manual, a automação detecta a mudança e pausa. Confira a posição e reative. As regiões de controle Ctrl A/B e expressão são preservadas do destino reservado: as atribuições existentes a MOD e DS continuam úteis ao trocar o modelo desses blocos, mas não são reprogramadas automaticamente.

As receitas e suas fontes ficam em um repositório público. Dados lidos da unidade, backups e relatórios permanecem em `%LOCALAPPDATA%\MK300Studio`. O receptor não envia esses dados ao GitHub.

## Limites de timbre

A fidelidade depende dos modelos disponíveis na unidade e da guitarra/saída utilizada. A receita é um ponto de partida pesquisado; ouvir e ajustar continua fazendo parte do processo. O catálogo segue a planilha fornecida, não é uma detecção do conteúdo real de cada slot. Parâmetros cujo encoding não foi confirmado são bloqueados.

Este caminho envia presets com os modelos já disponíveis. Não gera nem importa capturas NAM/AM2 ou IR. Esses arquivos continuam sendo importados pelo M-EFCS. O novo receptor foi validado com USB simulada; a gravação do editor anterior já foi confirmada pelo usuário na V75, e o receptor ainda precisa do primeiro teste físico.

## Protocolo para quem gera o pedido

O arquivo `automation/catalog.sha256` contém o SHA-256 dos bytes de `studio/catalog.json`. Use esse valor no pedido, junto com o catálogo da mesma versão. Os índices de modelo são **zero-based**; nomes do catálogo AMP/CAB podem começar com a numeração de tela, que é **one-based**. Exemplo confirmado: tela 71 → índice 70; tela 63 → índice 62. Não converter pelo nome de um catálogo de firmware diferente.

Caixa de entrada:

```json
{"format":"mk300-tone-inbox-1","job":null}
```

Ao publicar um timbre, `job` recebe um objeto com:

- `format`: `mk300-tone-job-1`.
- `id`: UUID hexadecimal novo de 32 caracteres minúsculos, nunca reutilizado.
- `created_at` e `expires_at`: datas ISO 8601 com fuso; validade de no máximo 24 horas. Gere depois que a recepção estiver ativa. Pedido anterior à ativação é ignorado.
- `catalog_sha256`: valor do arquivo mencionado acima.
- `request`: resumo do pedido musical.
- `sources`: lista de URLs consultadas. Não invente fontes nem trate inferências como confirmação.
- `notes`: limitações e inferências relevantes.
- `recipe`: exatamente `name`, `volume`, `bpm`, `pan`, `chain`, `blocks`.

`name` aceita 1 a 20 caracteres ASCII sem acentos; `volume` de 0 a 100; `bpm` de 40 a 240; `pan` de -100 a 100. `chain` lista os 11 blocos uma única vez. `blocks` contém todos eles: WAH, FX, GATE, DS, AMP, CAB, EQ, MOD, DLY, REV, VOL.

Cada bloco exige `enabled` booleano e pode conter `model_index` inteiro e `parameters`, um objeto cujas chaves são os nomes exatos dos parâmetros do catálogo e cujos valores são inteiros **brutos de protocolo**. Para um bloco desativado sem mudança de modelo, use apenas `{"enabled":false}`: isso conserva o modelo e os dados existentes. Trocar modelo inicializa os parâmetros catalogados com seus padrões e zera slots restantes. Parâmetros `readonly` não podem ser adivinhados.

Exemplo de uma configuração de bloco válida, não de um pedido completo:

```json
{"enabled":true,"model_index":47,"parameters":{"Fuzz":25,"Level":35}}
```

Não incluir `slot`, imagens brutas, comandos MIDI, configurações globais, controles/expressão, URLs de execução ou código no pedido. O receptor recusa campos extras. Para alterar o som depois, publique um novo pedido com novo ID; o antigo não é reexecutado.

## Validação

`python -m unittest discover -s tests -v` verifica o receptor e o fluxo anterior. `node tests/test_studio_ui.cjs` verifica ativação/recebimento/pausa e a preservação de rascunhos manuais com DOM e USB simulados. Nenhum teste envia dados a uma pedaleira física.
