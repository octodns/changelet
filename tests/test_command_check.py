#
#
#

from unittest import TestCase
from unittest.mock import MagicMock, patch

from changelet.command.check import Check


class TestCommandCheck(TestCase):

    def test_configure(self):
        # smoke
        Check().configure(None)

    @patch('changelet.command.check.exit')
    def test_exit(self, exit_mock):
        check = Check()
        check.exit(42)
        exit_mock.assert_called_once_with(42)

    @patch('changelet.command.check.Check.exit')
    def test_run(self, exit_mock):
        check = Check()

        config = MagicMock()

        # has changelog entry
        exit_mock.reset_mock()
        config.provider.changelog_entries_in_branch.return_value = True
        check.run(None, config)
        config.provider.changelog_entries_in_branch.assert_called_once()
        exit_mock.assert_called_once_with(0)

        # no changelog entgry
        exit_mock.reset_mock()
        config.provider.changelog_entries_in_branch.return_value = False
        check.run(None, config)
        exit_mock.assert_called_once_with(1)
