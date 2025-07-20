#
#
#

from datetime import datetime
from os import makedirs
from os.path import join
from unittest import TestCase

from helpers import TemporaryDirectory
from yaml import safe_load

from changelet.entry import Entry
from changelet.pr import Pr


class DummyProvider:

    def pr_by_id(self, id):
        text = '#{id}'
        url = f'https://github.com/octodns/changelet/pull/{id}'
        merged_at = datetime(2025, 7, 1, 1, 2, 3)
        return Pr(id=id, text=text, url=url, merged_at=merged_at)

    def pr_by_filename(self, filename):
        return self.pr_by_id(filename)


class TestEntry(TestCase):

    def test_save_and_load(self):
        provider = DummyProvider()
        pr = provider.pr_by_id(43)

        with TemporaryDirectory() as td:
            type = 'none'
            description = 'This does not matter'
            directory = join(td.dirname, '.changelog')
            filename = join(directory, 'the-change.md')
            entry = Entry(
                type=type, description=description, pr=pr, filename=filename
            )
            self.assertEqual(type, entry.type)
            self.assertEqual(description, entry.description)
            self.assertEqual(pr, entry.pr)
            self.assertEqual(filename, entry.filename)

            # create the parent dir
            makedirs(directory)

            # save with the default filename
            entry.save()

            with open(entry.filename, 'r') as fh:
                pieces = fh.read().split('---\n')
                data = safe_load(pieces[1])
                self.assertEqual(type, data['type'])
                # we gave it a PR before safe so it's id be recorded in there
                self.assertEqual(pr.id, data['pr'])
                self.assertEqual(description, pieces[2])

            # load what was saved
            loaded = Entry.load(filename, provider)
            self.assertEqual(entry, loaded)

            copy = entry.copy()
            self.assertEqual(entry, copy)
            # remove the PR to test behavior for actual files in a repo
            copy.pr = None
            # this will overwrite the original file, but we're done with it
            # anyway
            copy.save()
            # append a ending newline, as may be the case if someone manually
            # edited the changelog entry,
            with open(copy.filename, 'a') as fh:
                fh.write('\n')
            # and then load, this time w/o a PR so by filename
            copy = Entry.load(copy.filename, provider)
            self.assertEqual(entry, copy)

            # no PR
            entry.pr = None
            # and a new filename will create a new file
            new_filename = join(directory, 'changed.md')
            entry.filename = new_filename
            entry.save(filename=new_filename)
            # filename was updated
            self.assertEqual(new_filename, entry.filename)
            with open(new_filename, 'r') as fh:
                self.assertTrue('pr:' not in fh.read())

    def test_text(self):
        type = 'none'
        description = 'This does not matter'
        filename = join('.changelog', 'the-change.md')
        entry = Entry(type=type, description=description, filename=filename)
        self.assertEqual(f'* {description}', entry.text)

        provider = DummyProvider()
        pr = provider.pr_by_id(43)
        entry = Entry(
            type=type, description=description, pr=pr, filename=filename
        )
        self.assertEqual(f'* {description} - {pr.url}', entry.text)

    def test_sorting(self):
        type = 'none'
        description = 'This does not matter'
        filename = join('.changelog', 'the-change.md')
        entry = Entry(type=type, description=description, filename=filename)
        self.assertEqual(f'* {description}', entry.markdown)

        provider = DummyProvider()
        pr = provider.pr_by_id(43)
        entry = Entry(
            type=type, description=description, pr=pr, filename=filename
        )
        self.assertEqual(f'* {description} - {pr.markdown}', entry.markdown)
