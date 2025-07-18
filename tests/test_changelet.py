#
#
#

from argparse import ArgumentError
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from io import StringIO
from json import dumps
from os import makedirs
from os.path import join
from unittest import TestCase
from unittest.mock import call, patch

from helpers import TemporaryDirectory

from changelet.base import (
    Bump,
    Check,
    Create,
    _ChangeMeta,
    _format_version,
    _get_changelogs,
    _get_current_version,
    _get_new_version,
)
from changelet.cmds import general_usage
from changelet.cmds import main as cmds_main
from changelet.cmds import register_cmd


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


class TestBump(TestCase):

    class MockArgs:
        def __init__(self, title, make_changes=False):
            self.title = title
            self.make_changes = make_changes

    def test_parse_none(self):
        cmd = Bump()

        argv = ['e*e']
        with self.assertRaises(ArgumentError) as ctx:
            cmd.parse(argv, exit_on_error=False)
        msg = ctx.exception.message
        self.assertEqual('the following arguments are required: title', msg)

    def test_parse_title(self):
        cmd = Bump()

        desc = ['The release as one string']
        argv = ['e*e', *desc]
        args = cmd.parse(argv, exit_on_error=False)
        self.assertEqual(desc, args.title)
        self.assertFalse(args.make_changes)

        desc = 'The release as individual words'.split(' ')
        argv = ['e*e', *desc]
        args = cmd.parse(argv, exit_on_error=False)
        self.assertEqual(desc, args.title)

    def test_parse_make_changes(self):
        cmd = Bump()

        desc = ['The release as one string']
        argv = ['e*e', '--make-changes', *desc]
        args = cmd.parse(argv, exit_on_error=False)
        self.assertEqual(desc, args.title)
        self.assertTrue(args.make_changes)

        desc = 'The release as individual words'.split(' ')
        argv = ['e*e', '--make-changes', *desc]
        args = cmd.parse(argv, exit_on_error=False)
        self.assertEqual(desc, args.title)
        self.assertTrue(args.make_changes)

    @patch('changelet.base.exit')
    @patch('changelet.base._get_changelogs')
    @patch('changelet.base._get_current_version')
    def test_run_nothing(self, gcv_mock, gcl_mock, exit_mock):
        cmd = Bump()

        gcv_mock.return_value = (0, 1, 3)
        title = 'This is the title'.split(' ')

        # no changes
        gcl_mock.return_value = []
        self.assertIsNone(cmd.run(self.MockArgs(title)))

        # only type none
        now = datetime.now()
        gcl_mock.return_value = [
            {
                'filepath': '',
                'md': 'change 1',
                'pr': 42,
                'time': now - timedelta(days=1),
                'type': 'none',
            },
            {
                'filepath': '',
                'md': 'change 2',
                'pr': 88,
                'time': now - timedelta(days=2),
                'type': 'none',
            },
        ]
        self.assertIsNone(cmd.run(self.MockArgs(title)))

    @patch('changelet.base.exit')
    @patch('changelet.base._get_changelogs')
    @patch('changelet.base._get_current_version')
    @patch('changelet.base.remove')
    def test_run_dry_run(self, rm_mock, gcv_mock, gcl_mock, exit_mock):
        cmd = Bump()

        gcv_mock.return_value = (0, 1, 3)
        now = datetime.now()
        gcl_mock.return_value = [
            # major
            {
                'filepath': 'one',
                'md': 'change 1',
                'pr': 42,
                'time': now - timedelta(days=1),
                'type': 'major',
            },
            # minor
            {
                'filepath': 'two.one',
                'md': 'change 2.1',
                'pr': 88,
                'time': now - timedelta(days=2),
                'type': 'minor',
            },
            {
                'filepath': 'two.two',
                'md': 'change 2.2',
                'pr': 89,
                'time': now - timedelta(days=2),
                'type': 'minor',
            },
            ## no PR, no link
            {
                'filepath': 'two.three',
                'md': 'change 2.3',
                'pr': None,
                'time': now - timedelta(days=2),
                'type': 'minor',
            },
            ## no MD, skipped
            {
                'filepath': 'two.four',
                'md': None,
                'pr': -1,
                'time': now - timedelta(days=2),
                'type': 'minor',
            },
            # patch
            {
                'filepath': 'three',
                'md': 'change 3',
                'pr': 99,
                'time': now - timedelta(days=3),
                'type': 'patch',
            },
            # none, not included
            {
                'filepath': 'four',
                'md': 'change 4',
                'pr': 42,
                'time': now - timedelta(days=4),
                'type': 'none',
            },
        ]

        title = 'This is the title'.split(' ')
        new_version, buf = cmd.run(self.MockArgs(title))
        self.assertEqual('1.0.0', new_version)
        expected = f'''## 1.0.0 - {now.strftime("%Y-%m-%d")} - This is the title

Major:
* change 1 [#42](https://github.com/octodns/changelet/pull/42)

Minor:
* change 2.1 [#88](https://github.com/octodns/changelet/pull/88)
* change 2.2 [#89](https://github.com/octodns/changelet/pull/89)
* change 2.3

Patch:
* change 3 [#99](https://github.com/octodns/changelet/pull/99)

'''
        self.assertEqual(expected, buf)
        rm_mock.assert_not_called()

        # make changes
        with TemporaryDirectory() as td:
            changelog = join(td.dirname, 'CHANGELOG.md')
            with open(changelog, 'w') as fh:
                fh.write('fin')

            init = join(td.dirname, 'changelet')
            makedirs(init)
            init = join(init, '__init__.py')
            with open(init, 'w') as fh:
                fh.write("# __version__ = '0.1.3' #")

            new_version, buf = cmd.run(
                self.MockArgs(title, make_changes=True), directory=td.dirname
            )
            self.assertEqual('1.0.0', new_version)
            self.assertEqual(expected, buf)
            # all the changelog md files were removed
            rm_mock.assert_has_calls(
                [
                    call(f'{td.dirname}/one'),
                    call(f'{td.dirname}/two.one'),
                    call(f'{td.dirname}/two.two'),
                    call(f'{td.dirname}/two.three'),
                    call(f'{td.dirname}/two.four'),
                    call(f'{td.dirname}/three'),
                    call(f'{td.dirname}/four'),
                ]
            )
            # no extra calls
            self.assertEqual(7, rm_mock.call_count)
            # changelog md was prepended
            with open(changelog) as fh:
                self.assertEqual(f'{expected}fin', fh.read())
            # init had version updated
            with open(init) as fh:
                self.assertEqual("# __version__ = '1.0.0' #", fh.read())


class TestFormatVersion(TestCase):

    def test_format(self):
        self.assertEqual('1.2.3', _format_version((1, 2, 3)))
        self.assertEqual('1.2.3', _format_version(('1', '2', '3')))


class TestGetNewVersion(TestCase):

    def test_get_new_version(self):
        # no changelogs, get nothing back/no bump
        self.assertIsNone(_get_new_version((1, 2, 3), []))

        # none doesn't bump
        self.assertIsNone(_get_new_version((1, 2, 3), [{'type': 'none'}]))

        # patch bump
        self.assertEqual(
            (1, 2, 4), _get_new_version((1, 2, 3), [{'type': 'patch'}])
        )

        # minor bump
        self.assertEqual(
            (1, 3, 0), _get_new_version((1, 2, 3), [{'type': 'minor'}])
        )

        # major bump
        self.assertEqual(
            (2, 0, 0), _get_new_version((1, 2, 3), [{'type': 'major'}])
        )

        # assume the first one is the driving type, ecpect ordered changlogs
        # entries, don't touch them ourselves
        self.assertEqual(
            (1, 3, 0),
            _get_new_version((1, 2, 3), [{'type': 'minor'}, {'type': 'major'}]),
        )


class TestGetChangelog(TestCase):

    @patch('changelet.base._ChangeMeta.get')
    def test_load(self, cm_mock):
        with TemporaryDirectory() as td:
            directory = join(td.dirname, '.changelog')
            makedirs(directory)

            # add a junk file that will be ignored
            with open(join(directory, 'foo.txt'), 'w') as fh:
                fh.write('ignored')

            return_values = []
            now = datetime(2025, 7, 1)

            def write_cl(i, _type, pr, append=None):
                return_values.append([pr, now - timedelta(days=i)])
                filename = join(td.dirname, '.changelog', f'cl_{i:04}.md')
                with open(filename, 'w') as fh:
                    fh.write(
                        f'''---
type: {_type}
---
This is change {i}, It is a {_type}'''
                    )
                    if append:
                        fh.write(append)

            for i, _type in enumerate(
                ('none', 'minor', 'major', 'major', 'patch')
            ):
                write_cl(i, _type, i, '\n' if i % 2 == 0 else None)
            # one that will be ignored b/c it has no PR
            write_cl(i + 1, 'patch', None)

            cm_mock.side_effect = return_values

            changelogs = _get_changelogs(directory=directory)
            # make sure they're in the order we expect, descending type & date
            self.assertEqual([2, 3, 1, 4, 0], [c['pr'] for c in changelogs])


class TestGetCurrentVersion(TestCase):

    def test_get_current_version(self):
        with TemporaryDirectory() as td:
            module_name = 'foo_bar'
            with open(join(td.dirname, f'{module_name}.py'), 'w') as fh:
                fh.write('__version__ = "3.2.1"')

            ver = _get_current_version(module_name, directory=td.dirname)
            self.assertEqual((3, 2, 1), ver)


class TestChangeMeta(TestCase):

    class MockResult:
        def __init__(self, stdout):
            self.stdout = stdout

    @patch('changelet.base.run')
    def test_fill_cache(self, run_mock):

        run_mock.return_value = self.MockResult(
            dumps(
                [
                    # straightforward
                    {
                        'number': 42,
                        'files': [{'path': '.changelog/foo.md'}],
                        'mergedAt': '2025-07-01T10:42Z',
                    },
                    # no changelog
                    {
                        'number': 43,
                        'files': [{'path': 'other.txt'}],
                        'mergedAt': '2025-07-02T10:42Z',
                    },
                    # multiple changelog
                    {
                        'number': 44,
                        'files': [
                            {'path': '.changelog/bar.md'},
                            {'path': '.changelog/baz.md'},
                        ],
                        'mergedAt': '2025-07-03T10:42Z',
                    },
                ]
            )
        )

        self.assertIsNone(_ChangeMeta._pr_cache)
        # for now we're focused on the cache processing so we just need to call get
        _ChangeMeta.get('', {})
        self.assertEqual(
            {
                '.changelog/foo.md': (42, datetime(2025, 7, 1, 10, 42)),
                '.changelog/bar.md': (44, datetime(2025, 7, 3, 10, 42)),
                '.changelog/baz.md': (44, datetime(2025, 7, 3, 10, 42)),
            },
            _ChangeMeta._pr_cache,
        )
        # get something out of our cache
        self.assertEqual(44, _ChangeMeta.get('.changelog/bar.md', {})[0])
        self.assertIsNone(_ChangeMeta.get('.changelog/nope.md', {})[0])

        # something with an explicit/override PR
        self.assertEqual(
            45, _ChangeMeta.get('.changelog/nope.md', {'pr': 45})[0]
        )


class TestCmds(TestCase):

    @patch('changelet.cmds.print')
    def test_general_usage(self, print_mock):
        general_usage(('e*e',))
        self.assertEqual(2, print_mock.call_count)
        self.assertTrue('Creates and checks' in print_mock.call_args.args[0])

        # with a msg just get the message

        print_mock.reset_mock()
        msg = 'foo=bar'
        general_usage(('e*e',), msg)
        self.assertEqual(2, print_mock.call_count)
        self.assertEqual(msg, print_mock.call_args.args[0])

    @patch('changelet.cmds.print')
    @patch('changelet.cmds.exit')
    def test_main(self, exit_mock, print_mock):

        class Foo:
            argv = None

            def parse(self, argv):
                Foo.argv = argv
                return [42]

            def run(self, args):
                args.append(43)
                return args

        register_cmd('foo', Foo)

        # missing command
        exit_mock.reset_mock()
        print_mock.reset_mock()
        cmds_main(['e*e'])
        exit_mock.assert_called_once()
        code = exit_mock.call_args[0][0]
        self.assertEqual(1, code)
        self.assertEqual('missing command', print_mock.call_args.args[0])

        # unknown command
        exit_mock.reset_mock()
        print_mock.reset_mock()
        cmds_main(['e*e', 'blip'])
        exit_mock.assert_called_once()
        code = exit_mock.call_args[0][0]
        self.assertEqual(1, code)
        self.assertEqual('unknown command "blip"', print_mock.call_args.args[0])

        # help
        exit_mock.reset_mock()
        print_mock.reset_mock()
        cmds_main(['e*e', '-h'])
        exit_mock.assert_called_once()
        code = exit_mock.call_args[0][0]
        self.assertEqual(0, code)
        self.assertTrue('Creates and checks' in print_mock.call_args.args[0])

        # valid
        exit_mock.reset_mock()
        print_mock.reset_mock()
        cmds_main(['e*e', 'foo', '--abc', '123'])
        exit_mock.assert_not_called()
        self.assertEqual(['e*e', '--abc', '123'], Foo.argv)
