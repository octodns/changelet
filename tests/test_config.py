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
        pass

    def test_repr(self):
        # smoke
        Config().__repr__()

    def test_default(self):
        config = Config()
        self.assertEqual('', config.root)
        self.assertEqual('.changelog', config.directory)
        self.assertEqual('Changelog: ', config.commit_prefix)
        self.assertEqual(
            {'class': 'changelet.github.GitHubCli'}, config._provider_config
        )
        self.assertIsInstance(config.provider, GitHubCli)
        # after fetching provider config is reset
        self.assertIsNone(config._provider_config)

    def test_overrides(self):
        klass = self.DummyProvider
        config = Config(
            root='.foo',
            directory='.bar',
            commit_prefix='abc: ',
            provider={'class': klass},
        )
        self.assertEqual('.foo', config.root)
        self.assertEqual('.bar', config.directory)
        self.assertEqual('abc: ', config.commit_prefix)
        self.assertIsInstance(config.provider, self.DummyProvider)

    def test_provider(self):
        config = Config(provider={'class': self.DummyProvider})
        self.assertIsInstance(config.provider, self.DummyProvider)

        config.provider = {
            'class': 'changelet.github.GitHubCli',
            'repo': 'octodns/changelet',
        }
        provider = config.provider
        self.assertIsInstance(provider, GitHubCli)
        self.assertEqual('octodns/changelet', provider.repo)

    def test_load_pyproject_toml(self):
        with TemporaryDirectory() as td:

            # no section
            filename = join(td.dirname, 'pyproject.toml')
            with open(filename, 'w') as fh:
                fh.write(
                    '''[tool.other]
key = "value"
'''
                )
            config = Config()
            config.load_pyproject_toml(filename)
            defaults = Config()
            self.assertEqual(defaults.root, config.root)
            self.assertEqual(defaults.directory, config.directory)
            self.assertEqual(defaults._provider_config, config._provider_config)

            # valid
            with open(filename, 'w') as fh:
                fh.write(
                    '''[tool.changelet]
root = "blip"
directory = ".location"
provider.class = "changelet.github.GitHubCli"
provider.repo = "org/repo"
'''
                )
            config = Config()
            config.load_pyproject_toml(filename)
            self.assertEqual('blip', config.root)
            self.assertEqual('.location', config.directory)
            self.assertIsInstance(config.provider, GitHubCli)
            self.assertEqual('org/repo', config.provider.repo)

    def test_build_changelet_yaml(self):
        with TemporaryDirectory() as td:
            # no data
            filename = join(td.dirname, '.changelet.yaml')
            with open(filename, 'w') as fh:
                fh.write(
                    '''---
'''
                )
            config = Config()
            config.load_yaml(filename)
            defaults = Config()
            self.assertEqual(defaults.root, config.root)
            self.assertEqual(defaults.directory, config.directory)
            self.assertEqual(defaults._provider_config, config._provider_config)

            # valid
            with open(filename, 'w') as fh:
                fh.write(
                    '''---
root: blip
directory: .location
provider:
    class: changelet.github.GitHubCli
    repo: org/repo
'''
                )
            config = Config()
            config.load_yaml(filename)
            self.assertEqual('blip', config.root)
            self.assertEqual('.location', config.directory)
            self.assertIsInstance(config.provider, GitHubCli)
            self.assertEqual('org/repo', config.provider.repo)

    def test_build(self):

        # defaults, with actualy project's pyproject.toml
        config = Config.build()
        defaults = Config()
        self.assertEqual(defaults.root, config.root)
        self.assertEqual(defaults.directory, config.directory)
        self.assertEqual(defaults._provider_config, config._provider_config)

        # mostly defaults, non-existant root so we don't have a pyproject.toml
        config = Config.build(root='doesnt-exist')
        self.assertEqual('doesnt-exist', config.root)
        self.assertEqual(defaults.directory, config.directory)
        self.assertEqual(defaults._provider_config, config._provider_config)

        # create a pyproject.toml that overrides defaults
        # precedence
        with TemporaryDirectory() as td:
            with open(join(td.dirname, 'pyproject.toml'), 'w') as fh:
                fh.write(
                    '''[tool.changelet]
directory = "from_pyproject_toml"
'''
                )
            config = Config.build(root=td.dirname)
            # matches the root we passed in so that it'd fine the pyproject.toml
            self.assertEqual(td.dirname, config.root)
            self.assertEqual('from_pyproject_toml', config.directory)

            # create a .changelet.yaml to override pyproject.toml
            filename = join(td.dirname, '.changelet.yaml')
            with open(filename, 'w') as fh:
                fh.write(
                    '''---
directory: from_yaml
'''
                )
            config = Config.build(root=td.dirname)
            # matches the root we passed in so that it'd fine the pyproject.toml
            self.assertEqual(td.dirname, config.root)
            self.assertEqual('from_yaml', config.directory)

            # same result if we use an explicit config file
            config = Config.build(config=filename)
            self.assertEqual('', config.root)
            self.assertEqual('from_yaml', config.directory)

            # both config files exist, override with kwargs
            config = Config.build(root=td.dirname, directory='from_kwargs')
            # matches the root we passed in so that it'd fine the pyproject.toml
            self.assertEqual(td.dirname, config.root)
            self.assertEqual('from_kwargs', config.directory)
