# Developer Agent Guide for changelet

This repository contains the `changelet` utility, a standalone Python command line tool and library for CHANGELOG and release version management. Spun out of octoDNS, it helps projects automate changelog creation, verification, and version bumping.

> [!IMPORTANT]
> **Core Workflow and Guidelines**
>
> All agents working on this repository must read and follow the general instructions and workflow guidelines defined in the core octoDNS `AGENTS.md` file.
> - **Local check**: Look for the file at `../octodns/AGENTS.md`.
> - **Remote check**: If the local file is not available, fetch it from GitHub: [octoDNS Core AGENTS.md](https://github.com/octodns/octodns/raw/refs/heads/main/AGENTS.md).
>
> You must align your code structure, style, pull request guidelines, and overall development workflows with the instructions specified there.

## Repository & Module Information

### Key Components

- **CLI Entry Point**: [main.py](file:///home/ross/octodns/changelet/changelet/main.py) (function [main](file:///home/ross/octodns/changelet/changelet/main.py#L13-L80)) defines the command-line interface, argument parsing, logging setup, and config loading.
- **Configuration Management**: [Config](file:///home/ross/octodns/changelet/changelet/config.py#L25-L122) (in [config.py](file:///home/ross/octodns/changelet/changelet/config.py)) loads configurations from `pyproject.toml` (under `[tool.changelet]`) or `.changelet.yaml`, and manages metadata provider instantiation.
- **Metadata/GitHub Integration**: [GitHubCli](file:///home/ross/octodns/changelet/changelet/github.py#L51-L157) and [GitHubActions](file:///home/ross/octodns/changelet/changelet/github.py#L14-L48) (in [github.py](file:///home/ross/octodns/changelet/changelet/github.py)) query PR metadata from GitHub or GitHub Actions environment.
- **Commands** (registered in [command/__init__.py](file:///home/ross/octodns/changelet/changelet/command/__init__.py)):
  - [Create](file:///home/ross/octodns/changelet/changelet/command/create.py#L14-L135): Generates a new YAML changelet entry file in the `.changelog/` directory.
  - [Check](file:///home/ross/octodns/changelet/changelet/command/check.py#L12-L37): Validates that a changelog entry exists and conforms to standard formats for the active branch or pull request.
  - [Bump](file:///home/ross/octodns/changelet/changelet/command/bump.py#L19-L215): Computes the next version (major, minor, patch) based on pending changelog entries, updates version fields in files like `setup.py` or `pyproject.toml`, compiles the entries into `CHANGELOG.md`, and archives the processed YAML entries.
- **Entry Representation**: [Entry](file:///home/ross/octodns/changelet/changelet/entry.py#L11-L129) represents a single changelog entry (storing type, description, author, pull request reference, etc.) and handles serialization to/from YAML format.

### CLI Commands & Usage

`changelet` operates via three main sub-commands:
1. **`changelet create --type <type> "description"`**:
   Creates a new changelog file in the `.changelog/` directory. Options for `--type` are:
   - `major`: Backward-incompatible breaking changes.
   - `minor`: Backward-compatible new functionality.
   - `patch`: Bug fixes or minor updates.
   - `none`: Tooling, documentation, or other non-user-facing updates.
2. **`changelet check`**:
   Ensures that a changelog entry is present and valid for the current PR or branch.
3. **`changelet bump`**:
   Bumps the package version and updates `CHANGELOG.md`.

## Development & Testing

- **Setup Script**: Run `./script/bootstrap` to create a virtual environment, install runtime and development dependencies (including `black`, `isort`, `pyflakes`, and `pytest`), and configure git pre-commit hooks.
- **Test Suite**: Run unit tests using `pytest` via `./script/test` (or `pytest tests/`). Test files are located in [tests/](file:///home/ross/octodns/changelet/tests).
- **Code Coverage**: Verify code coverage using `./script/coverage`.

## Key Constraints & Behaviors

- **Python Version**: Targets Python `>=3.9`.
- **Formatting**: Code formatting is enforced via `black` (version `>=26.0.0,<27.0.0`) and `isort`.
- **Non-Provider nature**: `changelet` is a release management tool, not an octoDNS DNS provider. It does not implement DNS providers, zone synchronization, or DNS record types.
