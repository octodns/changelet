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
                            'files': [{'path': 'other-file.md'}],
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

    @patch('changelet.github.run')
    def test_add_file(self, run_mock):
        gh = GitHubCli()
        filename = 'foo.bar'

        run_mock.reset_mock()
        gh.add_file(filename)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertTrue(filename in args)

    @patch('changelet.github.run')
    def test_has_staged(self, run_mock):
        gh = GitHubCli()

        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock('')
        self.assertFalse(gh.has_staged())
        run_mock.assert_called_once()

        run_mock.reset_mock()
        run_mock.return_value = self.ResultMock('There is output, thus changes')
        self.assertTrue(gh.has_staged())
        run_mock.assert_called_once()

    @patch('changelet.github.run')
    def test_commit(self, run_mock):
        gh = GitHubCli()
        description = 'Hello World'

        run_mock.reset_mock()
        gh.commit(description)
        run_mock.assert_called_once()
        args = run_mock.call_args[0][0]
        self.assertTrue(description in args)
