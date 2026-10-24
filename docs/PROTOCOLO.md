# Protocolo, origem e validação

## CL-TK87

Identificação física: `320f:5078`, revisão USB 1.03, interface 1, usage page FF1C, report 4 com 64 bytes. Não abrir a interface principal 0 para ler digitação.

O pacote de parâmetro usa comando 06, tamanho em byte 4, offset little-endian em 5–6, dados a partir de 8. Checksum é a soma unsigned de bytes 3–63, em little-endian nos bytes 1–2.

Nesta variante, o efeito começa no parâmetro **1**, não em 0. A ferramenta altera somente oito parâmetros a partir de 1: modo, velocidade invertida, brilho invertido, direção, aleatório e RGB. A alteração usa início 01, escrita 06, leitura 05 e finalização 02. O fluxo confere a leitura dos oito bytes antes de considerar a transferência concluída. Uma resposta HID recebida sozinha não é confirmação visual.

O mapa do software oficial identifica estático como 6; brilho no fio é `4-brilho`, velocidade no fio é `5-velocidade`. O primeiro encoder genérico deixou o teclado colorido girando. Encerrar a operação não resolveu sozinho; corrigir o offset e a ordem dos campos resolveu. O usuário confirmou azul fixo com RGB 0000FF.

Referência oficial consultada: [CL-TK87](https://clanm.com.br/drivers/teclado-gamer-cl-tk87-cod-descontinuado/). O pacote foi extraído para análise estática, sem executar seu instalador no sistema e sem redistribuir seus arquivos. Referência aberta: [OpenRGB Evision](https://github.com/robinvandernoord/OpenRGB-7E57/tree/master/Controllers/EVisionKeyboardController).

## CL-MK043

Identificação física: `04d9:a09f`, revisão USB 3.01. Interfaces 0/1 permanecem com usbhid. A ferramenta reivindica somente a interface 2, HID com endpoint OUT 03 e tamanho máximo 64. Não chama reset nem set_configuration no dispositivo.

A configuração usa 16 mensagens de controle HID SET_REPORT: `bmRequestType=21`, request 09, value 0300, index 2, payload 8 bytes. Dados maiores usam oito mensagens interrupt OUT de 32 bytes. As mensagens de controle são codificadas por permutação, XOR, rotação e offsets. O identificador público dessa codificação no driver CL-MK043 difere do usado no projeto LUOM consultado. Os valores são constantes de um protocolo público do dispositivo, não credenciais do usuário.

A função independente em `mouse_codec.py` traduz os comandos da referência para a variante Clanm. Cada comando tem soma dos oito bytes decodificados igual a FF. Os testes identificaram erros em algumas combinações de LOD/debounce da tabela de referência: a ferramenta calcula novamente o checksum na forma decodificada antes de codificar, em vez de alterar bytes codificados por uma fórmula aproximada.

No primeiro teste, o USB aceitou mensagens de outra variante sem alterar os LEDs. Com a codificação CL-MK043, o usuário confirmou **LEDs apagados** e depois **azul fixo**. Não há leitura de confirmação dos parâmetros do mouse. DPI, polling, LOD, tempos e mapeamentos ainda exigem ensaios físicos individuais; os testes atuais conferem estrutura e limites, não desempenho do sensor.

Cor fixa usa nove entradas iguais na paleta. Os seis níveis expostos têm codificação `(DPI/50)-1`; limites permitidos 50–12800, múltiplos de 50. A interface limita a seleção a seis níveis, sem expor o sétimo nível não configurável pela tabela usada. Existe proteção contra remover todas as funções de clique esquerdo.

Referência oficial: [Clanm Mouse King](https://clanm.com.br/drivers/mouse-gamer-king-cod-10057/), cujo instalador identifica CL-MK043. Referência aberta de sequência: [hampta/luom-g10-config](https://github.com/hampta/luom-g10-config).

## Aplicação e perfis

O aplicativo roda como usuário. A autenticação administrativa é usada somente pelo instalador de regras udev. A regra do teclado seleciona a interface 1 em duas etapas; a regra do mouse concede acesso ao dispositivo USB específico para permitir o controle da interface 2. Usa uaccess, sem MODE=0666 e sem adicionar o usuário a grupos.

Perfis JSON são dados, nunca código executável; versão 1, tamanho máximo de importação 64 KiB. A importação valida os parâmetros antes de preencher a tela e não escreve no hardware. Os últimos valores enviados são gravados em `~/.config/clanm-control/last-applied.json`; não são uma cópia do estado original de fábrica.

A interface bloqueia o fechamento normal durante uma transferência para não interromper uma sequência. Um lock impede operações USB simultâneas por instâncias deste aplicativo. Outros programas RGB devem ficar fechados durante a aplicação para evitar disputa de comandos.

## Verificado nesta máquina

- Identificadores USB, descritores e acesso como usuário.
- Cor fixa azul no teclado, confirmada pelo usuário; leitura de parâmetros correspondente.
- Mouse apagado e azul fixo, confirmados pelo usuário.
- Drivers de ponteiro e teclas do mouse ativos antes e depois da transferência.
- Testes unitários de encoders, limites, checksum, codificação Clanm e preservação dos dados do perfil.
- Interface GTK renderizada em display de teste e instalação por usuário.

Não testado: todas as combinações de efeitos, DPI medido, taxa efetiva, cada botão físico, macros, remapeamento do teclado e restauração em outra máquina. O projeto não faz atualização de firmware.

## Revisão 0.2: recuperação e isolamento de iluminação

Após o usuário relatar vermelho rosado no **teclado** e receio de alterar o mouse, a revisão foi feita sem enviar novos comandos aos periféricos. A cor registrada era A51D2D; a interface agora mostra o valor e oferece cores primárias puras. Não se afirma que isso, sozinho, resolva a aparência física.

O caminho ativo do mouse deixou de chamar `mouse_sequence`: usa `mouse_lighting_sequence`, que aceita exclusivamente modo/cor, emite somente registradores 0C e 0D e não emite interrupt OUT. Os controles avançados e efeitos não verificados foram removidos da interface. O encoder de perfil completo permanece como material histórico de pesquisa e testes, sem acesso pelo botão Aplicar.

Cor fixa agora usa RGB direto e seletor de cor única, sem o artifício da paleta repetida da versão anterior. Essa mudança reduz o escopo das escritas e corresponde às funções de iluminação do programa oficial; a nova transferência não foi testada fisicamente nesta revisão.

Antes de uma escrita de teclado, os oito parâmetros atuais são lidos e salvos em `undo-lighting.json`. Ao desfazer, são reaplicados e conferidos; se a leitura de retorno falhar, a cópia de recuperação é conservada. Para mouse, a cópia disponível é o último modo/cor enviado pelo aplicativo, não uma leitura do perfil original. O perfil azul é uma recuperação de iluminação, não restauração de fábrica.

## Revisão 0.4: efeitos nativos do MK043

A função de iluminação do executável oficial CL-MK043 distingue os IDs 0 a 11: desligado, fixo, respiração, neon, onda, reativo, rastro, vai e volta, deslizar, ioiô, mármore e estrela cadente. O controle continua restrito aos registros 0C (RGB) e 0D (efeito), sem interrupt OUT ou escrita de paletas. A tabela antiga de perfil completo não é usada para esses IDs.

Parâmetros decodificados do registro 0D (bytes 1–3), com velocidade `s` entre 0 e 4 e brilho `b` entre 0 e 255:

| IDs | Campos |
|---|---|
| 0 | 0, 0, 0 |
| 1, 5, 8, 11 | modo, b, 0 |
| 2, 3, 4 | modo, s, b |
| 6, 7 | modo, 2, 4-s |
| 9 | modo, b, (4-s)<<4 |
| 10 | modo, b, 4-s |

O comprimento de rastro é intermediário (2). Seletores de cor ficam em zero; modos que usam paleta dependem da paleta já gravada. A velocidade segue o slider lento–rápido do programa oficial, incluindo campos invertidos. A conferência atual cobre codificação, checksum, limites, importação antiga e comandos permitidos; não confirma aparência ou ritmo físico desses novos modos. Nenhum comando de hardware foi enviado para produzir esta revisão.

## Incidente e contenção 0.4.1

Após aplicar efeito novo, o usuário relatou perda de ponteiro e cliques; recuperar cor fixa restaurou o mouse. O último registro local é Respiração, brilho 255, velocidade 2. Há resets USB e aviso de interface não reivindicada no kernel. Isso não isola a causa. A hipótese de que os campos extraídos seriam suficientes para ativar animações não foi confirmada no hardware.

Todos os efeitos animados foram bloqueados no caminho ativo, antes do transporte, incluindo perfis importados e recuperação. A lista pública contém apenas fixo e desligado. Velocidade desativada. Nenhum comando de teste foi enviado nesta contenção.
