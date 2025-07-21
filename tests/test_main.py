#
#
#

from argparse import ArgumentError
from unittest import TestCase
from unittest.mock import patch

from changelet.main import main


class TestMain(TestCase):

    def test_main(self):
        # missing command
        with self.assertRaises(ArgumentError) as ctx:
            main(['e*e'], exit_on_error=False)
        self.assertEqual(
            'the following arguments are required: command', str(ctx.exception)
        )

        # has command, should be run, expect check to exit, don't care about
        # with what code
        with patch('changelet.command.check.exit') as exit_mock:
            main(['e*e', 'check'], exit_on_error=False)
        exit_mock.assert_called_once()
