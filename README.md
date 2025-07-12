## ChangeLog and Release Management Tooling

A simple standalone Python module for CHANGELOG and release management. Spun out of [octoDNS](https://github.com/octodns/octodns/).

### Installation

#### Command line

```
pip install changelet
```

### Usage

TODO

### Development

See the [/script/](/script/) directory for some tools to help with the development process. They generally follow the [Script to rule them all](https://github.com/github/scripts-to-rule-them-all) pattern. Most useful is `./script/bootstrap` which will create a venv and install both the runtime and development related requirements. It will also hook up a pre-commit hook that covers most of what's run by CI.
