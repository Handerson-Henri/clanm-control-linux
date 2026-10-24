# Como contribuir

## Relatar um problema

Abra uma issue com modelo exato, identificador USB (`lsusb`), distribuição, sessão Wayland/X11 e versão do aplicativo. Descreva a ação, o resultado esperado e o observado. Para problemas de cor, informe modo, brilho e código hexadecimal. Não publique arquivos pessoais, senhas, sessões ou capturas de digitação.

Diga o nível da validação: pacote gerado, USB aceitou, leitura retornou, resultado físico observado. Esses níveis não são equivalentes.

## Alterar o código

1. Crie um fork e uma branch para a mudança.
2. Mantenha encoders em `clanm/protocol.py`, codificação em `clanm/mouse_codec.py`, transporte em `clanm/backend.py` e interface em `clanm/ui.py`.
3. Cores e tipografia da interface pertencem a `clanm/design.py`. Cores dos LEDs são dados do usuário.
4. Adicione testes proporcionais e execute:

   ```bash
   PYTHONPATH=vendor:. python3 -m unittest discover -s tests -v
   ```

5. Para UI, confira tema claro/escuro, navegação por teclado e ações visíveis em janela menor.
6. Abra um pull request descrevendo comportamento, testes e limitações.

## Contratos do hardware

- Abrir, escolher cor e carregar perfil não podem escrever no dispositivo.
- O caminho público do mouse aceita somente modo, cor, brilho e velocidade e comandos de iluminação. Não reintroduza envio de perfil completo para alterar apenas LEDs.
- Preserve os drivers de entrada; não resete o dispositivo nem remova as interfaces principais do kernel.
- Antes de uma alteração no teclado, preserve os parâmetros de luz que podem ser lidos e permita recuperação.
- Não chame perfil de exemplo de padrão de fábrica sem evidência do fabricante ou leitura original verificada.
- Não publique DLLs, instaladores, firmware, capturas de terceiros ou backups pessoais.

Código sob GPL-2.0-or-later; preserve os créditos de terceiros.
