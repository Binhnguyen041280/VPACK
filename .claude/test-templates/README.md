# VPACK Test Templates

Directory này chứa generated test code từ lessons.

## Cấu trúc

Mỗi lesson có thể generate ra:
- Python test script (pytest)
- JavaScript test script (Jest)
- API test collection (cURL hoặc Postman)

## Test Templates Available

_(Templates sẽ được tạo từ lessons)_

### Planned Templates:

1. **test_config.py** - Test 5-step configuration wizard
2. **test_login.py** - Test authentication flow
3. **test_roi.py** - Test ROI configuration

## Usage

### Python Tests (pytest)

```bash
# Chạy tất cả tests
pytest .claude/test-templates/

# Chạy specific test
pytest .claude/test-templates/test_config.py

# Chạy với verbose output
pytest -v .claude/test-templates/test_config.py
```

### Prerequisites

```bash
# Install test dependencies
pip install pytest requests python-dotenv

# Set environment variables
export VPACK_BACKEND_URL="http://localhost:8080"
export VPACK_FRONTEND_URL="http://localhost:3000"
export TEST_GOOGLE_TOKEN="your-test-token"  # Nếu cần
```

## Generated Test Structure

```python
import pytest
import requests
import os

class TestVpackConfig:
    """Auto-generated from lesson: vpack-config-flow.json"""

    BASE_URL = "http://localhost:8080"

    def setup_method(self):
        self.session = requests.Session()
        self.context = {}

    def test_step_1_brand_name(self):
        """Test Step 1: Brand Name configuration"""
        # Implementation from lesson
        pass

    def test_complete_flow(self):
        """Test all 5 steps in sequence"""
        # Implementation from lesson
        pass
```

## Notes

- Tests tự động generated từ lessons
- Có thể customize sau khi generate
- Nên commit tests vào git để track changes
