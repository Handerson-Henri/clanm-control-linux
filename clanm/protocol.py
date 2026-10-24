"""Encoders puros. Nenhuma função deste módulo abre dispositivos.

Teclado: protocolo Evision documentado pelo OpenRGB (GPL-2.0-or-later).
Mouse: implementação independente das sequências USB documentadas por
hampta/luom-g10-config. Não inclui o driver Windows nem código desse projeto.
"""
KEYBOARD_MODES = {
    'Cor fixa': 6, 'Respiração': 5, 'Onda curta': 1, 'Onda longa': 2,
    'Roda de cores': 3, 'Ciclo de cores': 4, 'Reativo': 7,
    'Ondulação ao tocar': 8, 'Linha ao tocar': 9, 'Estrelas rápidas': 10,
    'Flores': 11, 'Arco-íris vertical': 12, 'Furacão': 13,
    'Acumular': 14, 'Estrelas lentas': 15, 'Visor': 16,
    'Surmount': 17, 'Arco-íris circular': 18,
}
MOUSE_MODES = {
    'Cor fixa': 'standard', 'Desligado': 'off', 'Respiração': 'breathing',
    'Neon': 'neon', 'Onda': 'wave', 'Reativo': 'key-reaction',
    'Rastro': 'trailing', 'Vai e volta': 'drag', 'Deslizar': 'slide',
    'Ioiô': 'yo-yo', 'Mármore': 'marbles', 'Estrela cadente': 'flying-star',
}
ACTIONS = {'Esquerdo':'0100f000', 'Direito':'0100f100', 'Meio':'0100f200',
           'Avançar':'0100f400', 'Voltar':'0100f300', 'Alternar DPI':'07000100',
           'Desativado':'00000000'}
DEFAULT_BUTTONS = ['Esquerdo','Direito','Meio','Avançar','Voltar','Alternar DPI']


def rgb(value):
    if not isinstance(value, str) or len(value) != 7 or not value.startswith('#'):
        raise ValueError('Cor deve ter o formato #RRGGBB.')
    try:
        return bytes.fromhex(value[1:])
    except ValueError as exc:
        raise ValueError('Cor inválida.') from exc


def keyboard_packet(config):
    mode = KEYBOARD_MODES[config['mode']]
    brightness, speed = int(config['brightness']), int(config['speed'])
    direction = int(config.get('direction', 0))
    if not 0 <= brightness <= 4 or not 0 <= speed <= 5 or direction not in (0,1):
        raise ValueError('Brilho, velocidade ou direção fora da faixa.')
    data = bytearray(64)
    data[0] = 4
    # CL-TK87 possui byte inicial de perfil antes dos controles de luz.
    # O driver oficial usa brilho invertido: 0 máximo, 4 desligado.
    data[3:6] = bytes((6, 8, 1))
    data[8:16] = bytes((mode, 5-speed, 4-brightness, direction, int(bool(config.get('random', False))))) + rgb(config['color'])
    data[1:3] = sum(data[3:]).to_bytes(2, 'little')
    return bytes(data)


def mouse_sequence(config):
    """Retorna operações (control ou out); valida tudo antes da primeira escrita."""
    levels = config['dpi']
    if len(levels) != 6 or any(type(v) is not int or not 50 <= v <= 12800 or v % 50 for v in levels):
        raise ValueError('Informe 6 níveis de DPI, de 50 a 12800, em múltiplos de 50.')
    active, count = int(config['active']), int(config['count'])
    if not 1 <= count <= 6 or not 0 <= active < count:
        raise ValueError('O nível ativo precisa estar entre os níveis habilitados.')
    buttons = config['buttons']
    if len(buttons) != 6 or any(x not in ACTIONS for x in buttons) or 'Esquerdo' not in buttons:
        raise ValueError('Mantenha pelo menos um botão com a função Esquerdo.')
    poll = {125:'272b85ff30d57676',250:'272ba5ffd0d57676',500:'272bd5ff00d57676',1000:'272bddffe8d57676'}[int(config['polling'])]
    slots = ['272b6dffe8257676','272b65ff00257676','272b7dfff8257676','272b75ffd0257676','272b4dffc8257676','272b45ffe0257676']
    counts = ['272b1dffe85576b6','272b15ff005576b6','272bedfff85576b6','272be5ffd05576b6','272bfdffc85576b6','272bf5ffe05576b6']
    effects = {
        'standard':'272b75ffe8356d6e','off':'272afdffe83577f6',
        'breathing':'272b2dff0035668e','neon':'272dcdffe83567f6',
        'wave':'272dd5fff834f68e','key-reaction':'272dadffc83567f6',
        'trailing':'272dadffd034f68e','drag':'272b35ffe0356686',
        'slide':'272b0dffd8356686','yo-yo':'272d0dff2835e7f6',
        'marbles':'272dbdff30357ff6','flying-star':'272d8dff40357ff6'}
    mode = MOUSE_MODES[config['mode']]
    color = rgb(config['color'])
    lod = int(config['lod'])
    if lod not in (1,2,3):
        raise ValueError('LOD precisa ser 1, 2 ou 3.')
    debounce = int(config['debounce'])
    debounce_table = {1:(0x2b,0x8d,0x76,0x86),2:(0x2b,0x9d,0x76,0x96),3:(0x2b,0x95,0x76,0x9e),4:(0x2b,0x6d,0x76,0xa6),5:(0x2b,0x65,0x76,0xae),6:(0x2b,0x7d,0x76,0xb6),7:(0x2b,0x4d,0x76,0xc6),8:(0x2b,0x15,0x76,0x1e),9:(0x2a,0xc5,0x76,0x4e),10:(0x2a,0x95,0x77,0x9e),20:(0x2a,0x55,0x77,0xde),100:(0x2b,0xb5,0x76,0x7e)}
    a,b,c,d = debounce_table[debounce]
    from .mouse_codec import decode, encode, REFERENCE_ID
    response = bytearray(decode(bytes((0x27,a,b,0xff,0,0xfd,c,d)),REFERENCE_ID))
    response[1] = 1 if lod==1 else 2
    response[7] = (255-sum(response[:7]))&255
    operations=[]
    def ctrl(value):
        from .mouse_codec import translate_reference
        operations.append(('control', translate_reference(bytes.fromhex(value) if isinstance(value,str) else value)))
    def out(value): operations.append(('out', bytes.fromhex(value) if isinstance(value,str) else bytes(value)))
    ctrl('2727d5fff4e57676')
    ctrl('252db5fff8eae6ee' if lod==3 else '252d75fff8ea26ee')
    ctrl('272bd5ffe8ed7676');ctrl(poll);ctrl(slots[active])
    ctrl('272b6dfff03d7676' if mode=='off' else '272b85049842556e')
    ctrl(effects[mode]);ctrl('272a8dfff05d7636')
    palette=bytearray(32)
    if mode=='standard':
        palette[:27]=color*9
    else:
        palette[:27]=bytes.fromhex('ff000000ff000000ffffff00ff00ff00ffffff8000ffffff00000000')[:27]
    out(palette);ctrl('272a85ffe85d7636')
    out('00ff000000ffff0000ffff0000ffffff00ffffffffffffff0000000000000000')
    ctrl(counts[count-1])
    dpi=bytearray(32);dpi[:6]=bytes(v//50-1 for v in levels);dpi[6:8]=bytes((0xbd,0x5f));out(dpi)
    ctrl('272d55ffe86d7876')
    out(''.join(ACTIONS[v] for v in buttons)+'0700010007000200')
    out('0b0000000d000000000000000000000000000000000000000400010004000200')
    ctrl('272d2dff006d7876');out(bytes(32))
    out('0b0000000d000000000000000000000000000000000000000000000000000000')
    ctrl('272bf5fff85d76d6');out(bytes([255])+bytes(31))
    operations.append(('control',encode(response)))
    ctrl('272c6d024022ccd6');ctrl('272bb5fff0057676')
    assert all(len(data)==(8 if op=='control' else 32) for op,data in operations)
    return operations


# Numeração do CL-MK043 oficial; não confundir com tabelas de outras variantes.
MOUSE_LIGHT_EFFECTS = {
    'Cor fixa':1, 'Desligado':0, 'Respiração':2, 'Neon':3, 'Onda':4,
    'Reativo':5, 'Rastro':6, 'Vai e volta':7, 'Deslizar':8,
    'Ioiô':9, 'Mármore':10, 'Estrela cadente':11,
}
MOUSE_SPEED_MODES = {2,3,4,6,7,9,10}
MOUSE_BRIGHTNESS_MODES = {1,2,3,4,5,8,9,10,11}


def mouse_lighting_sequence(config):
    """Somente RGB 0C e efeito 0D. Nunca DPI, botões ou paletas."""
    from .mouse_codec import encode
    if not {'mode','color'} <= set(config) or set(config)-{'mode','color','speed','brightness'}:
        raise ValueError('A iluminação aceita somente modo, cor, brilho e velocidade.')
    try:mode=MOUSE_LIGHT_EFFECTS[config['mode']]
    except (KeyError,TypeError) as exc:raise ValueError('Efeito de iluminação desconhecido.') from exc
    speed=config.get('speed',2);brightness=config.get('brightness',255)
    if type(speed) is not int or not 0<=speed<=4:
        raise ValueError('A velocidade deve ser um nível inteiro de 0 a 4.')
    if type(brightness) is not int or not 0<=brightness<=255:
        raise ValueError('O brilho deve ser um inteiro de 0 a 255.')
    color=rgb(config['color']) if mode else bytes(3)
    def command(code,params):
        raw=bytearray(8);raw[0]=code;raw[1:1+len(params)]=params
        raw[7]=(255-sum(raw[:7]))&255
        return ('control',encode(raw))
    # Formatos por modo extraídos da função de luz do CL-MK043 oficial.
    # A frequência crescente usa campos distintos, alguns invertidos.
    if mode==0:effect=bytes(3)
    elif mode in (1,5,8,11):effect=bytes((mode,brightness,0))
    elif mode in (2,3,4):effect=bytes((mode,speed,brightness))
    elif mode in (6,7):effect=bytes((mode,2,4-speed))  # comprimento intermediário
    elif mode==9:effect=bytes((mode,brightness,(4-speed)<<4))
    elif mode==10:effect=bytes((mode,brightness,4-speed))
    return [command(0x0c,color),command(0x0d,effect)]
