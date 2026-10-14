# Receber timbres no MK300 Studio

O Studio liga os pedidos feitos no ChatGPT à MK-300 conectada ao computador. O ChatGPT pesquisa e prepara a receita; o programa local recebe, monta o preset, faz backup, grava por USB e confere os dados.

## Primeiro uso

1. Extraia o [ZIP do projeto](https://github.com/RickDiax/mvave/archive/refs/heads/main.zip) e abra `ABRIR-STUDIO.cmd`.
2. Clique em **Preparar minha pedaleira**. Em **Configurações**, escolha as portas MIDI e a posição que ficará reservada para os novos timbres. Não existe destino padrão: você escolhe.
3. Clique em **Conferir destino e ativar**, confira o nome do preset e confirme. Ativar somente lê a pedaleira; não grava um timbre.
4. Para vincular sua conversa, use **Copiar vínculo para o ChatGPT**, em Configurações → Entrega do ChatGPT, e cole na conversa. Isso informa o canal deste computador. Você faz esse vínculo uma vez por conversa/computador.
5. Peça a música ou o artista no ChatGPT e solicite o envio ao Studio. Se preferir, o campo opcional na tela **Receber timbres** monta um pedido já com o vínculo incluído.
6. Aguarde a confirmação em **Última entrega**. Para ouvir, selecione outra posição na pedaleira e volte ao destino gravado. O programa não carrega o preset automaticamente.

O Studio consulta os pedidos a cada 15 segundos, sujeito à conexão e ao cache do GitHub. A janela do programa precisa continuar aberta, com USB e internet. A aba do navegador pode ser fechada. Ao reiniciar o programa, ative o recebimento novamente.

## O que existe em cada área

- **Receber timbres:** estado do recebimento, destino escolhido e última gravação confirmada. Nenhum preset de exemplo aparece como se fosse parte da coleção do usuário.
- **Meus timbres:** versões guardadas no computador e receitas recebidas. Importar um timbre ou backup abre um rascunho, sem escrever na pedaleira.
- **Editor:** conferência e ajustes opcionais. Abrir um timbre não o carrega na pedaleira. Só **Conferir e enviar** grava.
- **Configurações:** portas MIDI, instrumento, destino dos pedidos e repositório de entrega. Os ajustes ficam lembrados para essa instalação.

## Outras pessoas podem usar?

Sim, como aplicativo local para Windows e MK-300. Cada instalação cria um **canal próprio**, guardado em `%LOCALAPPDATA%\MK300Studio\receiver.json`. Biblioteca e backups também são locais. O identificador do canal permanece ao atualizar o programa nessa mesma conta do Windows; copiar apenas o projeto para outro computador gera outro identificador.

Para automatizar na própria conta:

1. Crie um **fork público** deste projeto no GitHub, com branch `main`.
2. Conecte o GitHub dessa conta ao ChatGPT e permita acesso ao fork.
3. No Studio, abra Configurações → **Entrega do ChatGPT e compartilhamento** e informe `seu-usuario/mvave` em Repositório de entrega. Salve as configurações.
4. Ative o recebimento e cole o vínculo gerado pelo programa na sua conversa do ChatGPT.

O programa baixa receitas somente do repositório configurado e do seu canal. Não usa uma caixa compartilhada como alternativa. Um pedido com outro identificador é recusado antes de abrir a USB. O canal é um identificador de roteamento, **não uma senha**; a autorização para publicar vem do acesso ao repositório no GitHub.

Esta versão não é um site público com contas, login ou serviço central de IA. Sem acesso do ChatGPT ao repositório, o editor e os arquivos locais continuam funcionando, mas o envio automático da conversa não está estabelecido. Não requer chave de API da OpenAI no computador.

## Backups e cuidados do fluxo

Cada envio preserva a região de controles Ctrl A/B e expressão do preset de origem. As atribuições não são programadas automaticamente. No editor, é possível escolher explicitamente outra posição para copiar os controles.

Antes de escrever, o programa confere se o destino continua igual ao que foi reservado. Se outro programa ou o usuário salvou alterações ali, o recebimento pausa. Em caso de timeout depois do envio, confira a posição antes de reativar; a escrita não é repetida automaticamente. Pedidos processados têm identificação persistente.

Há somente **um pedido pendente por canal**, o mais recente. Aguarde a entrega antes de publicar o seguinte. Pedidos anteriores à ativação ou expirados são ignorados. O ChatGPT confirma a publicação da receita; a confirmação USB aparece no programa. Não há retorno automático do resultado local para o ChatGPT nesta versão.

As receitas publicadas são públicas. Dados lidos da pedaleira, backups e relatórios ficam no computador. Exportar um preset não inclui as capturas ou IR dos slots que ele utiliza. NAM/AM2/IR continuam sendo importados pelo M-EFCS.

## Protocolo para gerar receitas — versão 2

Leia `AGENTS.md`, `studio/catalog.json` e `automation/catalog.sha256` da versão atual do repositório. Use a planilha de modelos fornecida pelo usuário quando acessível e pesquise a referência musical. Não confunda numeração de tela com índices de protocolo: os índices são **zero-based**.

Obtenha o **repositório e o canal** do vínculo que o usuário copiou do Studio. Publique somente neste caminho:

```text
automation/channels/IDENTIFICADOR_DO_CANAL.json
```

O arquivo deve conter:

```json
{"format":"mk300-tone-inbox-2","channel_id":"UUID_HEXADECIMAL_DE_32_CARACTERES","job":null}
```

Para enviar, substitua `job` por um objeto com:

- `format`: `mk300-tone-job-2`.
- `channel_id`: o mesmo canal do vínculo e do arquivo.
- `id`: novo UUID hexadecimal minúsculo de 32 caracteres. Nunca reutilizar.
- `created_at`, `expires_at`: datas ISO 8601 com fuso; validade máxima de 24 horas. O pedido precisa ser posterior à ativação local.
- `catalog_sha256`: valor de `automation/catalog.sha256`.
- `request`, `sources`, `notes`: pedido, URLs efetivamente consultadas e inferências/limitações relevantes.
- `recipe`: exatamente `name`, `volume`, `bpm`, `pan`, `chain`, `blocks`.

`name`: 1 a 20 caracteres ASCII; `volume`: 0–100; `bpm`: 40–240; `pan`: -100–100. `chain` lista os 11 blocos uma vez. `blocks` contém WAH, FX, GATE, DS, AMP, CAB, EQ, MOD, DLY, REV, VOL. Cada bloco exige `enabled` booleano e pode informar `model_index` inteiro e `parameters` por nome exato de catálogo, com valores inteiros **brutos de protocolo**.

Para desativar sem trocar o modelo use `{"enabled":false}`. A troca inicializa os parâmetros catalogados e zera os slots restantes. Parâmetros `readonly` não podem ser adivinhados. Campos extras, destinos, portas, comandos, imagens brutas e alterações em controles/globais são recusados.

O antigo `automation/inbox.json` é legado e não é consultado por esta versão. Não publique ali nem invente um canal quando não houver vínculo. Não escreva em canais de outras pessoas. Atualizar o layout/validar código não autoriza publicar uma receita de teste ativa.

## Validação

`python -m unittest discover -s tests -v` testa gravação, preservação dos dados e isolamento entre instalações. `node tests/test_studio_ui.cjs` verifica navegação, configuração inicial, edição, biblioteca, vínculo e recebimento com DOM e USB simulados. O novo fluxo por canal ainda precisa de validação física; os testes não enviam dados à pedaleira.
