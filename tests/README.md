# 🧪 Test Suite - Samna Salta Bot

This directory contains all tests for the Samna Salta Telegram bot, organized following industry best practices.

## 📁 Directory Structure

```
tests/
├── README.md                    # This file - test documentation
├── conftest.py                  # Shared pytest fixtures and configuration
├── pytest.ini                  # Pytest configuration
├── requirements-test.txt        # Test-specific dependencies
│
├── unit/                        # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_utils/              # Utility function tests
│   │   ├── test_helpers.py
│   │   ├── test_security.py
│   │   └── test_i18n.py
│   ├── test_services/           # Service layer tests
│   │   ├── test_cart_service.py
│   │   ├── test_order_service.py
│   │   └── test_notification_service.py
│   ├── test_models/             # Database model tests
│   │   ├── test_customer.py
│   │   ├── test_product.py
│   │   └── test_order.py
│   └── test_handlers/           # Handler unit tests
│       ├── test_start.py
│       ├── test_menu.py
│       └── test_cart.py
│
├── integration/                 # Integration tests (component interactions)
│   ├── __init__.py
│   ├── test_database/           # Database integration tests
│   │   ├── test_operations.py
│   │   └── test_repositories.py
│   ├── test_services/           # Service integration tests
│   │   ├── test_cart_workflow.py
│   │   └── test_order_workflow.py
│   └── test_api/                # API integration tests
│       └── test_telegram_api.py
│
├── e2e/                         # End-to-end tests (full user journeys)
│   ├── __init__.py
│   ├── test_user_flows/         # Complete user journey tests
│   │   ├── test_customer_registration.py
│   │   ├── test_order_placement.py
│   │   └── test_admin_operations.py
│   └── test_bot_integration.py  # Bot integration tests
│
├── fixtures/                    # Test data and fixtures
│   ├── __init__.py
│   ├── test_data.py             # Test data constants
│   ├── mock_data.py             # Mock data generators
│   └── sample_orders.json       # Sample order data
│
├── utils/                       # Test utilities and helpers
│   ├── __init__.py
│   ├── test_helpers.py          # Common test utilities
│   ├── mock_factory.py          # Mock object factories
│   └── assertions.py            # Custom assertions
│
└── reports/                     # Test reports and artifacts
    ├── coverage/                # Coverage reports
    ├── performance/             # Performance test results
    └── screenshots/             # E2E test screenshots
```

## 🎯 Test Categories

### **Unit Tests** (`/unit/`)
- **Purpose**: Test individual functions/methods in isolation
- **Speed**: Fast (< 100ms per test)
- **Scope**: Single function/class
- **Dependencies**: Mocked external dependencies
- **Examples**: Helper functions, service methods, model validation

### **Integration Tests** (`/integration/`)
- **Purpose**: Test component interactions
- **Speed**: Medium (100ms - 1s per test)
- **Scope**: Multiple components working together
- **Dependencies**: Real database, mocked external APIs
- **Examples**: Service workflows, database operations, API calls

### **End-to-End Tests** (`/e2e/`)
- **Purpose**: Test complete user journeys
- **Speed**: Slow (1s - 30s per test)
- **Scope**: Full application stack
- **Dependencies**: Real database, real external services
- **Examples**: Complete order flow, user registration, admin operations

## 🏷️ Naming Conventions

### **File Names**
- `test_*.py` - Test files
- `conftest.py` - Pytest configuration
- `*_test.py` - Alternative naming (not recommended)

### **Test Functions**
- `test_*` - Test functions
- `test_*_should_*` - Behavior-driven naming
- `test_*_when_*` - Condition-based naming

### **Test Classes**
- `Test*` - Test classes
- `*TestCase` - Alternative naming

## 📋 Test Guidelines

### **1. Test Structure (AAA Pattern)**
```python
def test_function_name():
    # Arrange - Setup test data
    input_data = "test"
    
    # Act - Execute function
    result = function_under_test(input_data)
    
    # Assert - Verify results
    assert result == "expected"
```

### **2. Test Naming**
```python
# Good
def test_add_to_cart_should_increase_item_count():
def test_user_registration_when_phone_already_exists():
def test_calculate_total_with_discount():

# Bad
def test_1():
def test_function():
def test_something():
```

### **3. Test Isolation**
- Each test should be independent
- Use `setup_method()` and `teardown_method()` for cleanup
- Don't rely on test execution order

### **4. Mocking Strategy**
```python
# Mock external dependencies
@patch('src.services.telegram_api.send_message')
def test_notification_service(mock_send):
    mock_send.return_value = True
    # Test implementation
```

## 🚀 Running Tests

### **Run All Tests**
```bash
# From project root
pytest tests/

# From tests directory
pytest
```

### **Run by Category**
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# E2E tests only
pytest tests/e2e/
```

### **Run with Coverage**
```bash
pytest tests/ --cov=src --cov-report=html
```

### **Run Specific Test**
```bash
pytest tests/unit/test_helpers.py::test_format_price
```

### **Run with Markers**
```bash
# Run only fast tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration
```

## 📊 Test Metrics

### **Coverage Targets**
- **Unit Tests**: 90%+ line coverage
- **Integration Tests**: 80%+ line coverage
- **E2E Tests**: Critical user paths covered

### **Performance Targets**
- **Unit Tests**: < 100ms per test
- **Integration Tests**: < 1s per test
- **E2E Tests**: < 30s per test

## 🔧 Configuration

### **pytest.ini**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
```

### **conftest.py**
```python
import pytest
from src.container import Container

@pytest.fixture
def container():
    """Provide test container"""
    return Container()

@pytest.fixture
def mock_bot():
    """Provide mock bot for testing"""
    return MagicMock()
```

## 🐛 Debugging Tests

### **Common Issues**
1. **Import Errors**: Check `PYTHONPATH` and relative imports
2. **Database Issues**: Ensure test database is separate
3. **Async Issues**: Use `@pytest.mark.asyncio` for async tests
4. **Mock Issues**: Verify mock setup and assertions

### **Debug Commands**
```bash
# Run with verbose output
pytest -v -s

# Run single test with debugger
pytest tests/unit/test_helpers.py::test_format_price -s --pdb

# Show test collection
pytest --collect-only
```

## 📈 Continuous Integration

### **GitHub Actions Example**
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r requirements-test.txt
          pytest tests/ --cov=src --cov-report=xml
```

## 🎯 Best Practices Summary

1. **Organize by test type** (unit, integration, e2e)
2. **Use descriptive test names** that explain behavior
3. **Keep tests independent** and isolated
4. **Mock external dependencies** in unit tests
5. **Use fixtures** for common setup
6. **Maintain high coverage** with meaningful tests
7. **Run tests frequently** during development
8. **Document test purpose** and expected behavior 