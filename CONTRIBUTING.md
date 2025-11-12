# Contributing to ePACK

Thank you for your interest in contributing to ePACK! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow. Please be respectful and constructive in your interactions with other contributors.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Node.js 18.x or 20.x (LTS)
- Git
- Docker (optional, for containerized development)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ePACK.git
   cd ePACK
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/Binhnguyen041280/ePACK.git
   ```

## Development Setup

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Initialize database
python database.py
```

### Frontend Setup

```bash
cd frontend
npm ci
```

### Install Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

## Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Test your changes**:
   ```bash
   # Backend tests
   pytest tests/

   # Frontend tests
   cd frontend && npm test

   # Run linters
   make lint
   ```

4. **Commit your changes** following our commit guidelines

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub

## Coding Standards

### Python (Backend)

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for code formatting (line length: 100)
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use [Flake8](https://flake8.pycqa.org/) for linting
- Use [mypy](http://mypy-lang.org/) for type checking
- Add type hints to all functions (minimum 70% coverage goal)
- Write docstrings for all public functions (Google style)

**Example:**

```python
def process_video(video_path: str, config: dict) -> bool:
    """Process a video file with the given configuration.

    Args:
        video_path: Path to the video file to process.
        config: Configuration dictionary with processing parameters.

    Returns:
        True if processing was successful, False otherwise.

    Raises:
        FileNotFoundError: If video file doesn't exist.
        ValueError: If config is invalid.
    """
    # Implementation here
    pass
```

### TypeScript/JavaScript (Frontend)

- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use [Prettier](https://prettier.io/) for code formatting
- Use [ESLint](https://eslint.org/) for linting
- Use TypeScript strict mode
- Prefer functional components with hooks
- Use meaningful variable and function names

**Example:**

```typescript
interface VideoConfig {
  path: string
  mode: 'auto' | 'manual'
}

export const processVideo = async (config: VideoConfig): Promise<boolean> => {
  // Implementation here
}
```

### General Guidelines

- Keep functions small and focused (< 50 lines)
- Use descriptive variable names (no single-letter names except for loops)
- Add comments for complex logic
- Avoid magic numbers (use constants)
- Handle errors gracefully
- Log important events

## Testing Guidelines

### Backend Testing

- Write unit tests for all new functions
- Write integration tests for API endpoints
- Maintain test coverage > 70%
- Use pytest fixtures for test setup
- Mock external dependencies

**Test file structure:**

```
tests/
├── unit/
│   ├── test_video_processing.py
│   └── test_qr_detection.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_database.py
└── e2e/
    └── test_workflow.py
```

### Frontend Testing

- Write unit tests for components
- Write integration tests for user flows
- Use Jest and React Testing Library
- Test user interactions, not implementation details

## Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring (no feature or bug fix)
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, build, etc.)
- **perf**: Performance improvements
- **ci**: CI/CD changes

### Examples

```
feat(backend): add QR code detection for WeChat codes

Implement WeChat QR code detection using opencv-contrib-python.
This adds support for detecting QR codes in packing videos.

Closes #123
```

```
fix(frontend): resolve dashboard rendering issue on mobile

The dashboard was not rendering correctly on mobile devices
due to CSS grid issues. Updated responsive breakpoints.

Fixes #456
```

## Pull Request Process

1. **Update documentation** if needed (README, API docs, etc.)

2. **Ensure all tests pass**:
   ```bash
   make test
   make lint
   ```

3. **Update CHANGELOG.md** with your changes

4. **Create PR** with a clear title and description:
   - Describe what changes you made
   - Explain why you made these changes
   - Reference any related issues
   - Add screenshots for UI changes

5. **Address review comments** promptly

6. **Squash commits** if requested

7. **Wait for approval** from maintainers (minimum 1 approval required)

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added/updated
- [ ] CHANGELOG.md updated
```

## Reporting Bugs

### Before Reporting

1. Check if the bug has already been reported in [Issues](https://github.com/Binhnguyen041280/ePACK/issues)
2. Try the latest version to see if the bug still exists
3. Collect relevant information (logs, screenshots, etc.)

### Bug Report Template

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g., macOS 12.0, Ubuntu 20.04]
- Python version: [e.g., 3.10.5]
- Node version: [e.g., 18.16.0]
- ePACK version: [e.g., 2.1.0]

**Additional context**
Any other relevant information.
```

## Feature Requests

We welcome feature requests! Please:

1. Check if the feature has already been requested
2. Provide a clear use case
3. Explain why this feature would be useful
4. Be open to discussion about implementation

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Alternative solutions or features you've considered.

**Additional context**
Any other context, screenshots, or mockups.
```

## Questions?

If you have questions about contributing, please:

1. Check the [documentation](https://github.com/Binhnguyen041280/ePACK/tree/main/docs)
2. Search existing [issues](https://github.com/Binhnguyen041280/ePACK/issues)
3. Create a new issue with the "question" label

Thank you for contributing to ePACK! 🎉
