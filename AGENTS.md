# MK-300: objetivo e fluxo de criação de timbres

O usuário quer pedir um timbre de música/artista no ChatGPT e recebê-lo na MK-300 automaticamente. Não tratar o projeto apenas como um editor manual nem pedir ao usuário que copie parâmetros ou importe JSON para cada timbre.

Para pedidos musicais com envio ao Studio:

1. Consulte a planilha do usuário `MK-300_M-VAVE_V73_PTBR.xlsx` quando acessível. Ela é a referência de modelos pedida pelo usuário. Leia `studio/catalog.json`, `automation/catalog.sha256` e `automation/LEIA-ME.md` da versão atual antes de gerar uma receita. Não confundir números da tela com índices zero-based de protocolo.
2. Pesquise a música/artista e os equipamentos/efeitos em fontes pertinentes. Distingua informações documentadas de aproximações para a pedaleira. Considere a Strat com single coils informada pelo usuário. Não invente fontes ou fidelidade sonora comprovada.
3. Monte uma receita compatível com os parâmetros e faixas do catálogo. Preserve as atribuições Ctrl A/B existentes; não alegue tê-las reprogramado. Para controles novos ainda não decodificados, explique a limitação.
4. Quando o pedido autorizar o envio, publique um novo job em `automation/inbox.json`, no repositório RickDiax/mvave, usando o protocolo documentado. O usuário já definiu que pedir a criação e envio de um timbre deve acionar esse fluxo. Não precisa de confirmação por preset se o receptor local estiver ativo e o pedido estiver no escopo solicitado. O destino é reservado no programa, não no job.
5. Use novo UUID e datas atuais com fuso a cada pedido; o receptor ignora pedidos anteriores à ativação. A caixa de entrada contém apenas o pedido mais recente. Não publique vários timbres seguidos para a mesma posição sem o usuário pedir esse comportamento.
6. Após publicar, diga “receita enviada ao Studio pelo GitHub”. Só afirme gravação física verificada se houver retorno do Studio ou confirmação explícita do usuário. O ChatGPT não recebe automaticamente o resultado USB nesta versão.

O receptor exige computador ligado, programa aberto, internet e pedaleira USB conectada. NAM/AM2/IR não são importados automaticamente nesta versão. Não gerar pedidos ativos para testes de código; a caixa de entrada de desenvolvimento deve continuar com `job: null` até um pedido musical real do usuário.

Alterações no receptor devem conservar backup antes da primeira escrita, validação do destino, preservação dos controles/bytes desconhecidos, identificação persistente de pedidos processados e ausência de repetição de escrita após falha. Rode os testes pertinentes antes de publicar.
