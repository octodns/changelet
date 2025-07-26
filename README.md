## ChangeLog and Release Management Tooling

A simple standalone Python module for CHANGELOG and release management. Spun out of [octoDNS](https://github.com/octodns/octodns/).

### Installation

#### Command line

```console
pip install changelet
```

### Usage

For help with using the command

```console
changelet --help
```

In most cases the only command you're likely to encounter is `create`. It will be used to add a changelog entry to your branch/PR.

```console
changelet create --type (TYPE) Short description of your change to be included in the changelog
```

The options for type are
* `major` - rare for non-maintainers, a change that will break backwards compatibility and require users to take care when updating
* `minor` - adds new functionality that is either self contained or done in a completely backwards compatible manner
* `patch` - fixes an issue or bug with existing functionality
* `none` - change that should not be included in the CHANGELOG and will not directly impact users, e.g. documentation, README, tooling, ...

### Using changlet

Currently the tooling has only been tested with repositories in the octoDNS org, but it should be usable elsewhere. You'll want to have a look at the following for how to incorporate it into your repo and workflows.

* [(octodns) script/changelog](https://github.com/octodns/octodns/blob/main/script/changelog)
* [.git_hooks_pre-commit](.git_hooks_pre-commit) (and [script/bootstrap](script/bootstrap) which installs it)
* [.github/workflows/changelog.yml](.github/workflows/changelog.yml)

### Development

See the [/script/](/script/) directory for some tools to help with the development process. They generally follow the [Script to rule them all](https://github.com/github/scripts-to-rule-them-all) pattern. Most useful is `./script/bootstrap` which will create a venv and install both the runtime and development related requirements. It will also hook up a pre-commit hook that covers most of what's run by CI.
