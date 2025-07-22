#
#
#

from argparse import ArgumentError
from sys import version_info
from unittest import TestCase
from unittest.mock import patch

from changelet.config import Config
from changelet.main import main


class TestMain(TestCase):

    def test_missing_command(self):
        # missing command
        if version_info.minor > 11:
            ctx = self.assertRaises(ArgumentError)
        else:  # < 12
            # older versions of argparse exit even when told not to
            ctx = patch('argparse.ArgumentParser.exit')

        with ctx as ctx:
            main(['e*e'], exit_on_error=False)

        if version_info.minor > 11:
            self.assertEqual(
                'the following arguments are required: command',
                str(ctx.exception),
            )
        else:
            ctx.assert_called_once()

    def test_success(self):
        # has command, should be run, expect check to exit, don't care about
        # with what code
        with patch('changelet.command.check.exit') as exit_mock:
            main(['e*e', 'check'], exit_on_error=False)
        exit_mock.assert_called_once()

    @patch('changelet.config.Config.build')
    def test_arg_config(self, build_mock):
        build_mock.return_value = Config()

        # has command, should be run, expect check to exit, don't care about
        # with what code
        with patch('changelet.command.check.exit') as exit_mock:
            main(['e*e', '--config', 'foo.yaml', 'check'], exit_on_error=False)
        exit_mock.assert_called_once()
        build_mock.assert_called_once_with(config='foo.yaml')

    @patch('changelet.config.Config.build')
    def test_arg_root(self, build_mock):
        build_mock.return_value = Config()

        # has command, should be run, expect check to exit, don't care about
        # with what code
        with patch('changelet.command.check.exit') as exit_mock:
            main(['e*e', '--root', 'root-dir', 'check'], exit_on_error=False)
        exit_mock.assert_called_once()
        build_mock.assert_called_once_with(root='root-dir')

    @patch('changelet.config.Config.build')
    def test_arg_directory(self, build_mock):
        build_mock.return_value = Config()

        # has command, should be run, expect check to exit, don't care about
        # with what code
        with patch('changelet.command.check.exit') as exit_mock:
            main(
                ['e*e', '--directory', 'directory-dir', 'check'],
                exit_on_error=False,
            )
        exit_mock.assert_called_once()
        build_mock.assert_called_once_with(directory='directory-dir')
