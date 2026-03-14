## 0.5.0 - 2026-03-14

Minor:
* Make module name configurable via Config instead of deriving from directory name in bump - [#44](https://github.com/octodns/changelet/pull/44)
* Make base branch configurable in GitHubCli provider instead of hardcoding main - [#43](https://github.com/octodns/changelet/pull/43)
* Migrate bump command subprocess calls to provider - [#42](https://github.com/octodns/changelet/pull/42)
* Replace interactive git add -p with explicit file staging - [#42](https://github.com/octodns/changelet/pull/42)
* Add --continue support - [#32](https://github.com/octodns/changelet/pull/32)
* Add support for CHANGELET_GIT_ADD_ARGS and CHANGELET_GIT_COMMIT_ARGS environment variables to pass additional arguments to git commands - [#28](https://github.com/octodns/changelet/pull/28)

Patch:
* Remove misleading None default from Config.load_yaml filename parameter - [#41](https://github.com/octodns/changelet/pull/41)
* Wire up EntryType enum for type validation - [#40](https://github.com/octodns/changelet/pull/40)
* Limit _parse_file split to preserve --- in descriptions - [#39](https://github.com/octodns/changelet/pull/39)
* Restore sys.path after _get_current_version import - [#38](https://github.com/octodns/changelet/pull/38)
* Add trailing newline when saving changelog entry files - [#35](https://github.com/octodns/changelet/pull/35)
* Fix startswith(directory) path prefix matching to avoid false matches on similarly named directories - [#34](https://github.com/octodns/changelet/pull/34)
* Fix has_staged check in create --commit to run before staging the entry - [#33](https://github.com/octodns/changelet/pull/33)

## 0.4.0 - 2025-11-26

Minor:
* Add --ignore-local-changes option to bump --pr command - [#25](https://github.com/octodns/changelet/pull/25)
* Add support for bump --pr to bump and generate standard pr - [#23](https://github.com/octodns/changelet/pull/23)

Patch:
* Fix issue with PYTHONPATH order finding wrong version of module - [#22](https://github.com/octodns/changelet/pull/22)
* Improve description cleanup with .strip - [#21](https://github.com/octodns/changelet/pull/21)

## 0.3.0 - 2025-09-10

Minor:
* Add commit prefix for changelog only commits - [#14](https://github.com/octodns/changelet/pull/14)

## 0.2.0 - 2025-08-15

Minor:
* Add support for --logging cmdline arg - [#11](https://github.com/octodns/changelet/pull/11)
* Add --quiet flag to create - [#10](https://github.com/octodns/changelet/pull/10)
* Add support for --commit arg to create - [#9](https://github.com/octodns/changelet/pull/9)

Patch:
* Fix org and repo in PR urls - [#12](https://github.com/octodns/changelet/pull/12)

## 0.1.0 - 2025-07-26

Major:
* Initial Release
