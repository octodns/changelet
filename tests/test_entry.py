#
#
#

from datetime import datetime, timedelta
from os import makedirs
from os.path import isfile, join
from unittest import TestCase

from helpers import TemporaryDirectory
from yaml import safe_load

from changelet.config import Config
from changelet.entry import Entry
from changelet.pr import Pr


class DummyProvider:

    def pr_by_id(self, root, directory, id, merged_at=None):
        text = '#{id}'
        url = f'https://github.com/octodns/changelet/pull/{id}'
        merged_at = merged_at or datetime(2025, 7, 1, 1, 2, 3)
        return Pr(id=id, text=text, url=url, merged_at=merged_at)

    def pr_by_filename(self, root, directory, filename):
        return self.pr_by_id(root=root, directory=directory, id=filename)


class TestEntry(TestCase):

    def test_repr(self):
        # smoke
        Entry(type='none', description='', pr=None, filename='').__repr__()

    def test_properties(self):
        entry = Entry(type='none', description='', pr=None, filename='')
        # no pr means epoch, none=0
        self.assertEqual((0, Entry.EPOCH), entry._ordering)

        # change the description, no change to ordering
        entry.description = 'foo'
        self.assertEqual((0, Entry.EPOCH), entry._ordering)

        # change the filename, no change to ordering
        entry.filename = 'foo.md'
        self.assertEqual((0, Entry.EPOCH), entry._ordering)

        # change the type, get an updated ordering
        entry.type = 'minor'
        self.assertEqual((2, Entry.EPOCH), entry._ordering)

        # add a PR, update ordering
        merged_at = datetime(2025, 1, 12)
        entry.pr = Pr(id=42, text='', url='', merged_at=merged_at)
        self.assertEqual((2, merged_at), entry._ordering)

    def test_save_and_load(self):
        provider = DummyProvider()
        pr = provider.pr_by_id(root='', directory='', id=43)

        # if it doesn't have a filename remove is a noop
        entry = Entry(type='minor', description='ephemeral')
        self.assertFalse(entry.remove())

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
            config = Config(directory='.cl', provider=None)
            config._provider = provider
            loaded = Entry.load(filename=filename, config=config)
            self.assertEqual(entry.type, loaded.type)
            self.assertEqual(entry.description, loaded.description)
            self.assertEqual(entry.pr.id, loaded.pr.id)
            self.assertEqual(entry.filename, loaded.filename)

            copy = entry.copy()
            self.assertEqual(entry.type, copy.type)
            self.assertEqual(entry.description, copy.description)
            self.assertEqual(entry.pr.id, copy.pr.id)
            self.assertEqual(entry.filename, copy.filename)

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
            copy = Entry.load(filename=copy.filename, config=config)
            self.assertEqual(entry.type, copy.type)
            self.assertEqual(entry.description, copy.description)
            # pr id will be the filename b/c of our test/mock provider
            self.assertEqual(entry.filename, copy.pr.id)
            self.assertEqual(entry.filename, copy.filename)

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

            # remove the file and make sure it's gone
            self.assertTrue(entry.remove())
            self.assertFalse(isfile(entry.filename))

    def test_load_all(self):
        provider = DummyProvider()

        with TemporaryDirectory() as td:
            config = Config(directory=join(td.dirname, '.cl'), provider=None)
            config._provider = provider

            # nothing, not even directory, initially exists
            self.assertEqual([], Entry.load_all(config=config))

            for i, type in enumerate(
                ('minor', 'patch', 'minor', 'none', 'major', 'none')
            ):
                description = f'Change {i:04d}'
                filename = join(config.directory, f'change-{i:04d}.md')
                pr = provider.pr_by_id(root='', directory='', id=i)
                entry = Entry(
                    type=type, description=description, pr=pr, filename=filename
                )
                entry.save()

            filename = join(config.directory, 'other.txt')
            with open(filename, 'w') as fh:
                fh.write('ignored')

            entries = list(Entry.load_all(config=config))
            self.assertEqual(6, len(entries))

    def test_text(self):
        type = 'none'
        description = 'This does not matter'
        filename = join('.changelog', 'the-change.md')
        entry = Entry(type=type, description=description, filename=filename)
        self.assertEqual(f'* {description}', entry.text)

        provider = DummyProvider()
        pr = provider.pr_by_id(root='', directory='', id=43)
        entry = Entry(
            type=type, description=description, pr=pr, filename=filename
        )
        self.assertEqual(f'* {description} - {pr.url}', entry.text)

    def test_markdown(self):
        type = 'none'
        description = 'This does not matter'
        filename = join('.changelog', 'the-change.md')
        entry = Entry(type=type, description=description, filename=filename)
        self.assertEqual(f'* {description}', entry.markdown)

        provider = DummyProvider()
        pr = provider.pr_by_id(root='', directory='', id=43)
        entry = Entry(
            type=type, description=description, pr=pr, filename=filename
        )
        self.assertEqual(
            f'* {description} - [{pr.text}]({pr.url})', entry.markdown
        )

    def test_sorting(self):
        config = Config(directory='.cl', provider=None)
        provider = DummyProvider()
        config._provider = provider
        now = datetime.now()

        entries = []
        for i, type in enumerate(
            ('minor', 'patch', 'minor', 'none', 'major', 'none')
        ):
            description = f'Change {i:04d}'
            filename = join(config.directory, f'change-{i:04d}.md')
            pr = provider.pr_by_id(
                root='', directory='', id=i, merged_at=now - timedelta(days=i)
            )
            entry = Entry(
                type=type, description=description, pr=pr, filename=filename
            )
            entries.append(entry)
        self.assertEqual(i + 1, len(entries))
        # initially in creation order
        self.assertEqual([0, 1, 2, 3, 4, 5], [e.pr.id for e in entries])
        # ascending
        entries.sort()
        self.assertEqual([5, 3, 1, 2, 0, 4], [e.pr.id for e in entries])
        self.assertEqual(
            ['none', 'none', 'patch', 'minor', 'minor', 'major'],
            [e.type for e in entries],
        )
