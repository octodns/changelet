#
#
#


from datetime import datetime
from json import loads
from logging import getLogger
from subprocess import PIPE, run

from .pr import Pr


class GitHubCli:

    def __init__(self, org, repo, changelog_directory, max_lookback=50):
        self.log = getLogger('GitHubCli[{org}/{repo}]')
        self.log.info(
            '__init__: changelog_directory=%s, max_lookback=%d',
            changelog_directory,
            max_lookback,
        )
        self.org = org
        self.repo = repo
        self.changelog_directory = changelog_directory
        self.max_lookback = max_lookback

        self._prs = None

    @property
    def prs(self):
        if self._prs is None:
            # will be indexed by both id & filename
            prs = {}

            result = run(
                [
                    'gh',
                    'pr',
                    'list',
                    '--repo',
                    f'{self.org}/{self.repo}',
                    '--base',
                    'main',
                    '--state',
                    'merged',
                    f'--limit={self.max_lookback}',
                    '--json',
                    'files,mergedAt,number',
                ],
                check=True,
                stdout=PIPE,
            )

            for pr in loads(result.stdout):
                number = pr['number']
                url = f'https://github.com/{self.org}/{self.repo}/pull/{number}'
                merged_at = datetime.fromisoformat(pr['mergedAt'])

                files = [
                    f['path']
                    for f in pr['files']
                    if f['path'].startswith(self.changelog_directory)
                ]
                if not files:
                    # no changelog entries, ignore it
                    continue

                pr = Pr(
                    id=number, text=f'#{number}', url=url, merged_at=merged_at
                )
                prs[number] = pr
                for filename in files:
                    prs[filename] = pr
            self._prs = prs

        return self._prs

    def pr_by_id(self, id):
        return self.prs.get(id)

    def pr_by_filename(self, filename):
        return self.prs.get(filename)
