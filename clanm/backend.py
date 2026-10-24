"""Transporte USB/HID limitado aos identificadores do kit detectado."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import select
import time
from .protocol import keyboard_packet, mouse_lighting_sequence

KEYBOARD=(0x320f,0x5078)
MOUSE=(0x04d9,0xa09f)
STATE=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'clanm-control'

def detect():
    result={'keyboard':None,'mouse':None}
    for device in Path('/sys/bus/usb/devices').iterdir():
        try:
            pair=(int((device/'idVendor').read_text(),16),int((device/'idProduct').read_text(),16))
        except (OSError,ValueError):
            continue
        if pair not in (KEYBOARD,MOUSE): continue
        label='keyboard' if pair==KEYBOARD else 'mouse'
        bus=int((device/'busnum').read_text());num=int((device/'devnum').read_text())
        node=Path(f'/dev/bus/usb/{bus:03d}/{num:03d}')
        entry={'usb_id':f'{pair[0]:04x}:{pair[1]:04x}','connected':True,'access':os.access(node,os.R_OK|os.W_OK),'node':str(node)}
        if label=='keyboard':
            entry.update(access=False,node=None)
            for raw in Path('/sys/class/hidraw').glob('*'):
                real=(raw/'device').resolve()
                if device.resolve() not in real.parents: continue
                interface=next((p for p in real.parents if (p/'bInterfaceNumber').is_file()),None)
                if interface is not None and (interface/'bInterfaceNumber').read_text().strip()=='01':
                    desc=(raw/'device/report_descriptor').read_bytes()
                    if bytes.fromhex('061cff') not in desc or bytes.fromhex('8504') not in desc: continue
                    node=Path('/dev')/raw.name
                    entry.update(node=str(node),access=os.access(node,os.R_OK|os.W_OK))
        result[label]=entry
    return result

@contextmanager
def operation_lock():
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/'hardware.lock').open('w') as file:
        try: fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc: raise RuntimeError('Outra operação USB está em andamento.') from exc
        yield


def keyboard_exchange(fd, packet):
    if os.write(fd,packet)!=64:raise IOError('Escrita HID incompleta.')
    deadline=time.monotonic()+1
    while time.monotonic()<deadline:
        ready,_,_=select.select([fd],[],[],max(0,deadline-time.monotonic()))
        if not ready:break
        answer=os.read(fd,64)
        if len(answer)==64 and answer[0]==4 and answer[3]==packet[3]:
            if answer[7] in (254,255):raise IOError('O teclado recusou o comando RGB.')
            return answer
    raise TimeoutError('O teclado não confirmou o comando RGB.')


def keyboard_command(command,size=0,offset=0):
    packet=bytearray(64);packet[0]=4;packet[3]=command;packet[4]=size
    packet[5:7]=offset.to_bytes(2,'little')
    packet[1:3]=sum(packet[3:]).to_bytes(2,'little')
    return bytes(packet)


def apply_keyboard(config):
    packet=keyboard_packet(config)
    device=detect()['keyboard']
    if not device or not device['node']:raise RuntimeError('CL-TK87 compatível não encontrado.')
    if not device['access']:raise PermissionError('Use Liberar acesso USB e reconecte o teclado se necessário.')
    with operation_lock():
        fd=os.open(device['node'],os.O_RDWR|os.O_NONBLOCK)
        try:
            keyboard_exchange(fd,keyboard_command(1))
            try:
                before=keyboard_exchange(fd,keyboard_command(5,8,1))[8:16]
                save_undo('keyboard',{'raw':list(before)})
                keyboard_exchange(fd,packet)
                readback=keyboard_exchange(fd,keyboard_command(5,8,1))
                if readback[8:16]!=packet[8:16]:raise IOError('A leitura RGB não corresponde aos valores enviados.')
            finally:
                keyboard_exchange(fd,keyboard_command(2))
        finally:os.close(fd)
    save_applied('keyboard',config)
    return 'Teclado: ajustes enviados e leitura RGB conferida. Confira a iluminação.'


def apply_mouse(config):
    operations=mouse_lighting_sequence(config)
    return send_mouse_lighting(config,operations)


def send_mouse_lighting(config,operations):
    device=detect()['mouse']
    if not device: raise RuntimeError('Mouse 04d9:a09f não encontrado.')
    if not device['access']: raise PermissionError('Use Liberar acesso USB e reconecte o mouse se necessário.')
    import usb.core
    import usb.util
    with operation_lock():
        previous=last_lighting('mouse')
        if previous:save_undo('mouse',{'config':previous})
        dev=usb.core.find(idVendor=MOUSE[0],idProduct=MOUSE[1])
        if dev is None: raise RuntimeError('Mouse desconectado.')
        detached=False;claimed=False
        try:
            interface=dev.get_active_configuration()[(2,0)]
            endpoints=[ep for ep in interface if ep.bEndpointAddress==3 and ep.wMaxPacketSize==64]
            if interface.bInterfaceClass!=3 or not endpoints:
                raise RuntimeError('Interface USB diferente da esperada; operação cancelada.')
            # Não reseta o USB nem remove drivers das interfaces 0/1 (ponteiro/teclas).
            if dev.is_kernel_driver_active(2):
                dev.detach_kernel_driver(2);detached=True
            usb.util.claim_interface(dev,2);claimed=True
            for op,data in operations:
                if op=='control':
                    sent=dev.ctrl_transfer(0x21,9,0x0300,2,data,timeout=1000)
                else:
                    sent=dev.write(3,data,timeout=1000)
                if sent!=len(data): raise IOError('Transferência USB incompleta; reaplique um perfil conhecido.')
                time.sleep(0.01)
        finally:
            try:
                if claimed: usb.util.release_interface(dev,2)
            finally:
                try:
                    if detached: dev.attach_kernel_driver(2)
                finally: usb.util.dispose_resources(dev)
    save_applied('mouse',config)
    return 'Mouse: somente iluminação enviada. DPI, sensibilidade e botões não foram escritos.'


def default_config():
    from .protocol import DEFAULT_BUTTONS
    return {'keyboard':{'mode':'Cor fixa','color':'#55aaff','brightness':3,'speed':3,'direction':0,'random':False},
            'mouse':{'mode':'Cor fixa','color':'#55aaff','dpi':[800,1200,1600,2400,3200,6400],
                     'active':1,'count':6,'polling':1000,'lod':2,'debounce':4,'buttons':list(DEFAULT_BUTTONS)}}


def atomic_json(path,value):
    import tempfile
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.profile-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as out: json.dump(value,out,ensure_ascii=False,indent=2)
        os.replace(tmp,path)
    finally:
        if Path(tmp).exists():Path(tmp).unlink()


def save_applied(kind,config):
    path=STATE/'last-applied.json'
    try:data=json.loads(path.read_text())
    except (OSError,ValueError):data={}
    data[kind]={**data.get(kind,{}),**config}
    atomic_json(path,data)


def last_lighting(kind):
    try:
        config=json.loads((STATE/'last-applied.json').read_text())[kind]
        return {key:config[key] for key in ('mode','color')}
    except (OSError,ValueError,KeyError,TypeError):return None


def save_undo(kind,snapshot):
    path=STATE/'undo-lighting.json'
    try:data=json.loads(path.read_text())
    except (OSError,ValueError):data={}
    data[kind]=snapshot
    atomic_json(path,data)


def undo_available(kind):
    try:return kind in json.loads((STATE/'undo-lighting.json').read_text())
    except (OSError,ValueError):return False


def undo_lighting(kind):
    try:snapshot=json.loads((STATE/'undo-lighting.json').read_text())[kind]
    except (OSError,ValueError,KeyError) as exc:raise ValueError('Não há alteração anterior salva nesta versão. Use Voltar ao azul testado.') from exc
    if kind=='mouse':
        return apply_mouse(snapshot['config'])
    if kind!='keyboard':raise ValueError('Dispositivo desconhecido.')
    raw=bytes(snapshot['raw'])
    if len(raw)!=8:raise ValueError('Cópia de iluminação inválida.')
    device=detect()['keyboard']
    if not device or not device['access']:raise PermissionError('Teclado sem acesso USB.')
    packet=bytearray(keyboard_command(6,8,1));packet[8:16]=raw
    packet[1:3]=sum(packet[3:]).to_bytes(2,'little')
    with operation_lock():
        fd=os.open(device['node'],os.O_RDWR|os.O_NONBLOCK)
        try:
            keyboard_exchange(fd,keyboard_command(1))
            try:
                current=keyboard_exchange(fd,keyboard_command(5,8,1))[8:16]
                keyboard_exchange(fd,packet)
                if keyboard_exchange(fd,keyboard_command(5,8,1))[8:16]!=raw:
                    raise IOError('O teclado não confirmou a restauração.')
            finally:keyboard_exchange(fd,keyboard_command(2))
        finally:os.close(fd)
        # Só substitui a cópia anterior depois que a restauração foi confirmada.
        save_undo('keyboard',{'raw':list(current)})
    from .protocol import KEYBOARD_MODES
    name=next((name for name,mode in KEYBOARD_MODES.items() if mode==raw[0]),None)
    if name and raw[1]<=5 and raw[2]<=4 and raw[3] in (0,1):
        save_applied('keyboard',{'mode':name,'speed':5-raw[1],'brightness':4-raw[2],
                               'direction':raw[3],'random':bool(raw[4]),'color':'#'+raw[5:8].hex()})
    return 'Iluminação anterior do teclado restaurada e conferida por leitura.'
