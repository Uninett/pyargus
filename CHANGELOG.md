# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added support for the new API token refresh endpoint introduced in Argus 1.29.

### Changed

- Implemented [ruff](https://docs.astral.sh/ruff/) for linting and code formatting.

### Removed

- Explicit support for Python 3.7 was dropped.

## [0.5.0] - 2024-09-13

### Added

- Added support for the new `metadata` attribute introduced in Argus 1.17.0.

### Fixed

- Ignore unknown incident attributes from Argus API, so as not to crash when new versions of Argus introduce new attributes

### Changed

- Switched from `setup.cfg` to using `pyproject.toml`
- Test on all Python versions from 3.7 through 3.11.
