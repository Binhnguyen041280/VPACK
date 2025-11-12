# Changelog

All notable changes to VPACK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive test suite with pytest and jest
- CI/CD pipeline with GitHub Actions
- Pre-commit hooks for code quality
- Python packaging with pyproject.toml
- Gunicorn WSGI server configuration for production
- Dependabot configuration for automated dependency updates
- Security scanning with Trivy
- Code coverage reporting
- Linting configs (.flake8, .prettierrc, .eslintrc)
- EditorConfig for consistent coding styles
- CONTRIBUTING.md and SECURITY.md documentation

### Changed
- Updated TypeScript from 4.9.5 to 5.7.2
- Updated package.json name from "horizon-ai-template-pro" to "vpack"
- Improved Dockerfile with Gunicorn instead of Flask dev server
- Enhanced docker-compose.yml with health checks
- Split requirements.txt into prod/dev/test files
- Fixed package-lock.json gitignore (now committed for reproducible builds)
- Improved .gitignore with better test coverage patterns

### Fixed
- GitHub Actions workflow (updated Node 14.x to 20.x)
- Removed broken frontend deploy workflow
- Fixed hardcoded branch names in workflows

## [2.1.0] - 2025-01-11

### Added
- Production-ready build automation with detailed scripts/build_all.sh
- Environment-aware configuration system
- Multi-deployment mode support (dev/docker/production/installed)
- Comprehensive Makefile with 30+ useful targets

### Changed
- Fixed exact package versions in requirements.txt for reproducible builds
- Updated opencv-python to opencv-contrib-python for WeChat QR support
- Environment-aware path resolution for cross-platform compatibility

### Fixed
- Missing dependencies in requirements.txt
- Hardcoded macOS paths replaced with environment-aware resolution

## [2.0.0] - 2024-02-06

### Added
- Multi-source video processing (local and cloud)
- Google Drive cloud integration with PyDrive2
- OAuth 2.0 authentication system
- PayOS payment integration
- License management system with RSA validation
- Multi-timezone support with IANA timezones
- Batch processing scheduler with APScheduler
- Dual logging system (app.log + event_processing.log)

### Changed
- Major architecture refactor
- Migrated to Next.js 15 for frontend
- Upgraded to React 19
- Flask 3.1.0 for backend

## [1.0.0] - 2023-06-20

### Added
- Initial release
- Video processing with MediaPipe and OpenCV
- QR code detection with pyzbar
- Hand detection for packing events
- ROI (Region of Interest) configuration
- SQLite database with WAL mode
- Flask REST API
- Next.js frontend with Chakra UI
- Docker containerization
- Basic documentation

---

## Types of Changes

- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` for vulnerability fixes

## Migration Guides

### Upgrading to 2.1.0

1. **Dependencies**: Run `pip install -r backend/requirements.txt`
2. **Frontend**: Run `npm ci` in frontend directory
3. **Database**: Backup existing database before running
4. **Configuration**: Check new environment variables in .env.example

### Upgrading to 2.0.0

1. **Breaking Change**: OAuth configuration required
2. **Database Migration**: Run `python database.py` to update schema
3. **New Features**: Configure cloud sync if needed

## Links

- [Repository](https://github.com/Binhnguyen041280/VPACK)
- [Issues](https://github.com/Binhnguyen041280/VPACK/issues)
- [Documentation](https://github.com/Binhnguyen041280/VPACK/tree/main/docs)
