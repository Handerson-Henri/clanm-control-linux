import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from clanm import backend
from clanm.protocol import mouse_lighting_sequence,keyboard_packet
from clanm.mouse_codec import decode

REAL_OPEN=os.open
REAL_CLOSE=os.close
def fake_open(path,*args,**kwargs):
    return 999 if path=='fake' else REAL_OPEN(path,*args,**kwargs)
def fake_close(fd):
    if fd!=999:REAL_CLOSE(fd)

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch=patch.object(backend,'STATE',Path(self.tmp.name))
        self.patch.start();self.addCleanup(self.patch.stop)
    def test_mouse_lighting_contains_only_two_lighting_registers(self):
        for color in ('#ff0000','#00ff00','#0000ff','#ffffff'):
            ops=mouse_lighting_sequence({'mode':'Cor fixa','color':color})
            self.assertEqual(len(ops),2)
            self.assertEqual([decode(data)[0] for kind,data in ops],[0x0c,0x0d])
            self.assertTrue(all(kind=='control' for kind,data in ops))
            self.assertEqual(decode(ops[0][1])[1:4],bytes.fromhex(color[1:]))
            for _,data in ops:self.assertEqual(sum(decode(data))&255,255)
    def test_rejects_full_profile_before_any_hardware_access(self):
        with patch.object(backend,'detect') as detect:
            with self.assertRaises(ValueError):backend.apply_mouse(backend.default_config()['mouse'])
            detect.assert_not_called()
    def test_mouse_off_does_not_touch_other_settings(self):
        ops=mouse_lighting_sequence({'mode':'Desligado','color':'#ff0000'})
        self.assertEqual(decode(ops[0][1])[1:4],bytes(3))
        self.assertEqual(decode(ops[1][1])[1:4],bytes(3))
    def test_red_keyboard_is_pure_red_on_the_wire(self):
        c=backend.default_config()['keyboard'];c['color']='#ff0000'
        self.assertEqual(keyboard_packet(c)[13:16],bytes((255,0,0)))
    def test_history_keeps_legacy_mouse_sensitivity(self):
        old=backend.default_config()['mouse']
        backend.save_applied('mouse',old)
        backend.save_applied('mouse',{'mode':'Desligado','color':'#0000ff'})
        value=json.loads((backend.STATE/'last-applied.json').read_text())['mouse']
        self.assertEqual(value['dpi'],old['dpi'])
        self.assertEqual(backend.last_lighting('mouse'),{'mode':'Desligado','color':'#0000ff','brightness':255,'speed':2})
    def test_keyboard_backup_is_saved_before_write(self):
        c=backend.default_config()['keyboard'];before=bytes((6,2,0,0,0,0,0,255))
        expected=keyboard_packet(c)
        def exchange(fd,packet):
            if packet[3]==6:
                snap=json.loads((backend.STATE/'undo-lighting.json').read_text())
                self.assertEqual(snap['keyboard']['raw'],list(before))
            answer=bytearray(64);answer[0]=4;answer[3]=packet[3]
            if packet[3]==5:answer[8:16]=before if exchange.reads==0 else expected[8:16];exchange.reads+=1
            return bytes(answer)
        exchange.reads=0
        with patch.object(backend,'detect',return_value={'keyboard':{'node':'fake','access':True}}),patch.object(backend.os,'open',side_effect=fake_open),patch.object(backend.os,'close',side_effect=fake_close),patch.object(backend,'keyboard_exchange',side_effect=exchange):
            backend.apply_keyboard(c)
        self.assertTrue(backend.undo_available('keyboard'))
    def test_undo_keeps_backup_if_device_readback_fails(self):
        target=bytes((6,2,0,0,0,0,0,255));current=bytes((5,3,0,0,0,255,0,0))
        backend.save_undo('keyboard',{'raw':list(target)})
        def exchange(fd,packet):
            answer=bytearray(64)
            if packet[3]==5:answer[8:16]=current
            return bytes(answer)
        with patch.object(backend,'detect',return_value={'keyboard':{'node':'fake','access':True}}),patch.object(backend.os,'open',side_effect=fake_open),patch.object(backend.os,'close',side_effect=fake_close),patch.object(backend,'keyboard_exchange',side_effect=exchange):
            with self.assertRaises(IOError):backend.undo_lighting('keyboard')
        self.assertEqual(json.loads((backend.STATE/'undo-lighting.json').read_text())['keyboard']['raw'],list(target))
    def test_no_false_factory_reset(self):
        self.assertFalse(backend.undo_available('mouse'))
        with self.assertRaises(ValueError):backend.undo_lighting('mouse')

    def test_mouse_undo_preserves_effect_speed_and_brightness(self):
        previous={'mode':'Respiração','color':'#ff0000','speed':4,'brightness':100}
        backend.save_applied('mouse',previous)
        self.assertEqual(backend.last_lighting('mouse'),previous)
        backend.save_undo('mouse',{'config':previous})
        with patch.object(backend,'send_mouse_lighting') as send:
            backend.undo_lighting('mouse')
            self.assertEqual(send.call_args.args[0],previous)
