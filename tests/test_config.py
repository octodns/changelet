#
#
#

from os.path import join
from unittest import TestCase

from helpers import TemporaryDirectory

from changelet.config import Config
from changelet.github import GitHubCli


class TestConfig(TestCase):

    class DummyProvider:

        def __init__(self, directory):
            self.directory = directory

    def test_base(self):
        config = Config(
            directory='.foo', provider={'class': self.DummyProvider}
        )
        self.assertEqual('.foo', config.directory)
        # was passed down into provider
        provider = config.provider
        self.assertEqual('.foo', provider.directory)
        # refetch gets the same instance
        self.assertEqual(provider, config.provider)

    def test_provider(self):
        config = Config(
            directory='.foo', provider={'class': self.DummyProvider}
        )
        self.assertIsInstance(config.provider, self.DummyProvider)

        config = Config(
            provider={
                'class': 'changelet.github.GitHubCli',
                'repo': 'octodns/changelet',
            }
        )
        provider = config.provider
        self.assertEqual('octodns/changelet', provider.repo)
        self.assertEqual('.changelog', provider.directory)

    def test_build_pyproject_toml(self):
        with TemporaryDirectory() as td:
            # no file
            config = Config.build_pyproject_toml(td.dirname)
            self.assertIsNone(config)

            # no section
            with open(join(td.dirname, 'pyproject.toml'), 'w') as fh:
                fh.write(
                    '''[tool.other]
key = "value"
'''
                )
            config = Config.build_pyproject_toml(td.dirname)
            self.assertIsNone(config)

            # valid
            with open(join(td.dirname, 'pyproject.toml'), 'w') as fh:
                fh.write(
                    '''[tool.changelet]
directory = ".location"
provider.class = "changelet.github.GitHubCli"
provider.repo = "org/repo"
'''
                )
            config = Config.build_pyproject_toml(td.dirname)
            self.assertEqual('.location', config.directory)
            self.assertIsInstance(config.provider, GitHubCli)
            self.assertEqual('org/repo', config.provider.repo)

            config = Config.build(td.dirname)
            self.assertTrue(config)

    def test_build_changelet_yaml(self):
        with TemporaryDirectory() as td:
            # no file
            config = Config.build_changelet_yaml(td.dirname)
            self.assertIsNone(config)

            # no section
            with open(join(td.dirname, '.changelet.yaml'), 'w') as fh:
                fh.write(
                    '''---
'''
                )
            config = Config.build_changelet_yaml(td.dirname)
            self.assertIsNone(config)

            # valid
            with open(join(td.dirname, '.changelet.yaml'), 'w') as fh:
                fh.write(
                    '''---
directory: .location
provider:
    class: changelet.github.GitHubCli
    repo: org/repo
'''
                )
            config = Config.build_changelet_yaml(td.dirname)
            self.assertEqual('.location', config.directory)
            self.assertIsInstance(config.provider, GitHubCli)
            self.assertEqual('org/repo', config.provider.repo)

            config = Config.build(td.dirname)
            self.assertTrue(config)
