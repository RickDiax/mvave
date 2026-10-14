# Primeiro teste: Windows e MK-300 V75

**Editor visual disponível:** veja [MK300 Studio](../studio/LEIA-ME.md). Para abrir, execute `ABRIR-STUDIO.cmd` na raiz do projeto.

Este teste lista portas MIDI e consulta o bloco global e o preset atualmente editado. Nao carrega, salva ou substitui presets, nao envia notas e nao modifica configuracoes globais. O firmware V75 foi informado pelo usuario; o script nao detecta a versao.

## Executar

1. Baixe o ZIP desta versao do repositorio e extraia tudo para uma pasta local. Nao execute dentro do ZIP.
2. Instale **Python 3.12 x64** pelo site https://www.python.org/downloads/release/python-31210/ se necessario, escolhendo Windows installer (64-bit) e incluindo o Python Launcher. Python 3.11 x64 tambem e aceito. Outras versoes/arquiteturas nao sao selecionadas para este teste.
3. Entre em `windows` e abra `instalar.cmd`. Ele cria o ambiente local `windows/.venv-midi` e instala somente `mido` e `python-rtmidi`. Requer internet. Nao precisa instalar o projeto completo, Git ou tone-analyzer neste primeiro teste.
4. Ligue a MK-300 e conecte-a por um cabo USB de dados. Feche M-EFCS, DAW e outros programas MIDI antes do teste.
5. Abra `testar.cmd` e aguarde a mensagem. Um relatorio JSON sera criado em `windows/diagnosticos`.
6. Envie o JSON ao ChatGPT para verificarmos a leitura.

Se o Windows exibir um aviso sobre arquivo baixado, confira a origem e examine os arquivos antes de executa-los. Nao e necessario desativar protecoes ou executar como administrador.

## Portas com nomes diferentes

A entrada e a saida podem ter nomes diferentes no Windows. O diagnostico aceita ambas separadamente. Se nao houver uma unica candidata reconhecida, ele para e lista as portas; nao tenta dispositivos aleatorios.

Abra um terminal na pasta `windows` e use os nomes completos exibidos:

```bat
testar.cmd --input "NOME COMPLETO DA ENTRADA" --output "NOME COMPLETO DA SAIDA"
```

Para apenas listar portas, sem enviar consultas:

```bat
testar.cmd --list-only
```

## Interpretar o resultado

- `ports_listed`: somente portas listadas; comunicacao ainda nao testada.
- `read_success`: consultas de 86 e 448 bytes respondidas, checksum conferido e campos basicos plausiveis.
- `error`: leia a mensagem. Cabo, portas ocupadas e mudancas no protocolo sao possibilidades, nao conclusoes automaticas.

Uma leitura bem-sucedida nao valida comandos de gravacao, importacao NAM, catalogo V75 ou fidelidade sonora. Os indices dos modelos e knobs sao salvos como dados brutos, evitando atribuir automaticamente nomes antigos a slots modificados.

O JSON inclui nomes das portas, nome do preset e dados brutos do preset atual. Fica somente no computador e nao e enviado automaticamente. Nao e um backup completo da pedaleira e nao deve ser importado pelo M-EFCS. A pasta de relatorios e o ambiente Python sao ignorados pelo Git.

Depois deste teste: conferir o catalogo da unidade, fazer backup pelo M-EFCS e preparar um primeiro timbre para uma posicao escolhida pelo usuario. Nenhum comando de escrita esta presente neste diagnostico.

## Validacao do codigo

Testes simulados verificam consultas de leitura, rejeicao de mensagens invalidas, selecao de portas e layouts inesperados. Executar da raiz: `python -m unittest discover -s tests -p test_windows_diagnostic.py`.

Execucao real em Windows/MK-300 V75 ainda depende do teste local. Este recurso e independente dos atalhos do projeto destinados a macOS.

## Erro de compilador ao instalar python-rtmidi

A versao 1.5.8 publica wheels Windows x64 para CPython 3.11 e 3.12. O instalador anterior aceitava qualquer Python mais novo e poderia selecionar uma versao sem wheel, tentando compilar C++. O instalador corrigido seleciona 3.12/3.11 x64 e usa `--only-binary=:all:`; ele nunca tenta compilar. Fonte: https://pypi.org/project/python-rtmidi/1.5.8/#files

Se voce ja tentou instalar, baixe novamente o ZIP e extraia para uma nova pasta. A antiga `.venv` nao sera usada. Nao e preciso instalar Visual Studio nem desinstalar seu Python atual. Depois de instalar Python 3.12 x64, execute o novo `instalar.cmd` e o novo `testar.cmd`.

## Teste autorizado de copia: 142 para 137

Apos a leitura funcionar, o usuario escolheu USER PRESET 137 para testar gravacao. A origem e o **Belief salvo na memoria, posicao 142**, nao alteracoes ainda nao salvas no editor.

Se ja instalou as dependencias, copie apenas `copiar_teste.py` e `copiar-teste.cmd` desta versao para a pasta `windows` existente, ao lado de `diagnostico.py`. Mantenha seu ambiente `.venv-midi`.

1. Feche M-EFCS e DAW e deixe a pedaleira ligada por USB.
2. Execute `copiar-teste.cmd`. Ja usa as portas observadas nesta unidade: USB-Midi 0 / USB-Midi 1.
3. O programa le a origem e o destino. Recusa qualquer origem com nome diferente de Belief e qualquer destino diferente de USER PRESET (com numero opcional).
4. Guarda localmente as imagens originais de ambas as posicoes no JSON de diagnostico antes de escrever.
5. Copia os 448 bytes da origem, alterando somente o nome para TESTE USB, grava apenas a posicao 137 e verifica por leitura de retorno.
6. Quando disser “Copia salva e verificada byte a byte”, selecione **137** na pedaleira para ouvir.
7. Envie o JSON `copia_142_137_...` de `windows/diagnosticos`.

O programa nao carrega presets, nao muda configuracoes globais e nao modifica AMP/CAB ou a posicao 142. Nao tem opcao para forcar sobrescrita de um preset nomeado. O JSON e uma copia tecnica dos dois registros, nao um backup completo nem um arquivo importavel no M-EFCS.

Para fazer apenas a previa, no terminal da pasta windows:

```bat
.venv-midi\Scripts\python.exe copiar_teste.py
```

Em caso de falha apos iniciar escrita, nao repita a gravacao automaticamente; confira a posicao 137 e envie o relatorio. A ausencia de ACK nao garante que nada tenha sido escrito.

Os testes simulados cobrem preservacao dos bytes desconhecidos, recusa de destino nomeado, backup antes da escrita, verificacao de retorno, enderecamento exclusivo de 137 e rejeicao de comandos para origem/globais/carregamento. O teste fisico de escrita na V75 ainda precisa ser executado.
