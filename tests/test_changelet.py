#
#
#

from unittest import TestCase

from changelet import __version__


class TestChangeLet(TestCase):
    def test_nothing(self):
        self.assertTrue(__version__)
