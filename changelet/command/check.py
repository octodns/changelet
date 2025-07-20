#
#
#

from sys import argv, exit, stderr


class Check:
    name = 'check'
    description = (
        'Checks to see if the current branch contains a changelog entry'
    )

    def configure(self, parser):
        return None

    def exit(self, code):
        exit(code)

    def run(self, args, config):
        if config.provider.changelog_entries_in_branch():
            return self.exit(0)

        print(
            f'PR is missing required changelog file, run {argv[0]} create',
            file=stderr,
        )
        self.exit(1)
