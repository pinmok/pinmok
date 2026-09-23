# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2026-09-23

### Added

- Added `int_to_bytes`, `bytes_to_int`, `to_snake_case`, `to_compact_case`, and `to_camel_case` utility filters to
  `pinmok_tags`, featuring built-in error suppression to prevent template rendering crashes on invalid inputs.

### Fixed

- Fixed the issue where theme scanning only checked a single directory and optimized related methods to support
  multi-directory scanning.
- Fixed an issue where template names could not be localized. Template names now support multiple languages.

## [1.0.1] - 2026-07-05

### Fixed

- Fixed a bug where child menu items could disappear after repeated menu synchronization.

### Changed

- `menu_key` is now generated from each menu item's logical path instead of a hash, making it stable across re-syncs.

### Removed

- Removed unused admin menu caching code that had no effect on behavior.