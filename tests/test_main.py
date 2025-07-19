#
#
#

from unittest import TestCase

from changelet.main import main


class TestMain(TestCase):

    def test_main(self):
        main([])
