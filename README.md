# ePACK - Enterprise Video Processing & Analysis Container Kit

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.1.6-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-Commercial-red.svg)](LICENSE)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF)](https://github.com/Binhnguyen041280/ePACK/actions)

## 📋 Overview

**ePACK** is an enterprise-grade desktop application for automated video processing, AI-powered event detection, and intelligent tracking analysis. Built with production-ready infrastructure, comprehensive testing, and professional development workflows.

### ✨ Key Features

- **🎥 Multi-Source Processing**: Local storage and Google Drive cloud integration
- **🤖 AI-Powered Detection**: Advanced hand detection and QR code recognition
- **📊 Intelligent Analysis**: Smart tracking code detection with configurable ROI
- **⚡ Multi-Mode Processing**: First Run, Default (auto-scan), and Custom modes
- **🌐 Cloud Sync**: Automatic synchronization with Google Drive
- **💳 License Management**: Integrated payment system with secure license activation
- **🔐 OAuth Security**: Secure Google authentication with encrypted credentials
- **🌍 Multi-Timezone**: IANA timezone management with DST awareness
- **🚀 Production Ready**: Professional packaging, CI/CD, and deployment infrastructure

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Binhnguyen041280/ePACK.git
cd ePACK

# Install as Python package
pip install -e .

# Run from CLI
epack
epack-server
```

### Development Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python database.py

# Frontend
cd frontend
npm ci
npm run dev
```

### Docker Deployment

```bash
docker-compose up -d --build
# Frontend: http://localhost:3000
# Backend: http://localhost:8080
```

---

## 🧪 Testing

```bash
# Backend tests
pytest tests/ -v --cov=backend

# Frontend tests
cd frontend && npm test

# All quality checks
make lint && make test
```

---

## 📚 Documentation

- **User Guides**: [docs/vtrack-official/for-users/](docs/vtrack-official/for-users/)
- **Developer Guides**: [docs/vtrack-official/for-developers/](docs/vtrack-official/for-developers/)
- **API Reference**: [docs/backend API.md](docs/backend%20API.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security**: [SECURITY.md](SECURITY.md)

---

## 🏗️ Architecture

### Technology Stack

**Frontend**: Next.js 15.1.6, React 19, TypeScript 5.7.2, Chakra UI
**Backend**: Flask 3.1.0, Gunicorn, Python 3.10+, SQLite
**AI/ML**: MediaPipe, OpenCV-contrib, TensorFlow
**DevOps**: Docker, GitHub Actions, Dependabot

### System Overview

```
Frontend (Next.js) → Backend API (Flask/Gunicorn) → Database (SQLite)
                          ↓
                  AI Processing (MediaPipe/OpenCV)
                          ↓
                  Cloud Sync (Google Drive)
```

---

## 📦 Package Distribution

ePACK is PyPI-ready:

```bash
# Build package
python -m build

# Install from wheel
pip install dist/epack-1.0.0-py3-none-any.whl
```

---

## 🛠️ Development

### Project Structure

```
ePACK/
├── backend/              # Flask backend (129 Python files)
│   ├── modules/         # 18 modular components
│   ├── models/          # AI models (WeChat QR)
│   └── gunicorn.conf.py # Production config
├── frontend/            # Next.js frontend (99 TS files)
├── tests/              # Comprehensive test suite
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── e2e/           # End-to-end tests
├── docs/              # Documentation (8.2MB)
├── .github/           # CI/CD workflows
├── pyproject.toml     # Package configuration
└── docker-compose.yml # Container orchestration
```

### Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

---

## 📊 CI/CD Pipeline

✅ Backend tests (Python 3.10, 3.11, 3.12)
✅ Frontend tests (Node 18.x, 20.x)
✅ Linting (Black, Flake8, ESLint)
✅ Security scanning (Trivy, Safety)
✅ Automated dependency updates

---

## 📄 License

Copyright (c) 2025 ePACK Team. All rights reserved.

Commercial License - See [LICENSE](LICENSE) for details.

Third-party components: Flask (BSD-3), Next.js (MIT), OpenCV (Apache 2.0), MediaPipe (Apache 2.0)

---

## 🤝 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/Binhnguyen041280/ePACK/issues)
- **Email**: support@epack.app

---

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

**Current Version**: 1.0.0 - Initial enterprise release with production-ready infrastructure

---

<div align="center">

**[Documentation](https://github.com/Binhnguyen041280/ePACK/tree/main/docs)** •
**[Issues](https://github.com/Binhnguyen041280/ePACK/issues)** •
**[Contributing](CONTRIBUTING.md)** •
**[Security](SECURITY.md)**

Made with ❤️ by the ePACK Team

</div>
