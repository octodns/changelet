#
#
#

from argparse import ArgumentParser
from os import makedirs
from os.path import join
from unittest import TestCase
from unittest.mock import MagicMock, patch

from helpers import AssertActionMixin, TemporaryDirectory

from changelet.command.create import Create
from changelet.config import Config
from changelet.entry import EntryType


class TestCommandCreate(TestCase, AssertActionMixin):

    def test_configure(self):
        create = Create()
        parser = ArgumentParser(exit_on_error=False)
        create.configure(parser)

        actions = {a.dest: a for a in parser._actions}

        self.assert_action(actions['add'], flags=['-a', '--add'], default=False)
        self.assert_action(
            actions['pr'], flags=['-p', '--pr'], nargs=1, default=None
        )
        self.assert_action(
            actions['type'],
            flags=['-t', '--type'],
            nargs=1,
            default=None,
            required=False,
            choices={'none', 'patch', 'minor', 'major'},
        )
        self.assert_action(
            actions['continue_'], flags=['--continue'], default=False
        )
        self.assert_action(
            actions['description'],
            flags=[],
            nargs='*',
            default=None,
            required=False,
        )

    @patch('changelet.entry.Entry.save')
    def test_run(self, save_mock):

        class ArgsMock:

            def __init__(
                self, type, description, pr=None, add=False, commit=False
            ):
                self.type = type
                self.description = description
                self.pr = pr
                self.add = add
                self.commit = commit
                self.continue_ = False

        with TemporaryDirectory() as td:
            type = 'patch'
            description = 'Hello World'
            args = ArgsMock(type=type, description=description.split(' '))
            directory = join(td.dirname, '.cl')
            config = Config(
                directory=directory, commit_prefix='xyz: ', provider=None
            )
            config._provider = provider_mock = MagicMock()
            create = Create()

            # directory doesn't exist, will be created
            save_mock.reset_mock()
            provider_mock.reset_mock()
            entry = create.run(args, config)
            # args made it through
            self.assertEqual(EntryType(type), entry.type)
            self.assertEqual(description, entry.description)
            self.assertIsNone(entry.pr)
            filename = entry.filename
            self.assertTrue(filename.startswith(directory))
            self.assertTrue(filename.endswith('.md'))
            save_mock.assert_called_once()
            # add wasn't called
            provider_mock.add_file.assert_not_called()
            provider_mock.has_staged.assert_not_called()

            # directory exist
            save_mock.reset_mock()
            provider_mock.reset_mock()
            args.pr = pr = 43
            args.add = True
            entry = create.run(args, config)
            # args made it through
            self.assertEqual(EntryType(type), entry.type)
            self.assertEqual(description, entry.description)
            self.assertEqual(pr, entry.pr)
            # new filename
            new_filename = entry.filename
            self.assertNotEqual(filename, new_filename)
            save_mock.assert_called_once()
            provider_mock.add_file.assert_called_once_with(new_filename)
            provider_mock.has_staged.assert_not_called()

            # commit w/staged
            save_mock.reset_mock()
            provider_mock.reset_mock()
            provider_mock.staged_changelog_entry.return_value = None
            provider_mock.has_staged.return_value = True
            args.add = False
            args.commit = True
            entry = create.run(args, config)
            new_filename = entry.filename
            provider_mock.has_staged.assert_called_once()
            provider_mock.add_file.assert_called_once_with(new_filename)
            provider_mock.commit.assert_called_once_with(description)
            save_mock.assert_called_once()

            # commit w/o staged
            save_mock.reset_mock()
            provider_mock.reset_mock()
            provider_mock.staged_changelog_entry.return_value = None
            provider_mock.has_staged.return_value = False
            args.add = False
            args.commit = True
            entry = create.run(args, config)
            new_filename = entry.filename
            provider_mock.has_staged.assert_called_once()
            provider_mock.add_file.assert_called_once_with(new_filename)
            # custom/overridden config_prefix
            provider_mock.commit.assert_called_once_with(f'xyz: {description}')
            save_mock.assert_called_once()

    @patch('changelet.command.create.sys_exit')
    def test_run_continue(self, exit_mock):

        class ArgsMock:
            continue_ = True

        with TemporaryDirectory() as td:
            directory = join(td.dirname, '.cl')
            config = Config(
                directory=directory, commit_prefix='xyz: ', provider=None
            )
            config._provider = provider_mock = MagicMock()
            create = Create()
            args = ArgsMock()

            # no staged entry found
            provider_mock.reset_mock()
            exit_mock.reset_mock()
            provider_mock.staged_changelog_entry.return_value = None
            create.run(args, config)
            provider_mock.staged_changelog_entry.assert_called_once_with(
                directory
            )
            exit_mock.assert_called_once_with(1)

            # staged entry found, no other staged changes (prefix added)
            provider_mock.reset_mock()
            exit_mock.reset_mock()
            description = 'Hello World'
            staged_file = join(directory, 'abc123.md')
            makedirs(directory)
            with open(staged_file, 'w') as fh:
                fh.write('---\ntype: patch\n---\n')
                fh.write(description)
            provider_mock.staged_changelog_entry.return_value = staged_file
            provider_mock.has_staged.return_value = False
            create.run(args, config)
            provider_mock.has_staged.assert_called_once_with(
                exclude=staged_file
            )
            provider_mock.commit.assert_called_once_with('xyz: Hello World')

            # staged entry found, with other staged changes (no prefix)
            provider_mock.reset_mock()
            exit_mock.reset_mock()
            provider_mock.staged_changelog_entry.return_value = staged_file
            provider_mock.has_staged.return_value = True
            create.run(args, config)
            provider_mock.has_staged.assert_called_once_with(
                exclude=staged_file
            )
            provider_mock.commit.assert_called_once_with('Hello World')

    @patch('changelet.command.create.sys_exit')
    @patch('changelet.entry.Entry.save')
    def test_run_commit_already_staged(self, save_mock, exit_mock):

        class ArgsMock:
            continue_ = False
            type = 'patch'
            description = ['Hello', 'World']
            pr = None
            add = False
            commit = True

        with TemporaryDirectory() as td:
            directory = join(td.dirname, '.cl')
            config = Config(
                directory=directory, commit_prefix='xyz: ', provider=None
            )
            config._provider = provider_mock = MagicMock()
            create = Create()
            args = ArgsMock()

            # already staged changelog entry detected
            provider_mock.staged_changelog_entry.return_value = (
                '.cl/existing.md'
            )
            create.run(args, config)
            provider_mock.staged_changelog_entry.assert_called_once_with(
                directory
            )
            exit_mock.assert_called_once_with(1)
            # entry should not have been saved
            save_mock.assert_not_called()
            provider_mock.add_file.assert_not_called()
            provider_mock.commit.assert_not_called()

    @patch('changelet.command.create.sys_exit')
    def test_run_missing_required_args(self, exit_mock):

        class ArgsMock:
            def __init__(self, type=None, description=None):
                self.continue_ = False
                self.add = False
                self.commit = False
                self.pr = None
                self.type = type
                self.description = description

        with TemporaryDirectory() as td:
            directory = join(td.dirname, '.cl')
            config = Config(
                directory=directory, commit_prefix='xyz: ', provider=None
            )
            config._provider = MagicMock()
            create = Create()

            # missing type
            args = ArgsMock(type=None, description=['Hello'])
            exit_mock.reset_mock()
            create.run(args, config)
            exit_mock.assert_called_once_with(1)

            # missing description
            args = ArgsMock(type='patch', description=None)
            exit_mock.reset_mock()
            create.run(args, config)
            exit_mock.assert_called_once_with(1)

            # empty description list
            args = ArgsMock(type='patch', description=[])
            exit_mock.reset_mock()
            create.run(args, config)
            exit_mock.assert_called_once_with(1)
