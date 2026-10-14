# Primeiro teste: Windows e MK-300 V75

Este teste lista portas MIDI e consulta o bloco global e o preset atualmente editado. Nao carrega, salva ou substitui presets, nao envia notas e nao modifica configuracoes globais. O firmware V75 foi informado pelo usuario; o script nao detecta a versao.

## Executar

1. Baixe o ZIP desta versao do repositorio e extraia tudo para uma pasta local. Nao execute dentro do ZIP.
2. Instale Python 3.11 ou superior pelo site https://www.python.org/downloads/windows/ se necessario, incluindo o Python Launcher.
3. Entre em `windows` e abra `instalar.cmd`. Ele cria um ambiente local e instala somente `mido` e `python-rtmidi`. Requer internet. Nao precisa instalar o projeto completo, Git ou tone-analyzer neste primeiro teste.
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
