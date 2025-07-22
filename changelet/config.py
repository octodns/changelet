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
    DEFAULT_ROOT = ''

    @classmethod
    def build(cls, **kwargs):
        # create w/defaults
        config = Config()

        root = kwargs.get('root', cls.DEFAULT_ROOT)

        # override w/toml, if applicable
        pyproject_toml_filename = join(root, 'pyproject.toml')
        if isfile(pyproject_toml_filename):
            config.load_pyproject_toml(pyproject_toml_filename)

        # explicit yaml file
        yaml_filename = kwargs.get('config')
        if not yaml_filename:
            # default yaml file
            yaml_filename = join(root, '.changelet.yaml')
        # override w/yaml, if applicable
        if isfile(yaml_filename):
            config.load_yaml(yaml_filename)

        # override root w/command line arg, if applicable
        try:
            config.root = kwargs['root']
        except KeyError:
            pass

        # override directory w/command line arg, if applicable
        try:
            config.directory = kwargs['directory']
        except KeyError:
            pass

        return config

    def __init__(
        self,
        root=DEFAULT_ROOT,
        directory='.changelog',
        provider={'class': 'changelet.github.GitHubCli'},
    ):
        self.root = root
        self.directory = directory

        # will instantiate & configure
        self.provider = provider

    @property
    def provider(self):
        if self._provider_config is not None:
            value = dict(self._provider_config)
            klass = value.pop('class')
            if isinstance(klass, str):
                module, klass = klass.rsplit('.', 1)
                module = import_module(module)
                klass = getattr(module, klass)
            self._provider = klass(**value)
            self._provider_config = None
        return self._provider

    @provider.setter
    def provider(self, value):
        self._provider_config = value

    def load_pyproject_toml(self, filename):
        with open(filename, 'rb') as fh:
            config = toml_load(fh).get('tool', {}).get('changelet')
            if isinstance(config, dict):
                for k, v in config.items():
                    setattr(self, k, v)

    def load_yaml(self, filename=None):
        with open(filename, 'rb') as fh:
            config = yaml_load(fh)
            if isinstance(config, dict):
                for k, v in config.items():
                    setattr(self, k, v)

    def __repr__(self):
        return f'Config<root={self.root}, directory={self.directory}, provider={self.provider}>'
