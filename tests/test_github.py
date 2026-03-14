#
#
#

from json import dumps
from unittest import TestCase
from unittest.mock import patch

from changelet.github import GitHubCli


class TestGitHubCli(TestCase):

    class ResultMock:

        def __init__(self, stdout):
            self.stdout = stdout

    def test_repr(self):
        # smoke
        GitHubCli().__repr__()

    def test_pr_by_id(self):
        gh = GitHubCli()
        # pre-fill the cache
        gh._prs = {42: 'pr'}
        self.assertEqual(
            'pr', gh.pr_by_id(root='', directory='.changelog', id=42)
        )
        self.assertIsNone(gh.pr_by_id(root='', directory='.changelog', id=43))

    def test_pr_by_filename(self):
        gh = GitHubCli()
        # pre-fill the cache
        gh._prs = {'.changelog/abc123.md': 'pr'}
        self.assertEqual(
            'pr',
            gh.pr_by_filename(
                root='', directory='.changelog', filename='.changelog/abc123.md'
            ),
        )
        self.assertIsNone(
            gh.pr_by_filename(
                root='',
                directory='.changelog',
                filename='.changelog/unknown.md',
            )
        )

    @patch('changelet.github.GitHubCli._run')
    def test_cache_filling_cmd_params_default(self, run_mock):
        gh = GitHubCli()

        run_mock.side_effect = [{'nameWithOwner': 'name/with'}, []]
        self.assertEqual({}, gh.prs(root='', directory='.changelog'))
        calls = run_mock.call_args_list
        self.assertEqual(2, len(calls))
        # 2nd call is the one we're interested in
        args = calls[1].args[0]
        # make sure our repo was not part of the call params
        self.assertFalse('--repo' in args)
        # make sure the default limit is applied
        self.assertTrue('--limit=50' in args)

    @patch('changelet.github.run')
    def test_cache_filling_cmd_params_base_branch(self, run_mock):
        gh = GitHubCli(repo='org/repo', base_branch='master')

        run_mock.return_value = self.ResultMock('[]')
        self.assertEqual({}, gh.prs(root='', directory='.changelog'))
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertTrue('master' in args)
        # main should not be in the args
        self.assertFalse('main' in args)

    @patch('changelet.github.run')
    def test_cache_filling_cmd_params(self, run_mock):
        gh = GitHubCli(max_lookback=75, repo='org/repo')

        # we passed a repo to the ctor, so no gh repo view call happens
        run_mock.return_value = self.ResultMock('[]')
        self.assertEqual({}, gh.prs(root='', directory='.changelog'))
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        # make sure our org and repo are part of the call params
        self.assertTrue('org/repo' in args)
        # make sure the default limit is applied
        self.assertTrue('--limit=75' in args)

    @patch('changelet.github.run')
    def test_cache_filling_parsing(self, run_mock):
        gh = GitHubCli()

        run_mock.side_effect = [
            self.ResultMock(dumps({'nameWithOwner': 'theorg/darepo'})),
            self.ResultMock(
                dumps(
                    [
                        {
                            'files': [{'path': '.changelog/abcd1234.md'}],
                            'mergedAt': '2025-07-01T10:42',
                            'number': '42',
                        },
                        {
                            'files': [
                                {'path': '.changelog/foo.md'},
                                {'path': '.changelog/bar.md'},
                            ],
                            'mergedAt': '2025-07-02T10:42',
                            'number': '43',
                        },
                        {
                            'files': [
                                {'path': '.changelog-extra/something.md'}
                            ],
                            'mergedAt': '2025-07-03T10:42',
                            'number': '44',
                        },
                        {
                            'files': [{'path': 'other-file.txt'}],
                            'mergedAt': '2025-07-04T10:42',
                            'number': '45',
                        },
                    ]
                )
            ),
        ]
        prs = gh.prs(root='', directory='.changelog')
        self.assertEqual(2, len(run_mock.call_args))
        self.assertEqual(
            [
                '.changelog/abcd1234.md',
                '.changelog/bar.md',
                '.changelog/foo.md',
                '42',
                '43',
            ],
            sorted(prs.keys()),
        )
        # make sure the results of the org/repo lookup are used in the URLs
        self.assertEqual(
            'https://github.com/theorg/darepo/pull/42', prs['42'].url
        )

        # make sure a second call uses the cache
        run_mock.reset_mock()
        pr = gh.prs(root='', directory='.changelog')['43']
        self.assertEqual('43', pr.id)
        run_mock.assert_not_called()

    @patch('changelet.github.run')
    def test_changelog_entries_in_branch_base_branch(self, run_mock):
        gh = GitHubCli(base_branch='develop')

        run_mock.return_value = self.ResultMock(b'.foobar/blip.md')
        gh.changelog_entries_in_branch(root='', directory='.foobar')
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'diff', '--name-only', 'origin/develop'], args)

    @patch('changelet.github.run')
    def test_changelog_entries_in_branch(self, run_mock):
        gh = GitHubCli()

        directory = '.foobar'

        # no directory
        run_mock.reset_mock()
        self.assertEqual(
            set(), gh.changelog_entries_in_branch(root='', directory=directory)
        )
        run_mock.assert_called_once()

        # no changes
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(b'')
        self.assertEqual(
            set(), gh.changelog_entries_in_branch(root='', directory=directory)
        )
        run_mock.assert_called_once()

        # non changelog changes
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(b'foo/bar.py')
        self.assertEqual(
            set(), gh.changelog_entries_in_branch(root='', directory=directory)
        )
        run_mock.assert_called_once()

        # changelog changes
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(
            b'foo/bar.py\n.foobar/blip.md\nother.txt'
        )
        self.assertEqual(
            {'.foobar/blip.md'},
            gh.changelog_entries_in_branch(root='', directory=directory),
        )
        run_mock.assert_called_once()

        # prefix match should not include files from similar directories
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(
            b'.foobar/blip.md\n.foobar-extra/blip.md'
        )
        self.assertEqual(
            {'.foobar/blip.md'},
            gh.changelog_entries_in_branch(root='', directory=directory),
        )
        run_mock.assert_called_once()

    @patch('changelet.github.run')
    def test_add_file(self, run_mock):
        gh = GitHubCli()
        filename = 'foo.bar'

        run_mock.reset_mock()
        gh.add_file(filename)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertTrue(filename in args)

    @patch('changelet.github.environ')
    @patch('changelet.github.run')
    def test_add_file_with_extra_args(self, run_mock, environ_mock):
        gh = GitHubCli()
        filename = 'foo.bar'

        # Test with single extra argument
        run_mock.reset_mock()
        environ_mock.get.return_value = '--force'
        gh.add_file(filename)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'add', '--force', filename], args)

        # Test with multiple extra arguments
        run_mock.reset_mock()
        environ_mock.get.return_value = '--force --verbose'
        gh.add_file(filename)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'add', '--force', '--verbose', filename], args)

        # Test with empty string
        run_mock.reset_mock()
        environ_mock.get.return_value = ''
        gh.add_file(filename)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'add', filename], args)

        # Test with whitespace only
        run_mock.reset_mock()
        environ_mock.get.return_value = '   '
        gh.add_file(filename)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'add', filename], args)

    @patch('changelet.github.run')
    def test_has_staged(self, run_mock):
        gh = GitHubCli()

        # no staged files
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(b'')
        self.assertFalse(gh.has_staged())
        run_mock.assert_called_once()

        # staged files present
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(b'src/foo.py\nREADME.md')
        self.assertTrue(gh.has_staged())
        run_mock.assert_called_once()

        # exclude the only staged file
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(b'.changelog/abc123.md')
        self.assertFalse(gh.has_staged(exclude='.changelog/abc123.md'))

        # exclude one of multiple staged files
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(
            b'src/foo.py\n.changelog/abc123.md'
        )
        self.assertTrue(gh.has_staged(exclude='.changelog/abc123.md'))

    @patch('changelet.github.run')
    def test_staged_changelog_entry(self, run_mock):
        gh = GitHubCli()
        directory = '.changelog'

        # no staged changelog entry
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(b'')
        self.assertIsNone(gh.staged_changelog_entry(directory))
        run_mock.assert_called_once()

        # staged non-changelog files only
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(b'src/foo.py\nREADME.md')
        self.assertIsNone(gh.staged_changelog_entry(directory))

        # staged changelog entry present
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(
            b'src/foo.py\n.changelog/abc123.md\n.changelog/def456.md'
        )
        self.assertEqual(
            '.changelog/abc123.md', gh.staged_changelog_entry(directory)
        )

        # staged .md file but not in the changelog directory
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(b'docs/notes.md')
        self.assertIsNone(gh.staged_changelog_entry(directory))

        # staged .md file in a similarly named directory
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(
            b'.changelog-extra/something.md'
        )
        self.assertIsNone(gh.staged_changelog_entry(directory))

    @patch('changelet.github.run')
    def test_commit(self, run_mock):
        gh = GitHubCli()
        description = 'Hello World'

        run_mock.reset_mock()
        gh.commit(description)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertTrue(description in args)

    @patch('changelet.github.run')
    def test_current_branch(self, run_mock):
        gh = GitHubCli()

        run_mock.return_value = self.ResultMock('main\n')
        self.assertEqual('main', gh.current_branch())
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'branch', '--show-current'], args)

    @patch('changelet.github.run')
    def test_has_local_changes(self, run_mock):
        gh = GitHubCli()

        # no changes
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock('')
        self.assertFalse(gh.has_local_changes())
        run_mock.assert_called_once()

        # has changes
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(' M foo.py\n')
        self.assertTrue(gh.has_local_changes())
        run_mock.assert_called_once()

    @patch('changelet.github.run')
    def test_pull(self, run_mock):
        gh = GitHubCli()

        gh.pull()
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'pull'], args)

    @patch('changelet.github.run')
    def test_create_branch(self, run_mock):
        gh = GitHubCli()

        gh.create_branch('my-branch')
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'checkout', '-b', 'my-branch'], args)

    @patch('changelet.github.run')
    def test_push_branch(self, run_mock):
        gh = GitHubCli()

        gh.push_branch('my-branch')
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'push', '-u', 'origin', 'my-branch'], args)

    @patch('changelet.github.run')
    def test_create_pr(self, run_mock):
        gh = GitHubCli()

        run_mock.return_value = self.ResultMock(
            'https://github.com/org/repo/pull/1\n'
        )
        url = gh.create_pr('My Title', 'My Body')
        self.assertEqual('https://github.com/org/repo/pull/1', url)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(
            [
                'gh',
                'pr',
                'create',
                '--title',
                'My Title',
                '--body',
                'My Body',
                '--assignee',
                '@me',
            ],
            args,
        )

    @patch('changelet.github.environ')
    @patch('changelet.github.run')
    def test_commit_with_extra_args(self, run_mock, environ_mock):
        gh = GitHubCli()
        description = 'Hello World'

        # Test with single extra argument
        run_mock.reset_mock()
        environ_mock.get.return_value = '--no-verify'
        gh.commit(description)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(
            ['git', 'commit', '--no-verify', '--message', description], args
        )

        # Test with multiple extra arguments
        run_mock.reset_mock()
        environ_mock.get.return_value = '--no-verify --signoff'
        gh.commit(description)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(
            [
                'git',
                'commit',
                '--no-verify',
                '--signoff',
                '--message',
                description,
            ],
            args,
        )

        # Test with quoted arguments
        run_mock.reset_mock()
        environ_mock.get.return_value = (
            '--no-verify --author="John Doe <john@example.com>"'
        )
        gh.commit(description)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(
            [
                'git',
                'commit',
                '--no-verify',
                '--author=John Doe <john@example.com>',
                '--message',
                description,
            ],
            args,
        )

        # Test with empty string
        run_mock.reset_mock()
        environ_mock.get.return_value = ''
        gh.commit(description)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'commit', '--message', description], args)

        # Test with whitespace only
        run_mock.reset_mock()
        environ_mock.get.return_value = '   '
        gh.commit(description)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertEqual(['git', 'commit', '--message', description], args)
