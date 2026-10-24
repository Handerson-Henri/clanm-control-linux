import unittest
from unittest.mock import patch
from clanm import backend
from clanm.mouse_codec import decode
from clanm.protocol import MOUSE_LIGHT_EFFECTS, mouse_lighting_sequence


class MouseEffectsTests(unittest.TestCase):
    def test_official_mode_parameters_and_lighting_only(self):
        for name, mode in MOUSE_LIGHT_EFFECTS.items():
            for speed in range(5):
                for brightness in (0, 127, 255):
                    with self.subTest(mode=name, speed=speed, brightness=brightness):
                        config=dict(mode=name, color='#ff0000', speed=speed, brightness=brightness)
                        ops=mouse_lighting_sequence(config)
                        self.assertEqual([kind for kind, _ in ops], ['control', 'control'])
                        raw=[decode(data) for _, data in ops]
                        self.assertEqual([p[0] for p in raw], [0x0c, 0x0d])
                        self.assertEqual(raw[0][1:4], bytes((255,0,0)) if mode else bytes(3))
                        if mode==0: expected=(0,0,0)
                        elif mode in (1,5,8,11): expected=(mode,brightness,0)
                        elif mode in (2,3,4): expected=(mode,speed,brightness)
                        elif mode in (6,7): expected=(mode,2,4-speed)
                        elif mode==9: expected=(mode,brightness,(4-speed)<<4)
                        else: expected=(mode,brightness,4-speed)
                        self.assertEqual(raw[1][1:4], bytes(expected))
                        for packet in raw:
                            self.assertEqual(packet[4:7], bytes(3))
                            self.assertEqual(sum(packet)&255,255)

    def test_invalid_settings_never_reach_transport(self):
        base=dict(mode='Respiração',color='#0000ff')
        for key, value in [('speed',-1),('speed',5),('speed',True),('speed',1.5),
                           ('brightness',-1),('brightness',256),('brightness',True),
                           ('mode','desconhecido'),('dpi',800),('buttons',[])]:
            with self.subTest(key=key,value=value), patch.object(backend,'send_mouse_lighting') as send:
                with self.assertRaises(ValueError): backend.apply_mouse({**base,key:value})
                send.assert_not_called()

    def test_legacy_profiles_use_explicit_defaults_for_history(self):
        legacy=dict(mode='Cor fixa',color='#0000ff')
        explicit=dict(**legacy,brightness=255,speed=2)
        self.assertEqual(mouse_lighting_sequence(legacy),mouse_lighting_sequence(explicit))
        with patch.object(backend,'send_mouse_lighting') as send:
            backend.apply_mouse(legacy)
            self.assertEqual(send.call_args.args[0],explicit)
