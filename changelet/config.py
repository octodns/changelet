#
#
#

from importlib import import_module
from os.path import isfile, join
from sys import version_info
from typing import TYPE_CHECKING

from yaml import safe_load as yaml_load

# https://pypi.org/project/tomli/#intro
# based on code in black.file
if version_info >= (3, 11):  # pragma: no cover
    try:
        from tomllib import load as toml_load
    except ImportError:
        # Help users on older alphas
        if not TYPE_CHECKING:
            from tomli import load as toml_load
else:  # pragma: no cover
    from tomli import load as toml_load


class Config:

    @classmethod
    def build_default(cls, directory='.'):
        directory = join(directory, '.changelog')
        return Config(
            directory=directory,
            provider={'class': 'changelet.github.GitHubCli'},
        )

    @classmethod
    def build_pyproject_toml(cls, directory='.'):
        pyproject_toml = join(directory, 'pyproject.toml')
        if isfile(pyproject_toml):
            with open(pyproject_toml, 'rb') as fh:
                config = toml_load(fh).get('tool', {}).get('changelet')
                if config:
                    return Config(**config)

    @classmethod
    def build_changelet_yaml(cls, directory='.'):
        changelet_yaml = join(directory, '.changelet.yaml')
        if isfile(changelet_yaml):
            with open(changelet_yaml, 'rb') as fh:
                config = yaml_load(fh)
                if config:
                    return Config(**config)

    @classmethod
    def build(cls, config=None, directory='.'):
        return (
            cls.build_changelet_yaml(directory=directory)
            or cls.build_pyproject_toml(directory=directory)
            or cls.build_default(directory=directory)
        )

    def __init__(self, directory, provider):
        self.directory = directory

        self._provider_config = provider
        self._provider = None

    @property
    def provider(self):
        if self._provider is None:
            config = self._provider_config
            klass = config.pop('class')
            if isinstance(klass, str):
                module, klass = klass.rsplit('.', 1)
                module = import_module(module)
                klass = getattr(module, klass)
            self._provider = klass(directory=self.directory, **config)
        return self._provider

    def __repr__(self):
        return f'Config<directory={self.directory}, provider={self.provider}>'
