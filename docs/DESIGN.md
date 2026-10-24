# Adaptação do Design System

Referência consultada no repositório local Prints & Paints: `docs/agents/UI.md`, `client/src/App.vue` e `docs/erp/UX_SIDEBAR.md`. O sistema Prints & Paints foi utilizado somente como referência; seus arquivos não foram alterados.

A adaptação mantém o aplicativo nativo GTK, sem introduzir Vue/Vuetify ou trocar o transporte USB. Os componentes web não podem ser usados diretamente no GTK; seus princípios foram traduzidos para controles nativos acessíveis.

## Aplicado

- Paleta índigo e superfícies neutras do sistema, com tokens centralizados em `clanm/design.py`.
- Fonte Inter com fallback Sans, hierarquia de títulos, campos e informações auxiliares.
- Espaçamento na escala 4, 8, 12, 16, 24 e 32.
- Temas claro/escuro com preferência local, sem acesso ao hardware.
- Ações principais fixas no rodapé, fora do conteúdo rolável.
- Foco visível, nomes acessíveis nos campos e rótulos visíveis nos botões.
- Estados de conexão expressos em texto; o status não depende só da cor.
- Feedback local, bloqueio de envio duplicado e confirmações de recuperação preservados.
- Cor escolhida para LEDs tratada como dado do usuário, separada dos tokens da interface.

## Verificação

Interface renderizada nos temas claro e escuro, incluindo janela de aproximadamente 800 px de largura. Ações de aplicação e recuperação conferidas dentro da área visível. As combinações de texto principal/secundário e botões primários superam contraste 4,5:1 nas duas paletas; o texto da aba ativa escura usa uma tonalidade mais clara para atingir contraste adequado.

A simulação verificou que alternar o tema e renderizar a interface não chama os aplicadores USB. Os 19 testes de protocolo/recuperação continuaram passando. Esta revisão não enviou comandos aos periféricos.

## Validação física atualizada

O usuário confirmou conseguir colocar vermelho no teclado e no mouse antes desta revisão visual. Os demais limites de efeitos e recuperação permanecem descritos no README. A tela de prévia é ilustrativa e não representa leitura fotométrica do hardware.
