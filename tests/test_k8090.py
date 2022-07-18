# pylint: disable=protected-access

from unittest import TestCase

from src.k8090.relay_card import K8090


# Test the checksum method in the K8090 class
class TestK8090(TestCase):

    def test_checksum(self):
        self.assertEqual(K8090._checksum(0x10, 0x32, 0x45, 0x17), 0x5e)
        self.assertEqual(K8090._checksum(0x14, 0x4a, 0xff, 0x7b), 0x24)
        self.assertEqual(K8090._checksum(0x00, 0x00, 0x00, 0x00), 0xfc)
        self.assertEqual(K8090._checksum(0xff, 0xff, 0xff, 0xff), 0x00)
