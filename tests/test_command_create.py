#
#
#

from argparse import ArgumentParser
from os.path import join
from unittest import TestCase
from unittest.mock import MagicMock, patch

from helpers import AssertActionMixin, TemporaryDirectory

from changelet.command.create import Create
from changelet.config import Config


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
            required=True,
            choices={'none', 'patch', 'minor', 'major'},
        )
        self.assert_action(
            actions['description'],
            flags=[],
            nargs='+',
            default=None,
            required=True,
        )

    @patch('changelet.entry.Entry.save')
    def test_run(self, save_mock):

        class ArgsMock:

            def __init__(self, type, description, pr=None, add=False):
                self.type = type
                self.description = description
                self.pr = pr
                self.add = add

        with TemporaryDirectory() as td:
            type = 'patch'
            description = 'Hello World'
            args = ArgsMock(type=type, description=description.split(' '))
            directory = join(td.dirname, '.cl')
            config = Config(directory=directory, provider=None)
            config._provider = provider_mock = MagicMock()
            create = Create()

            # directory doesn't exist, will be created
            save_mock.reset_mock()
            entry = create.run(args, config)
            # args made it through
            self.assertEqual(type, entry.type)
            self.assertEqual(description, entry.description)
            self.assertIsNone(entry.pr)
            filename = entry.filename
            self.assertTrue(filename.startswith(directory))
            self.assertTrue(filename.endswith('.md'))
            save_mock.assert_called_once()
            # add wasn't called
            provider_mock.add_file.assert_not_called()

            # directory exist
            save_mock.reset_mock()
            args.pr = pr = 43
            args.add = True
            entry = create.run(args, config)
            # args made it through
            self.assertEqual(type, entry.type)
            self.assertEqual(description, entry.description)
            self.assertEqual(pr, entry.pr)
            # new filename
            new_filename = entry.filename
            self.assertNotEqual(filename, new_filename)
            save_mock.assert_called_once()
            provider_mock.add_file.assert_called_once_with(new_filename)
