#
#
#

from argparse import ArgumentParser
from unittest import TestCase
from unittest.mock import MagicMock, patch

from helpers import AssertActionMixin

from changelet.command.check import Check


class TestCommandCheck(TestCase, AssertActionMixin):
    def test_configure(self):
        check = Check()
        parser = ArgumentParser(exit_on_error=False)
        check.configure(parser)

        actions = {a.dest: a for a in parser._actions}

        self.assert_action(
            actions['quiet'], flags=['-q', '--quiet'], default=False
        )

    @patch('changelet.command.check.exit')
    def test_exit(self, exit_mock):
        check = Check()
        check.exit(42)
        exit_mock.assert_called_once_with(42)

    @patch('changelet.command.check.Check.exit')
    def test_run(self, exit_mock):
        class ArgsMock:

            def __init__(self, quiet=False):
                self.quiet = quiet

        check = Check()

        config = MagicMock()

        # has changelog entry
        args = ArgsMock()
        exit_mock.reset_mock()
        config.provider.changelog_entries_in_branch.return_value = True
        check.run(args, config)
        config.provider.changelog_entries_in_branch.assert_called_once()
        exit_mock.assert_called_once_with(0)

        # no changelog entgry
        exit_mock.reset_mock()
        config.provider.changelog_entries_in_branch.return_value = False
        with patch('changelet.command.check.print') as print_mock:
            check.run(args, config)
        print_mock.assert_called_once()
        exit_mock.assert_called_once_with(1)

        # quiet
        args.quiet = True
        exit_mock.reset_mock()
        config.provider.changelog_entries_in_branch.return_value = False
        with patch('changelet.command.check.print') as print_mock:
            check.run(args, config)
        print_mock.assert_not_called()
        exit_mock.assert_called_once_with(1)
