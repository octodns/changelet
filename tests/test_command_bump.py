#
#
#

from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from os import makedirs
from os.path import basename, join
from sys import version_info
from unittest import TestCase
from unittest.mock import call, patch

from helpers import AssertActionMixin, TemporaryDirectory
from semver import Version

from changelet.command.bump import (
    Bump,
    _get_current_version,
    _get_new_version,
    version,
)
from changelet.config import Config
from changelet.entry import Entry
from changelet.pr import Pr


class TestCommandBump(TestCase, AssertActionMixin):

    class MockArgs:
        def __init__(self, title, version=None, make_changes=False, pr=False):
            self.title = title
            self.make_changes = make_changes
            self.version = version
            self.pr = pr

    def test_configure(self):
        create = Bump()
        parser = ArgumentParser(exit_on_error=False)
        create.configure(parser)

        actions = {a.dest: a for a in parser._actions}

        self.assert_action(
            actions['make_changes'], flags=['--make-changes'], default=False
        )
        self.assert_action(actions['pr'], flags=['--pr'], default=False)
        # 3.12 made a change to * so that required=False, before that it was
        # True, for now we'll have to ignore it
        required = False if version_info >= (3, 12, 0) else None
        self.assert_action(
            actions['title'],
            flags=[],
            nargs='*',
            default=None,
            required=required,
        )

    @patch('changelet.command.bump.exit')
    def test_exit(self, exit_mock):
        bump = Bump()
        bump.exit(42)
        exit_mock.assert_called_once_with(42)

    @patch('changelet.command.bump.Bump.exit')
    @patch('changelet.entry.Entry.load_all')
    @patch('changelet.command.bump._get_current_version')
    def test_run_nothing(self, gcv_mock, ela_mock, exit_mock):
        cmd = Bump()

        directory = '.cl'
        config = Config(directory, provider=None)

        gcv_mock.return_value = Version.parse('0.1.3')
        title = 'This is the title'.split(' ')

        # no changes
        ela_mock.return_value = []
        exit_mock.return_value = None
        self.assertIsNone(cmd.run(args=self.MockArgs(title), config=config))

        # only type none
        ela_mock.return_value = [
            Entry(type='none', description='change 1'),
            Entry(type='none', description='change 2'),
        ]
        self.assertIsNone(cmd.run(args=self.MockArgs(title), config=config))

    @patch('changelet.command.bump.Bump.exit')
    @patch('changelet.entry.Entry.load_all')
    @patch('changelet.command.bump._get_current_version')
    @patch('changelet.entry.remove')
    def test_run(self, rm_mock, gcv_mock, ela_mock, exit_mock):
        cmd = Bump()

        gcv_mock.return_value = Version.parse('0.1.3')
        now = datetime.now().replace(tzinfo=timezone.utc)
        ela_mock.return_value = [
            Entry(
                type='none',
                description='change 1',
                pr=Pr(
                    id=1,
                    text='text 1',
                    url='http://1',
                    merged_at=now - timedelta(days=1),
                ),
            ),
            Entry(
                type='minor',
                description='change 2.1',
                pr=Pr(
                    id=2,
                    text='text 2.1',
                    url='http://2.1',
                    merged_at=now - timedelta(days=3),
                ),
            ),
            Entry(
                type='minor',
                description='change 2.2',
                pr=Pr(
                    id=2,
                    text='text 2.2',
                    url='http://2.2',
                    merged_at=now - timedelta(days=2),
                ),
            ),
            # no PR, no link
            Entry(type='minor', description='change 2.3', pr=None),
            Entry(
                type='major',
                description='change 3',
                pr=Pr(
                    id=2,
                    text='text 3',
                    url='http://3',
                    merged_at=now - timedelta(days=9),
                ),
            ),
            Entry(
                type='patch',
                description='change 4',
                pr=Pr(
                    id=2,
                    text='text 4',
                    url='http://4',
                    merged_at=now - timedelta(days=1),
                ),
            ),
            Entry(
                type='none',
                description='change 5',
                pr=Pr(
                    id=2,
                    text='text 5',
                    url='http://5',
                    merged_at=now - timedelta(days=3),
                ),
            ),
        ]

        config = Config('.cl', provider=None)

        # give our entries filenames
        for i, entry in enumerate(ela_mock.return_value):
            entry.filename = join(config.directory, f'ela-{i:04d}.md')

        title = 'This is the title'.split(' ')
        new_version, buf = cmd.run(args=self.MockArgs(title), config=config)
        self.assertEqual('1.0.0', new_version)
        expected = f'''## 1.0.0 - {now.strftime("%Y-%m-%d")} - This is the title

Major:
* change 3 - [text 3](http://3)

Minor:
* change 2.2 - [text 2.2](http://2.2)
* change 2.1 - [text 2.1](http://2.1)
* change 2.3

Patch:
* change 4 - [text 4](http://4)

'''
        self.assertEqual(expected, buf)
        rm_mock.assert_not_called()

        # make changes
        with TemporaryDirectory() as td:

            changelog = join(td.dirname, 'CHANGELOG.md')
            with open(changelog, 'w') as fh:
                fh.write('fin')

            init = join(td.dirname, basename(td.dirname))
            makedirs(init)
            init = join(init, '__init__.py')
            with open(init, 'w') as fh:
                fh.write("# __version__ = '0.1.3' #")

            config = Config(join(td.dirname, '.cl'), provider=None)

            # no title
            expected = expected.replace(' - This is the title', '')
            # manual version
            expected = expected.replace('1.0.0', '3.0.0')
            new_version, buf = cmd.run(
                self.MockArgs([], version=Version(3), make_changes=True),
                config=config,
                root=td.dirname,
            )
            self.assertEqual('3.0.0', new_version)
            self.assertEqual(expected, buf)
            # all the changelog md files were removed
            rm_mock.assert_has_calls(
                [call(e.filename) for e in ela_mock.return_value],
                any_order=True,
            )
            # no extra calls
            self.assertEqual(7, rm_mock.call_count)
            # changelog md was prepended
            with open(changelog) as fh:
                self.assertEqual(f'{expected}fin', fh.read())
            # init had version updated
            with open(init) as fh:
                self.assertEqual("# __version__ = '3.0.0' #", fh.read())


class TestGetNewVersion(TestCase):

    def test_get_new_version(self):
        # no changelogs, get nothing back/no bump
        self.assertIsNone(_get_new_version(Version(1, 2, 3), []))

        # none doesn't bump
        self.assertIsNone(
            _get_new_version(
                Version(1, 2, 3), [Entry(type='none', description='')]
            )
        )

        # patch bump
        self.assertEqual(
            Version(1, 2, 4),
            _get_new_version(
                Version(1, 2, 3), [Entry(type='patch', description='')]
            ),
        )

        # minor bump
        self.assertEqual(
            Version(1, 3, 0),
            _get_new_version(
                Version(1, 2, 3), [Entry(type='minor', description='')]
            ),
        )

        # major bump
        self.assertEqual(
            Version(2, 0, 0),
            _get_new_version(
                Version(1, 2, 3), [Entry(type='major', description='')]
            ),
        )

        # assume the first one is the driving type, ecpect ordered changlogs
        # entries, don't touch them ourselves
        self.assertEqual(
            Version(1, 3, 0),
            _get_new_version(
                Version(1, 2, 3),
                [
                    Entry(type='minor', description=''),
                    Entry(type='major', description=''),
                ],
            ),
        )


class TestGetCurrentVersion(TestCase):

    def test_get_current_version(self):
        with TemporaryDirectory() as td:
            module_name = 'foo_bar'
            with open(join(td.dirname, f'{module_name}.py'), 'w') as fh:
                fh.write('__version__ = "3.2.1"')

            ver = _get_current_version(module_name, directory=td.dirname)
            self.assertEqual(3, ver.major)
            self.assertEqual(2, ver.minor)
            self.assertEqual(1, ver.patch)

    @patch('changelet.command.bump.path')
    def test_get_current_version_prepends_to_path(self, path_mock):
        # Simulate the case where a module exists in virtualenv
        # but we want to get the local version from directory
        with TemporaryDirectory() as td:
            module_name = 'foo_bar'
            with open(join(td.dirname, f'{module_name}.py'), 'w') as fh:
                fh.write('__version__ = "3.2.1"')

            # Create a mock sys.path that includes the module elsewhere
            path_mock.__contains__ = lambda self, x: True

            try:
                _get_current_version(module_name, directory=td.dirname)
            except:
                # import_module will fail with our mock, but we can check the path call
                pass

            # Verify that insert(0, ...) was called to prepend, not append
            path_mock.insert.assert_called_once_with(0, td.dirname)


class TestVersion(TestCase):

    def test_smoke(self):
        # this is bascially semver.Version.parse so we'll leave the actual
        # testing to it, here we'll just make sure things are plumbed up
        self.assertEqual(Version(1, 22, 33), version('1.22.33'))
        with self.assertRaises(ValueError):
            version('1.foo.33')


class TestCommandBumpPR(TestCase):

    class MockArgs:
        def __init__(self, title, version=None, make_changes=False, pr=False):
            self.title = title
            self.make_changes = make_changes
            self.version = version
            self.pr = pr

    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    def test_pr_not_on_main(self, exit_mock, run_mock):
        cmd = Bump()
        config = Config('.cl', provider=None)

        # Mock git branch --show-current to return 'feature-branch'
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = 'feature-branch\n'

        exit_mock.return_value = None

        result = cmd.run(args=self.MockArgs([], pr=True), config=config)
        self.assertIsNone(result)
        exit_mock.assert_called_once_with(1)
        run_mock.assert_called_once_with(
            ['git', 'branch', '--show-current'], capture_output=True, text=True
        )

    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    def test_pr_with_unstaged_changes(self, exit_mock, run_mock):
        cmd = Bump()
        config = Config('.cl', provider=None)

        exit_mock.return_value = None

        # Mock responses for git commands
        def run_side_effect(cmd_args, **kwargs):
            result = type('obj', (object,), {})()
            result.returncode = 0
            if cmd_args == ['git', 'branch', '--show-current']:
                result.stdout = 'main\n'
            elif cmd_args == ['git', 'status', '--porcelain']:
                result.stdout = ' M some_file.py\n'
            return result

        run_mock.side_effect = run_side_effect

        result = cmd.run(args=self.MockArgs([], pr=True), config=config)
        self.assertIsNone(result)
        exit_mock.assert_called_once_with(1)

    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    def test_pr_git_branch_fails(self, exit_mock, run_mock):
        cmd = Bump()
        config = Config('.cl', provider=None)

        exit_mock.return_value = None

        # Mock git branch command failure
        run_mock.return_value.returncode = 1

        result = cmd.run(args=self.MockArgs([], pr=True), config=config)
        self.assertIsNone(result)
        exit_mock.assert_called_once_with(1)

    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    def test_pr_git_status_fails(self, exit_mock, run_mock):
        cmd = Bump()
        config = Config('.cl', provider=None)

        exit_mock.return_value = None

        # Mock responses for git commands
        def run_side_effect(cmd_args, **kwargs):
            result = type('obj', (object,), {})()
            if cmd_args == ['git', 'branch', '--show-current']:
                result.returncode = 0
                result.stdout = 'main\n'
            elif cmd_args == ['git', 'status', '--porcelain']:
                result.returncode = 1
            return result

        run_mock.side_effect = run_side_effect

        result = cmd.run(args=self.MockArgs([], pr=True), config=config)
        self.assertIsNone(result)
        exit_mock.assert_called_once_with(1)

    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    def test_pr_git_pull_fails(self, exit_mock, run_mock):
        cmd = Bump()
        config = Config('.cl', provider=None)

        exit_mock.return_value = None

        # Mock responses for git commands
        def run_side_effect(cmd_args, **kwargs):
            result = type('obj', (object,), {})()
            if cmd_args == ['git', 'branch', '--show-current']:
                result.returncode = 0
                result.stdout = 'main\n'
            elif cmd_args == ['git', 'status', '--porcelain']:
                result.returncode = 0
                result.stdout = ''
            elif cmd_args == ['git', 'pull']:
                result.returncode = 1
                result.stderr = 'Pull failed'
            return result

        run_mock.side_effect = run_side_effect

        result = cmd.run(args=self.MockArgs([], pr=True), config=config)
        self.assertIsNone(result)
        exit_mock.assert_called_once_with(1)

    @patch('changelet.entry.remove')
    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    @patch('changelet.entry.Entry.load_all')
    @patch('changelet.command.bump._get_current_version')
    def test_pr_success(self, gcv_mock, ela_mock, exit_mock, run_mock, rm_mock):
        cmd = Bump()

        gcv_mock.return_value = Version.parse('0.1.3')
        now = datetime.now().replace(tzinfo=timezone.utc)
        ela_mock.return_value = [
            Entry(
                type='minor',
                description='change 1',
                pr=Pr(
                    id=1,
                    text='text 1',
                    url='http://1',
                    merged_at=now - timedelta(days=1),
                ),
            )
        ]

        exit_mock.return_value = None

        # Mock responses for git commands
        def run_side_effect(cmd_args, **kwargs):
            result = type('obj', (object,), {})()
            result.returncode = 0
            result.stdout = ''
            result.stderr = ''
            if cmd_args == ['git', 'branch', '--show-current']:
                result.stdout = 'main\n'
            elif cmd_args == ['git', 'status', '--porcelain']:
                result.stdout = ''
            elif cmd_args[0:2] == ['gh', 'pr']:
                result.stdout = 'https://github.com/test/repo/pull/1\n'
            return result

        run_mock.side_effect = run_side_effect

        with TemporaryDirectory() as td:
            changelog = join(td.dirname, 'CHANGELOG.md')
            with open(changelog, 'w') as fh:
                fh.write('fin')

            init = join(td.dirname, basename(td.dirname))
            makedirs(init)
            init = join(init, '__init__.py')
            with open(init, 'w') as fh:
                fh.write("# __version__ = '0.1.3' #")

            config = Config(join(td.dirname, '.cl'), provider=None)

            # give our entries filenames
            for i, entry in enumerate(ela_mock.return_value):
                entry.filename = join(config.directory, f'ela-{i:04d}.md')

            new_version, buf = cmd.run(
                self.MockArgs([], pr=True), config=config, root=td.dirname
            )

            self.assertEqual('0.2.0', new_version)

            # Verify all git commands were called
            calls = run_mock.call_args_list
            self.assertEqual(
                ['git', 'branch', '--show-current'], calls[0][0][0]
            )
            self.assertEqual(['git', 'status', '--porcelain'], calls[1][0][0])
            self.assertEqual(['git', 'pull'], calls[2][0][0])
            self.assertEqual(
                ['git', 'checkout', '-b', 'rel-0-2-0'], calls[3][0][0]
            )
            self.assertEqual(['git', 'add', '-p'], calls[4][0][0])
            self.assertEqual(['git', 'commit', '-m'], calls[5][0][0][:3])
            self.assertEqual(
                'Version 0.2.0 bump & changelog update', calls[5][0][0][3]
            )
            self.assertEqual(
                ['git', 'push', '-u', 'origin', 'rel-0-2-0'], calls[6][0][0]
            )
            self.assertEqual(['gh', 'pr', 'create'], calls[7][0][0][:3])

    @patch('changelet.entry.remove')
    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    @patch('changelet.entry.Entry.load_all')
    @patch('changelet.command.bump._get_current_version')
    def test_pr_create_branch_fails(
        self, gcv_mock, ela_mock, exit_mock, run_mock, rm_mock
    ):
        cmd = Bump()

        gcv_mock.return_value = Version.parse('0.1.3')
        now = datetime.now().replace(tzinfo=timezone.utc)
        ela_mock.return_value = [
            Entry(
                type='minor',
                description='change 1',
                pr=Pr(
                    id=1,
                    text='text 1',
                    url='http://1',
                    merged_at=now - timedelta(days=1),
                ),
            )
        ]

        exit_mock.return_value = None

        # Mock responses for git commands
        def run_side_effect(cmd_args, **kwargs):
            result = type('obj', (object,), {})()
            result.returncode = 0
            result.stdout = ''
            result.stderr = ''
            if cmd_args == ['git', 'branch', '--show-current']:
                result.stdout = 'main\n'
            elif cmd_args == ['git', 'status', '--porcelain']:
                result.stdout = ''
            elif cmd_args[0:3] == ['git', 'checkout', '-b']:
                result.returncode = 1
                result.stderr = 'Branch exists'
            return result

        run_mock.side_effect = run_side_effect

        with TemporaryDirectory() as td:
            changelog = join(td.dirname, 'CHANGELOG.md')
            with open(changelog, 'w') as fh:
                fh.write('fin')

            init = join(td.dirname, basename(td.dirname))
            makedirs(init)
            init = join(init, '__init__.py')
            with open(init, 'w') as fh:
                fh.write("# __version__ = '0.1.3' #")

            config = Config(join(td.dirname, '.cl'), provider=None)

            result = cmd.run(
                self.MockArgs([], pr=True), config=config, root=td.dirname
            )

            self.assertIsNone(result)
            exit_mock.assert_called_with(1)

    @patch('changelet.entry.remove')
    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    @patch('changelet.entry.Entry.load_all')
    @patch('changelet.command.bump._get_current_version')
    def test_pr_git_add_fails(
        self, gcv_mock, ela_mock, exit_mock, run_mock, rm_mock
    ):
        cmd = Bump()

        gcv_mock.return_value = Version.parse('0.1.3')
        now = datetime.now().replace(tzinfo=timezone.utc)
        ela_mock.return_value = [
            Entry(
                type='minor',
                description='change 1',
                pr=Pr(
                    id=1,
                    text='text 1',
                    url='http://1',
                    merged_at=now - timedelta(days=1),
                ),
            )
        ]

        exit_mock.return_value = None

        # Mock responses for git commands
        def run_side_effect(cmd_args, **kwargs):
            result = type('obj', (object,), {})()
            result.returncode = 0
            result.stdout = ''
            result.stderr = ''
            if cmd_args == ['git', 'branch', '--show-current']:
                result.stdout = 'main\n'
            elif cmd_args == ['git', 'status', '--porcelain']:
                result.stdout = ''
            elif cmd_args == ['git', 'add', '-p']:
                result.returncode = 1
            return result

        run_mock.side_effect = run_side_effect

        with TemporaryDirectory() as td:
            changelog = join(td.dirname, 'CHANGELOG.md')
            with open(changelog, 'w') as fh:
                fh.write('fin')

            init = join(td.dirname, basename(td.dirname))
            makedirs(init)
            init = join(init, '__init__.py')
            with open(init, 'w') as fh:
                fh.write("# __version__ = '0.1.3' #")

            config = Config(join(td.dirname, '.cl'), provider=None)

            result = cmd.run(
                self.MockArgs([], pr=True), config=config, root=td.dirname
            )

            self.assertIsNone(result)
            exit_mock.assert_called_with(1)

    @patch('changelet.entry.remove')
    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    @patch('changelet.entry.Entry.load_all')
    @patch('changelet.command.bump._get_current_version')
    def test_pr_git_commit_fails(
        self, gcv_mock, ela_mock, exit_mock, run_mock, rm_mock
    ):
        cmd = Bump()

        gcv_mock.return_value = Version.parse('0.1.3')
        now = datetime.now().replace(tzinfo=timezone.utc)
        ela_mock.return_value = [
            Entry(
                type='minor',
                description='change 1',
                pr=Pr(
                    id=1,
                    text='text 1',
                    url='http://1',
                    merged_at=now - timedelta(days=1),
                ),
            )
        ]

        exit_mock.return_value = None

        # Mock responses for git commands
        def run_side_effect(cmd_args, **kwargs):
            result = type('obj', (object,), {})()
            result.returncode = 0
            result.stdout = ''
            result.stderr = ''
            if cmd_args == ['git', 'branch', '--show-current']:
                result.stdout = 'main\n'
            elif cmd_args == ['git', 'status', '--porcelain']:
                result.stdout = ''
            elif cmd_args[:2] == ['git', 'commit']:
                result.returncode = 1
                result.stderr = 'Commit failed'
            return result

        run_mock.side_effect = run_side_effect

        with TemporaryDirectory() as td:
            changelog = join(td.dirname, 'CHANGELOG.md')
            with open(changelog, 'w') as fh:
                fh.write('fin')

            init = join(td.dirname, basename(td.dirname))
            makedirs(init)
            init = join(init, '__init__.py')
            with open(init, 'w') as fh:
                fh.write("# __version__ = '0.1.3' #")

            config = Config(join(td.dirname, '.cl'), provider=None)

            result = cmd.run(
                self.MockArgs([], pr=True), config=config, root=td.dirname
            )

            self.assertIsNone(result)
            exit_mock.assert_called_with(1)

    @patch('changelet.entry.remove')
    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    @patch('changelet.entry.Entry.load_all')
    @patch('changelet.command.bump._get_current_version')
    def test_pr_git_push_fails(
        self, gcv_mock, ela_mock, exit_mock, run_mock, rm_mock
    ):
        cmd = Bump()

        gcv_mock.return_value = Version.parse('0.1.3')
        now = datetime.now().replace(tzinfo=timezone.utc)
        ela_mock.return_value = [
            Entry(
                type='minor',
                description='change 1',
                pr=Pr(
                    id=1,
                    text='text 1',
                    url='http://1',
                    merged_at=now - timedelta(days=1),
                ),
            )
        ]

        exit_mock.return_value = None

        # Mock responses for git commands
        def run_side_effect(cmd_args, **kwargs):
            result = type('obj', (object,), {})()
            result.returncode = 0
            result.stdout = ''
            result.stderr = ''
            if cmd_args == ['git', 'branch', '--show-current']:
                result.stdout = 'main\n'
            elif cmd_args == ['git', 'status', '--porcelain']:
                result.stdout = ''
            elif cmd_args[:2] == ['git', 'push']:
                result.returncode = 1
                result.stderr = 'Push failed'
            return result

        run_mock.side_effect = run_side_effect

        with TemporaryDirectory() as td:
            changelog = join(td.dirname, 'CHANGELOG.md')
            with open(changelog, 'w') as fh:
                fh.write('fin')

            init = join(td.dirname, basename(td.dirname))
            makedirs(init)
            init = join(init, '__init__.py')
            with open(init, 'w') as fh:
                fh.write("# __version__ = '0.1.3' #")

            config = Config(join(td.dirname, '.cl'), provider=None)

            result = cmd.run(
                self.MockArgs([], pr=True), config=config, root=td.dirname
            )

            self.assertIsNone(result)
            exit_mock.assert_called_with(1)

    @patch('changelet.entry.remove')
    @patch('changelet.command.bump.run')
    @patch('changelet.command.bump.Bump.exit')
    @patch('changelet.entry.Entry.load_all')
    @patch('changelet.command.bump._get_current_version')
    def test_pr_gh_create_fails(
        self, gcv_mock, ela_mock, exit_mock, run_mock, rm_mock
    ):
        cmd = Bump()

        gcv_mock.return_value = Version.parse('0.1.3')
        now = datetime.now().replace(tzinfo=timezone.utc)
        ela_mock.return_value = [
            Entry(
                type='minor',
                description='change 1',
                pr=Pr(
                    id=1,
                    text='text 1',
                    url='http://1',
                    merged_at=now - timedelta(days=1),
                ),
            )
        ]

        exit_mock.return_value = None

        # Mock responses for git commands
        def run_side_effect(cmd_args, **kwargs):
            result = type('obj', (object,), {})()
            result.returncode = 0
            result.stdout = ''
            result.stderr = ''
            if cmd_args == ['git', 'branch', '--show-current']:
                result.stdout = 'main\n'
            elif cmd_args == ['git', 'status', '--porcelain']:
                result.stdout = ''
            elif cmd_args[:2] == ['gh', 'pr']:
                result.returncode = 1
                result.stderr = 'PR creation failed'
            return result

        run_mock.side_effect = run_side_effect

        with TemporaryDirectory() as td:
            changelog = join(td.dirname, 'CHANGELOG.md')
            with open(changelog, 'w') as fh:
                fh.write('fin')

            init = join(td.dirname, basename(td.dirname))
            makedirs(init)
            init = join(init, '__init__.py')
            with open(init, 'w') as fh:
                fh.write("# __version__ = '0.1.3' #")

            config = Config(join(td.dirname, '.cl'), provider=None)

            result = cmd.run(
                self.MockArgs([], pr=True), config=config, root=td.dirname
            )

            self.assertIsNone(result)
            exit_mock.assert_called_with(1)
