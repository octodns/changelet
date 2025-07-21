#
#
#

from unittest import TestCase

from changelet.command import commands, register
from changelet.command.bump import Bump
from changelet.command.check import Check
from changelet.command.create import Create


class TestCommand(TestCase):

    def tearDown(self):
        try:
            del commands['dummy']
        except KeyError:
            pass

    def test_register(self):
        self.assertEqual(['bump', 'check', 'create'], list(commands.keys()))
        self.assertIsInstance(commands['bump'], Bump)
        self.assertIsInstance(commands['check'], Check)
        self.assertIsInstance(commands['create'], Create)

        class Dummy:
            name = 'dummy'

        register(Dummy)
        self.assertTrue('dummy' in commands)
        self.assertIsInstance(commands['dummy'], Dummy)
