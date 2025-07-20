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
        GitHubCli(directory='.changelog').__repr__()

    def test_pr_by_id(self):
        gh = GitHubCli(directory='.changelog')
        # pre-fill the cache
        gh._prs = {42: 'pr'}
        self.assertEqual('pr', gh.pr_by_id(42))
        self.assertIsNone(gh.pr_by_id(43))

    def test_pr_by_filename(self):
        gh = GitHubCli(directory='.changelog')
        # pre-fill the cache
        gh._prs = {'.changelog/abc123.md': 'pr'}
        self.assertEqual('pr', gh.pr_by_filename('.changelog/abc123.md'))
        self.assertIsNone(gh.pr_by_filename('.changelog/unknown.md'))

    @patch('changelet.github.run')
    def test_cache_filling_cmd_params_default(self, run_mock):
        gh = GitHubCli(directory='.changelog')

        run_mock.return_value = self.ResultMock('[]')
        self.assertEqual({}, gh.prs)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        # make sure our repo was not part of the call params
        self.assertFalse('--repo' in args)
        # make sure the default limit is applied
        self.assertTrue('--limit=50' in args)

    @patch('changelet.github.run')
    def test_cache_filling_cmd_params(self, run_mock):
        gh = GitHubCli(directory='.changelog', max_lookback=75, repo='org/repo')

        run_mock.return_value = self.ResultMock('[]')
        self.assertEqual({}, gh.prs)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        # make sure our org and repo are part of the call params
        self.assertTrue('org/repo' in args)
        # make sure the default limit is applied
        self.assertTrue('--limit=75' in args)

    @patch('changelet.github.run')
    def test_cache_filling_parsing(self, run_mock):
        gh = GitHubCli(directory='.changelog')

        run_mock.return_value = self.ResultMock(
            dumps(
                [
                    {
                        'files': [{'path': '.changelog/abcd1234.md'}],
                        'mergedAt': '2025-07-01T10:42Z',
                        'number': '42',
                    },
                    {
                        'files': [
                            {'path': '.changelog/foo.md'},
                            {'path': '.changelog/bar.md'},
                        ],
                        'mergedAt': '2025-07-02T10:42Z',
                        'number': '43',
                    },
                    {
                        'files': [{'path': 'other-file.md'}],
                        'mergedAt': '2025-07-03T10:42Z',
                        'number': '44',
                    },
                    {
                        'files': [{'path': 'other-file.txt'}],
                        'mergedAt': '2025-07-04T10:42Z',
                        'number': '45',
                    },
                ]
            )
        )
        prs = gh.prs
        run_mock.assert_called_once()
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

        # make sure a second call uses the cache
        pr = gh.prs['43']
        self.assertEqual('43', pr.id)
        run_mock.assert_called_once()

    @patch('changelet.github.isdir')
    @patch('changelet.github.run')
    def test_changelog_entries_in_branch(self, run_mock, isdir_mock):
        directory = '.foobar'
        gh = GitHubCli(directory=directory)

        # no directory
        isdir_mock.reset_mock()
        run_mock.reset_mock()
        isdir_mock.return_value = False
        self.assertEqual(set(), gh.changelog_entries_in_branch())
        isdir_mock.assert_called_once_with(directory)
        run_mock.assert_not_called()

        # fake the dir existing
        isdir_mock.return_value = True

        # no changes
        isdir_mock.reset_mock()
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(b'')
        self.assertEqual(set(), gh.changelog_entries_in_branch())
        isdir_mock.assert_called_once_with(directory)
        run_mock.assert_called_once()
        # custom directory was used in command
        args = run_mock.call_args[0][0]
        self.assertEqual(directory, args[-1])

        # non changelog changes
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(b'foo/bar.py')
        self.assertEqual(set(), gh.changelog_entries_in_branch())
        run_mock.assert_called_once()

        # changelog changes
        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock(
            b'foo/bar.py\n.foobar/blip.md\nother.txt'
        )
        self.assertEqual({'.foobar/blip.md'}, gh.changelog_entries_in_branch())
        run_mock.assert_called_once()
