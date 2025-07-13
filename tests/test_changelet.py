#
#
#

from argparse import ArgumentError
from contextlib import redirect_stdout
from io import StringIO
from shutil import rmtree
from tempfile import mkdtemp
from unittest import TestCase
from unittest.mock import patch

from changelet.base import Check, Create


class TemporaryDirectory(object):
    def __init__(self, delete_on_exit=True):
        self.delete_on_exit = delete_on_exit

    def __enter__(self):
        self.dirname = mkdtemp()
        return self

    def __exit__(self, *args, **kwargs):
        if self.delete_on_exit:
            rmtree(self.dirname)
        else:
            raise Exception(self.dirname)


class TestCreate(TestCase):

    class MockArgs:
        def __init__(self, _type, md, add=False, pr=None):
            self.type = _type
            self.md = md
            self.add = add
            self.pr = pr

    def test_parse_none(self):
        cmd = Create()

        argv = ['e*e']
        with self.assertRaises(ArgumentError) as ctx:
            cmd.parse(argv, exit_on_error=False)
        msg = ctx.exception.message
        self.assertEqual(
            'the following arguments are required: -t/--type, change-description-markdown',
            msg,
        )

    def test_parse_type(self):
        cmd = Create()

        # short w/o arg
        argv = ['e*e', '-t']
        with self.assertRaises(ArgumentError) as ctx:
            cmd.parse(argv, exit_on_error=False)
        msg = ctx.exception.message
        self.assertEqual('expected one argument', msg)

        # long w/o arg
        argv = ['e*e', '--type']
        with self.assertRaises(ArgumentError) as ctx:
            cmd.parse(argv, exit_on_error=False)
        msg = ctx.exception.message
        self.assertEqual('expected one argument', msg)

        # long w/incorrect arg
        argv = ['e*e', '--type', 'incorrect']
        with self.assertRaises(ArgumentError) as ctx:
            cmd.parse(argv, exit_on_error=False)
        msg = ctx.exception.message
        self.assertEqual(
            "invalid choice: 'incorrect' (choose from none, patch, minor, major)",
            msg,
        )

        # long w/valid arg
        argv = ['e*e', '--type', 'none']
        with self.assertRaises(ArgumentError) as ctx:
            cmd.parse(argv, exit_on_error=False)
        msg = ctx.exception.message
        self.assertEqual(
            'the following arguments are required: change-description-markdown',
            msg,
        )

    def test_parse_md(self):
        cmd = Create()

        # single arg desc
        desc = ['This is a test']
        argv = ['e*e', '--type', 'none', *desc]
        args = cmd.parse(argv, exit_on_error=False)
        self.assertEqual('none', args.type)
        self.assertEqual(desc, args.md)
        self.assertFalse(args.add)
        self.assertIsNone(args.pr)

        # multi arg desc
        desc = 'This is a test'.split(' ')
        argv = ['e*e', '--type', 'none', *desc]
        args = cmd.parse(argv, exit_on_error=False)
        self.assertEqual('none', args.type)
        self.assertEqual(desc, args.md)

    def test_parse_add(self):
        cmd = Create()

        # add, short
        desc = 'This will be added'.split(' ')
        argv = ['e*e', '-a', '--type', 'none', *desc]
        args = cmd.parse(argv, exit_on_error=False)
        self.assertTrue(args.add)
        self.assertIsNone(args.pr)

        # add, long
        argv = ['e*e', '--add', '--type', 'none', *desc]
        args = cmd.parse(argv, exit_on_error=False)
        self.assertTrue(args.add)
        self.assertIsNone(args.pr)

    def test_parse_pr(self):
        cmd = Create()

        # pr, missing arg
        desc = 'This has a pr'.split(' ')
        argv = ['e*e', '--pr', '--type', 'none', *desc]
        with self.assertRaises(ArgumentError) as ctx:
            cmd.parse(argv, exit_on_error=False)
        msg = ctx.exception.message
        self.assertEqual('expected one argument', msg)

        # pr, short
        argv = ['e*e', '-p', '42', '--type', 'none', *desc]
        args = cmd.parse(argv, exit_on_error=False)
        self.assertFalse(args.add)
        self.assertEqual(42, args.pr)

        # pr, long
        argv = ['e*e', '--pr', '42', '--type', 'none', *desc]
        args = cmd.parse(argv, exit_on_error=False)
        self.assertFalse(args.add)
        self.assertEqual(42, args.pr)

    def test_run(self):
        cmd = Create()

        with TemporaryDirectory() as td:
            desc = 'This is a test'
            args = self.MockArgs('none', desc.split(' '))
            buf = StringIO()
            with redirect_stdout(buf):
                filepath = cmd.run(args, td.dirname)
            self.assertTrue(filepath.startswith(td.dirname))
            msg = buf.getvalue()
            self.assertEqual(
                f'Created {filepath}, it can be further edited and should be committed to your branch.\n',
                msg,
            )

            # TODO: should use changelet object once it's a thing
            with open(filepath, 'r') as fh:
                data = fh.read()
            self.assertTrue('type: none' in data)
            self.assertTrue(desc in data)

            # 2nd run will get a new filepath
            new = cmd.run(args, td.dirname)
            self.assertNotEqual(filepath, new)

    def test_run_pr(self):
        cmd = Create()

        with TemporaryDirectory() as td:
            desc = 'This is a test, with a pr'
            args = self.MockArgs('minor', desc.split(' '), pr=99)
            filepath = cmd.run(args, td.dirname)

            # TODO: should use changelet object once it's a thing
            with open(filepath, 'r') as fh:
                data = fh.read()
            self.assertTrue('type: minor' in data)
            self.assertTrue('pr: 99' in data)
            self.assertTrue(desc in data)

    @patch('changelet.base.run')
    def test_run_add(self, run_mock):
        cmd = Create()

        with TemporaryDirectory() as td:
            desc = 'This is a test, with a pr'
            args = self.MockArgs('minor', desc.split(' '), add=True)
            buf = StringIO()
            with redirect_stdout(buf):
                filepath = cmd.run(args, td.dirname)
            run_mock.assert_called_once()
            args = run_mock.call_args[0][0]
            self.assertEqual(['git', 'add', filepath], args)
            msg = buf.getvalue()
            self.assertEqual(
                f'Created {filepath}, it has been staged and should be committed to your branch.\n',
                msg,
            )


class TestCheck(TestCase):

    class Result:
        def __init__(self, stdout, returncode):
            self.stdout = stdout
            self.returncode = returncode

    def test_parse(self):
        cmd = Check()
        # noop
        self.assertIsNone(cmd.parse(None))

    @patch('changelet.base.print')
    @patch('changelet.base.exit')
    def test_run_no_directory(self, exit_mock, print_mock):
        cmd = Check()

        cmd.run(None, 'non-existant')
        exit_mock.assert_called_once()
        code = exit_mock.call_args[0][0]
        self.assertEqual(1, code)
        print_mock.assert_called_once()
        msg = print_mock.call_args[0][0]
        self.assertEqual(
            'PR is missing required changelog file, run changelet create', msg
        )

    @patch('changelet.base.isdir')
    @patch('changelet.base.run')
    @patch('changelet.base.exit')
    def test_run_no_changelet(self, exit_mock, run_mock, isdir_mock):
        cmd = Check()

        # no entries
        exit_mock.reset_mock()
        run_mock.reset_mock()
        isdir_mock.return_value = True
        run_mock.return_value = self.Result(b'', 0)
        self.assertFalse(cmd.run(None))
        exit_mock.assert_called_once()
        code = exit_mock.call_args[0][0]
        self.assertEqual(1, code)
        args = run_mock.call_args[0][0]
        self.assertEqual(
            ['git', 'diff', '--name-only', 'origin/main', './.changelog'], args
        )

        # non-zero exit status
        exit_mock.reset_mock()
        run_mock.reset_mock()
        isdir_mock.return_value = True
        run_mock.return_value = self.Result(b'bar.md', 1)
        self.assertFalse(cmd.run(None))
        exit_mock.assert_called_once()
        code = exit_mock.call_args[0][0]
        self.assertEqual(1, code)
        args = run_mock.call_args[0][0]
        self.assertEqual(
            ['git', 'diff', '--name-only', 'origin/main', './.changelog'], args
        )

    @patch('changelet.base.isdir')
    @patch('changelet.base.run')
    @patch('changelet.base.exit')
    def test_run(self, exit_mock, run_mock, isdir_mock):
        cmd = Check()

        # no entries
        run_mock.reset_mock()
        isdir_mock.return_value = True
        run_mock.return_value = self.Result(b'something/foo.md', 0)
        self.assertTrue(cmd.run(None))
        exit_mock.assert_called_once()
        code = exit_mock.call_args[0][0]
        self.assertEqual(0, code)
        args = run_mock.call_args[0][0]
        self.assertEqual(
            ['git', 'diff', '--name-only', 'origin/main', './.changelog'], args
        )
