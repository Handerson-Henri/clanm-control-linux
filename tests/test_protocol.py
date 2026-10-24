import copy
import unittest
from unittest.mock import patch
from clanm.protocol import keyboard_packet,mouse_sequence,KEYBOARD_MODES,MOUSE_MODES
from clanm import backend

class ProtocolTests(unittest.TestCase):
    def setUp(self):self.config=backend.default_config()
    def test_keyboard_known_wire_packet_and_checksum(self):
        p=keyboard_packet(self.config['keyboard'])
        self.assertEqual(len(p),64)
        self.assertEqual(p[:16],bytes.fromhex('0416020608010000060201000055aaff'))
        self.assertEqual(int.from_bytes(p[1:3],'little'),sum(p[3:]))
    def test_keyboard_all_effects_and_bounds(self):
        for name in KEYBOARD_MODES:
            self.config['keyboard']['mode']=name
            self.assertEqual(len(keyboard_packet(self.config['keyboard'])),64)
        self.config['keyboard']['brightness']=5
        with self.assertRaises(ValueError):keyboard_packet(self.config['keyboard'])
    def test_mouse_dpi_encoding_and_sequence(self):
        ops=mouse_sequence(self.config['mouse'])
        self.assertEqual([kind for kind,data in ops].count('control'),16)
        self.assertEqual([kind for kind,data in ops].count('out'),8)
        outputs=[data for kind,data in ops if kind=='out']
        self.assertTrue(all(len(data)==32 for data in outputs))
        self.assertEqual(outputs[0][:27],bytes.fromhex('55aaff')*9)
        self.assertEqual(outputs[2][:8],bytes([15,23,31,47,63,127,0xbd,0x5f]))
        self.assertEqual(outputs[3][:8],bytes.fromhex('0100f0000100f100'))
    def test_all_mouse_effects(self):
        for mode in MOUSE_MODES:
            self.config['mouse']['mode']=mode
            self.assertEqual(len(mouse_sequence(self.config['mouse'])),24)
    def test_reject_invalid_dpi_and_left_click_loss(self):
        m=self.config['mouse']
        for dpi in [0,51,12850,1.5,True]:
            m['dpi'][0]=dpi
            with self.assertRaises(ValueError):mouse_sequence(m)
        m['dpi'][0]=800;m['buttons']=['Desativado']*6
        with self.assertRaises(ValueError):mouse_sequence(m)
    def test_active_slot_must_be_enabled(self):
        m=self.config['mouse'];m['count']=1;m['active']=1
        with self.assertRaises(ValueError):mouse_sequence(m)
    def test_validation_precedes_hardware_detection(self):
        m=self.config['mouse'];m['dpi'][0]=99
        with patch('clanm.backend.detect') as detect:
            with self.assertRaises(ValueError):backend.apply_mouse(m)
            detect.assert_not_called()
    def test_encoder_does_not_mutate_profile(self):
        old=copy.deepcopy(self.config)
        keyboard_packet(self.config['keyboard']);mouse_sequence(self.config['mouse'])
        self.assertEqual(self.config,old)
    def test_mouse_codec_matches_official_polling_vector(self):
        from clanm.mouse_codec import encode,decode,translate_reference
        raw=bytes.fromhex('01010000000000fd')
        self.assertEqual(encode(raw).hex(),'27242517d8fe0676')
        self.assertEqual(decode(encode(raw)),raw)
        self.assertEqual(translate_reference(bytes.fromhex('272bddffe8d57676')),encode(raw))
    def test_mouse_commands_checksum_and_parameter_combinations(self):
        from clanm.mouse_codec import decode
        m=self.config['mouse']
        for lod in [1,2,3]:
            for debounce in [1,2,3,4,5,6,7,8,9,10,20,100]:
                m['lod']=lod;m['debounce']=debounce
                for kind,data in mouse_sequence(m):
                    if kind=='control':self.assertEqual(sum(decode(data))&255,255)
    def test_color_input(self):
        for value in ['red','#fff','#zzzzzz','aa00000']:
            self.config['keyboard']['color']=value
            with self.assertRaises(ValueError):keyboard_packet(self.config['keyboard'])

if __name__=='__main__':unittest.main()
