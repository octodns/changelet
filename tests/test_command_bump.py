#
#
#

from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from os import makedirs
from os.path import basename, join
from sys import path, version_info
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

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
        def __init__(
            self,
            title,
            version=None,
            make_changes=False,
            pr=False,
            ignore_local_changes=False,
        ):
            self.title = title
            self.make_changes = make_changes
            self.version = version
            self.pr = pr
            self.ignore_local_changes = ignore_local_changes

    def test_configure(self):
        create = Bump()
        parser = ArgumentParser(exit_on_error=False)
        create.configure(parser)

        actions = {a.dest: a for a in parser._actions}

        self.assert_action(
            actions['make_changes'], flags=['--make-changes'], default=False
        )
        self.assert_action(actions['pr'], flags=['--pr'], default=False)
        self.assert_action(
            actions['ignore_local_changes'],
            flags=['--ignore-local-changes'],
            default=False,
        )
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

            original_path = path.copy()
            ver = _get_current_version(module_name, directory=td.dirname)
            self.assertEqual(3, ver.major)
            self.assertEqual(2, ver.minor)
            self.assertEqual(1, ver.patch)
            # sys.path should be restored after the call
            self.assertEqual(original_path, path)

    @patch('changelet.command.bump.path')
    def test_get_current_version_prepends_to_path(self, path_mock):
        # Verify that directory is prepended to sys.path so that it takes
        # precedence over virtualenv or system installs
        with TemporaryDirectory() as td:
            module_name = 'foo_bar'
            with open(join(td.dirname, f'{module_name}.py'), 'w') as fh:
                fh.write('__version__ = "3.2.1"')

            path_mock.__contains__ = lambda self, x: True

            try:
                _get_current_version(module_name, directory=td.dirname)
            except Exception:
                # import_module will fail with our mock, but we can
                # check the path call
                pass

            # Verify that insert(0, ...) was called to prepend
            path_mock.insert.assert_called_once_with(0, td.dirname)

    def test_get_current_version_restores_path_on_error(self):
        original_path = path.copy()
        with self.assertRaises(ModuleNotFoundError):
            _get_current_version('nonexistent_module_xyz', directory='/tmp')
        # sys.path should be restored even when import fails
        self.assertEqual(original_path, path)


class TestVersion(TestCase):

    def test_smoke(self):
        # this is bascially semver.Version.parse so we'll leave the actual
        # testing to it, here we'll just make sure things are plumbed up
        self.assertEqual(Version(1, 22, 33), version('1.22.33'))
        with self.assertRaises(ValueError):
            version('1.foo.33')


class TestCommandBumpPR(TestCase):

    class MockArgs:
        def __init__(
            self,
            title,
            version=None,
            make_changes=False,
            pr=False,
            ignore_local_changes=False,
        ):
            self.title = title
            self.make_changes = make_changes
            self.version = version
            self.pr = pr
            self.ignore_local_changes = ignore_local_changes

    def _provider_mock(self, **overrides):
        provider = MagicMock()
        provider.current_branch.return_value = 'main'
        provider.has_local_changes.return_value = False
        provider.create_pr.return_value = 'https://github.com/test/repo/pull/1'
        for k, v in overrides.items():
            setattr(provider, k, v)
        return provider

    @patch('changelet.command.bump.Bump.exit')
    def test_pr_not_on_main(self, exit_mock):
        cmd = Bump()
        config = Config('.cl', provider=None)
        config._provider = self._provider_mock(
            current_branch=MagicMock(return_value='feature-branch')
        )

        exit_mock.return_value = None

        result = cmd.run(args=self.MockArgs([], pr=True), config=config)
        self.assertIsNone(result)
        exit_mock.assert_called_once_with(1)
        config.provider.current_branch.assert_called_once()

    @patch('changelet.command.bump.Bump.exit')
    def test_pr_with_unstaged_changes(self, exit_mock):
        cmd = Bump()
        config = Config('.cl', provider=None)
        config._provider = self._provider_mock(
            has_local_changes=MagicMock(return_value=True)
        )

        exit_mock.return_value = None

        result = cmd.run(args=self.MockArgs([], pr=True), config=config)
        self.assertIsNone(result)
        exit_mock.assert_called_once_with(1)

    @patch('changelet.entry.remove')
    @patch('changelet.command.bump.Bump.exit')
    @patch('changelet.entry.Entry.load_all')
    @patch('changelet.command.bump._get_current_version')
    def test_pr_success(self, gcv_mock, ela_mock, exit_mock, rm_mock):
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
            ),
            # entry without a filename (no file to stage)
            Entry(type='minor', description='change 2'),
        ]

        exit_mock.return_value = None

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
            provider_mock = self._provider_mock()
            config._provider = provider_mock

            # give only the first entry a filename
            ela_mock.return_value[0].filename = join(
                config.directory, 'ela-0000.md'
            )

            new_version, buf = cmd.run(
                self.MockArgs([], pr=True), config=config, root=td.dirname
            )

            self.assertEqual('0.2.0', new_version)

            # Verify provider calls
            provider_mock.current_branch.assert_called_once()
            provider_mock.has_local_changes.assert_called_once()
            provider_mock.pull.assert_called_once()
            provider_mock.create_branch.assert_called_once_with('rel-0-2-0')

            # Verify provider.add_file was called for changelog, init,
            # and only the entry with a filename
            add_calls = provider_mock.add_file.call_args_list
            self.assertEqual(3, len(add_calls))
            self.assertEqual(changelog, add_calls[0][0][0])
            self.assertEqual(init, add_calls[1][0][0])
            self.assertEqual(
                join(config.directory, 'ela-0000.md'), add_calls[2][0][0]
            )

            provider_mock.commit.assert_called_once_with(
                'Version 0.2.0 bump & changelog update'
            )
            provider_mock.push_branch.assert_called_once_with('rel-0-2-0')
            provider_mock.create_pr.assert_called_once_with(
                'Version 0.2.0 bump & changelog update', buf
            )

    @patch('changelet.entry.remove')
    @patch('changelet.command.bump.Bump.exit')
    @patch('changelet.entry.Entry.load_all')
    @patch('changelet.command.bump._get_current_version')
    def test_pr_ignore_local_changes(
        self, gcv_mock, ela_mock, exit_mock, rm_mock
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
            provider_mock = self._provider_mock()
            config._provider = provider_mock

            # give our entries filenames
            for i, entry in enumerate(ela_mock.return_value):
                entry.filename = join(config.directory, f'ela-{i:04d}.md')

            new_version, buf = cmd.run(
                self.MockArgs([], pr=True, ignore_local_changes=True),
                config=config,
                root=td.dirname,
            )

            self.assertEqual('0.2.0', new_version)

            # Verify has_local_changes was NOT called
            provider_mock.has_local_changes.assert_not_called()
