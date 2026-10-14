# MK300 Studio

**Fluxo principal: pedir um timbre ao ChatGPT e receber por USB.** Veja [ativar a recepção automática](../automation/LEIA-ME.md). A interface agora destaca o receptor; o editor manual abaixo serve para conferir e ajustar versões.

Aplicativo local para Windows: usa o navegador como interface e Python para conversar com a MK-300 pela USB. A conexão USB e os backups ficam no computador; a recepção automática usa o seu GitHub como ponte.

## Abrir

1. Baixe o [ZIP completo do projeto](https://github.com/RickDiax/mvave/archive/refs/heads/main.zip) e extraia tudo. As pastas `studio`, `windows` e `mvave` precisam ficar juntas.
2. Conecte a pedaleira e feche M-EFCS/DAW.
3. Dê dois cliques em **`ABRIR-STUDIO.cmd`**, na pasta principal. Ele chama a preparação das dependências se necessário, usando Python 3.12 ou 3.11 x64. Se faltar o Python compatível, siga a orientação exibida e abra novamente. Na primeira preparação, pressione uma tecla quando solicitado para continuar.
4. O navegador abre automaticamente. Mantenha a janela do programa aberta. Também é possível usar `windows/abrir-studio.cmd` depois da instalação.
5. Escolha entrada **USB-Midi 0** e saída **USB-Midi 1**, conforme as portas observadas nesta unidade, e clique **Ler atual**. Também pode ler uma posição salva de 1 a 160.

O programa escuta apenas em `127.0.0.1`. Se a porta 8765 estiver ocupada, escolhe outra. Não precisa de Web MIDI no navegador. Feche o programa com Ctrl+C na janela de execução.

### Ícone e atalho do Windows

Execute **`CRIAR-ATALHO.cmd`** uma vez, na pasta principal. Ele cria o atalho **MK300 Studio** com o ícone do aplicativo na Área de Trabalho e na própria pasta. Depois, use esse atalho para abrir. Se mover a pasta do projeto, execute novamente para atualizar os caminhos. Não exige privilégios de administrador.

O Studio usa a mesma identidade no cabeçalho, na aba do navegador e no atalho. Os efeitos e comandos usam ícones SVG locais, sem fontes de ícones ou serviços externos. O arquivo `studio/assets/mk300-studio.ico` inclui resoluções de 16 a 256 pixels para o Windows; `brand.svg` é o original vetorial. Os ícones dos arquivos JSON no Explorador seguem a associação de arquivos do Windows; esta atualização não modifica essas associações.

## Criar e gravar

- Leia um preset como ponto de partida: isso conserva os bytes e controles que ainda não foram totalmente decodificados.
- Clique em cada bloco para trocar o modelo, ativar/desativar e ajustar seus parâmetros. **Antes/Depois** move o bloco na cadeia. O rascunho não altera o áudio em tempo real.
- **Salvar versão** cria um novo item na biblioteca. **Exportar timbre** gera um JSON do Studio para compartilhar ou guardar. Esses arquivos não são presets nativos do M-EFCS.
- Escolha a posição de destino e clique **Conferir destino e gravar**. Confira nome e posição na janela e clique **Gravar na pedaleira**.
- O programa relê o destino antes de escrever; se ele mudou desde a conferência, cancela. Salva um backup, envia o preset inteiro, confirma e compara os 448 bytes lidos de volta. Não altera configurações globais nem carrega o preset automaticamente.
- Para ouvir o resultado, selecione outra posição na pedaleira e volte ao destino gravado. Alterações no rascunho só passam ao hardware depois da gravação.

## Little Wing e Ctrl A/B

O ponto de partida Little Wing inclui Plexi, gabinete correspondente, UniVibe, reverb e MW-FACE inicialmente desligado, com Fuzz **25** e Level **35**. São sugestões de timbre, não medições de um equipamento de Hendrix.

Os controles são preservados do preset lido/importado. Se a posição 137 da sua unidade já está com **Ctrl A → MOD/UniVibe** e **Ctrl B → DS/distorção**, leia essa posição antes de criar, ou use **Herdar controles da posição 137**. Esse botão copia também expressão e os outros dados da região de controles para o rascunho. Confira as atribuições na pedaleira depois de gravar. Trocar DS por outro efeito dentro do mesmo bloco mantém a atribuição ao bloco.

## Biblioteca e restauração

Biblioteca: `%LOCALAPPDATA%\MK300Studio\timbres`.
Backups: `%LOCALAPPDATA%\MK300Studio\backups`.

Cada backup registra destino, imagem original, imagem planejada e resultado. Para recuperar o conteúdo anterior, use **Importar / restaurar JSON** e escolha o backup. O Studio carrega a imagem **anterior** no rascunho; confira e grave na posição desejada. A importação sozinha não grava nada.

Se houver timeout depois do envio, a situação pode ser parcial. O backup registra `uncertain`. Leia a posição para conferir antes de tentar gravar outra vez; não há repetição automática da escrita.

## Limites desta versão

- O protocolo foi observado na V73. Nesta unidade V75, leitura e gravação/cópia de presets já funcionaram. O novo aplicativo foi testado com simulações e automação dos eventos da interface usando seu diagnóstico real. Não houve teste de renderização em navegador ou teste físico do novo aplicativo; o fluxo completo ainda precisa ser conferido na pedaleira.
- AMP/CAB/DS seguem a planilha fornecida. Nomes e conteúdo dependem do banco instalado: **71OD-Fman100 / 63FimanVt** foram confirmados pelo usuário; **MW-FACE índice 47** e **UniVibe índice 11** foram observados no diagnóstico. Outros mapeamentos ainda precisam de conferência no aparelho. O catálogo é referência, não detecção automática dos modelos.
- Valores numéricos editáveis usam as faixas do catálogo, com escalas informadas. Valores originais fora da faixa são conservados até você editar. Enumerações sem encoding confirmado ficam bloqueadas; modelos que dependem delas devem ser selecionados no aparelho e lidos novamente.
- Não cria nem converte capturas NAM/AM2. Importação de capturas e IR continua pelo M-EFCS. Um preset aponta para o conteúdo do slot AMP/CAB; exportar o preset não inclui a captura ou IR daquele slot.
- Ainda não há desenho das atribuições Ctrl A/B, monitoração de áudio ou pré-escuta de efeitos no navegador.

## Testes de desenvolvimento

Na raiz do projeto, execute `python -m unittest discover -s tests -p 'test_studio.py' -v`. Eles verificam preservação dos bytes, validação dos parâmetros, receita Little Wing, biblioteca/restauração, backup antes de escrita, interrupção em caso de falha e proteção da API local.

Com Node.js disponível, `node tests/test_studio_ui.cjs` verifica os eventos da interface contra a API HTTP real, com DOM e USB simulados. Não exige pacotes npm. Opcionalmente aceita o caminho de um JSON de diagnóstico para usar um preset real como entrada.
