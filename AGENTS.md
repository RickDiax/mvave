# MK300 Studio — criação e entrega de timbres

O fluxo principal é pedir música/artista ao ChatGPT e receber o preset na MK-300. O editor manual é auxiliar. A interface possui Receber timbres, Meus timbres, Editor e Configurações. Não inserir presets pessoais fixos, contas, portas ou destinos de exemplo como se fossem os dados de todo usuário.

Para gerar e enviar um timbre:

1. Consulte a planilha MK-300 fornecida pelo usuário quando acessível, além de `studio/catalog.json`, `automation/catalog.sha256` e `automation/LEIA-ME.md` atuais. Respeite números de tela versus índices zero-based. Não presumir que toda unidade tem o mesmo conteúdo em AMP/CAB.
2. Pesquise a música/artista em fontes pertinentes. Separe informações documentadas das aproximações. Considere o instrumento informado pelo usuário; não presumir Strat para todos. Não invente fontes ou fidelidade comprovada.
3. Obtenha do vínculo copiado do Studio o **repositório e o channel_id** do computador. Use o vínculo já presente na conversa quando disponível; não peça de novo sem necessidade. Se ainda não houver vínculo, prepare a receita e peça somente esse vínculo antes de publicá-la. Não invente um canal.
4. Publique a receita no arquivo `automation/channels/CHANNEL_ID.json` do repositório indicado. Envelope `mk300-tone-inbox-2` e job `mk300-tone-job-2` devem conter o mesmo `channel_id`. Não publicar no antigo `automation/inbox.json` nem em outros canais. O destino é reservado localmente, nunca informado no job.
5. Novo UUID e datas atuais com fuso para cada job; validade máxima de 24 horas. Pedidos antigos à ativação são ignorados. Há um pendente por canal. Não publicar várias substituições seguidas sem instrução do usuário.
6. O usuário pediu geração e envio autônomos quando solicitar um timbre. Não pedir confirmação por preset se houver vínculo, escopo autorizado e receptor ativo informado. O backend mantém backup antes de escrever, conferência do destino, preservação dos bytes/controles e identificação persistente contra repetição.
7. Diga “receita enviada ao canal do seu Studio” após publicar. Não afirmar gravação física sem relatório ou confirmação explícita do usuário: o resultado USB não retorna automaticamente ao ChatGPT.

Preserve atribuições existentes Ctrl A/B e expressão; não alegue reprogramá-las. NAM/AM2/IR não são importados por esse caminho. Exige Windows, programa aberto, internet, acesso do ChatGPT ao repositório e MK-300 conectada.

Alterações no aplicativo devem rodar os testes pertinentes e manter isolamento de canais. Não publicar receita ativa de teste sem pedido musical real. Não migrar dados de usuário apagando a biblioteca ou seus presets salvos.
