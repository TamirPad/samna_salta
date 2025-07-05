# Samna Salta - Traditional Yemenite Food Ordering Bot 🥙

[![Tests](https://img.shields.io/badge/tests-168%20passing-brightgreen)](./tests/)
[![Coverage](https://img.shields.io/badge/coverage-54%25-yellow)](./tests/)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

A sophisticated Telegram bot for ordering traditional Yemenite cuisine, built with clean architecture principles and comprehensive testing.

## 🏗️ Architecture Overview

Samna Salta follows **Clean Architecture** and **Domain-Driven Design** principles:

```
┌─────────────────────────────────────────────────────────────┐
│                    🌐 Interface Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Telegram Bot   │  │   REST API      │                  │
│  │   Handlers      │  │   Endpoints     │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                  📋 Application Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Use Cases     │  │      DTOs       │                  │
│  │  (Business      │  │   (Data         │                  │
│  │   Logic)        │  │  Transfer)      │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    🎯 Domain Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │    Entities     │  │ Value Objects   │                  │
│  │  (Customer,     │  │  (Money, ID,    │                  │
│  │   Product)      │  │   Phone)        │                  │
│  └─────────────────┘  └─────────────────┘                  │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Repositories   │  │   Domain        │                  │
│  │  (Interfaces)   │  │   Services      │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 ⚙️ Infrastructure Layer                     │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Database      │  │     Cache       │                  │
│  │ (SQLAlchemy)    │  │   (Redis)       │                  │
│  └─────────────────┘  └─────────────────┘                  │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Security      │  │   Monitoring    │                  │
│  │ (Rate Limit)    │  │ (Performance)   │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Features

### Core Features
- **🍽️ Menu Management**: Traditional Yemenite dishes with options
- **🛒 Shopping Cart**: Add, modify, and checkout orders
- **👥 Customer Management**: Registration and profile management
- **📊 Order Analytics**: Business intelligence and reporting
- **💳 Payment Processing**: Secure payment handling
- **🚚 Delivery Management**: Pickup and delivery options

### Technical Features
- **🔒 Security**: Rate limiting, input validation, XSS protection
- **⚡ Performance**: Query optimization, caching, async operations
- **📈 Monitoring**: Real-time performance metrics and alerts
- **🧪 Testing**: 54% coverage with 168 passing tests
- **📚 Documentation**: Comprehensive API and architecture docs

## 🏃‍♂️ Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL
- Redis (optional, for caching)
- Telegram Bot Token

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/samna_salta.git
cd samna_salta
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
python -m src.infrastructure.database.operations init_db
```

6. **Run the bot**
```bash
python main.py
```

### Environment Configuration

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/samna_salta

# Security Configuration
SECRET_KEY=your_secret_key_here
RATE_LIMIT_ENABLED=true

# Cache Configuration (Optional)
REDIS_URL=redis://localhost:6379/0

# Monitoring Configuration
MONITORING_ENABLED=true
PERFORMANCE_ALERTS=true
```

## 📚 API Documentation

### Core Use Cases

#### Customer Registration
```python
from src.application.use_cases.customer_registration_use_case import CustomerRegistrationUseCase

# Register a new customer
result = await customer_use_case.register_customer(
    telegram_id=TelegramId(123456789),
    customer_name=CustomerName("Ahmed Al-Yemeni"),
    phone_number=PhoneNumber("+972501234567")
)
```

#### Cart Management
```python
from src.application.use_cases.cart_management_use_case import CartManagementUseCase

# Add item to cart
request = AddToCartRequest(
    telegram_id=123456789,
    product_id=1,
    quantity=2,
    options={"spice_level": "medium"}
)

result = await cart_use_case.add_to_cart(request)
```

#### Order Creation
```python
from src.application.use_cases.order_creation_use_case import OrderCreationUseCase

# Create order
order_data = {
    "customer_id": 1,
    "delivery_method": "pickup",
    "special_instructions": "Extra zhug sauce"
}

result = await order_use_case.create_order(order_data)
```

### Value Objects

#### Money Handling
```python
from src.domain.value_objects.money import Money
from decimal import Decimal

# Create money amounts
price = Money(Decimal("25.50"), "ILS")
tax = Money(Decimal("4.33"), "ILS")
total = price + tax  # Money(29.83, "ILS")

# Display formatting
print(price.format_display())  # "25.50 ILS"
```

#### Phone Number Validation
```python
from src.domain.value_objects.phone_number import PhoneNumber

# International format required
phone = PhoneNumber("+972501234567")  # ✅ Valid
phone = PhoneNumber("050-123-4567")   # ❌ Invalid (no country code)
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test categories
python -m pytest tests/test_domain.py          # Domain layer tests
python -m pytest tests/test_use_cases.py       # Application layer tests
python -m pytest tests/test_repositories.py    # Infrastructure tests
python -m pytest tests/test_integration.py     # Integration tests

# Run performance tests
python -m pytest tests/test_load_testing.py -v

# Run security tests
python -m pytest tests/test_security_enhancements.py -v
```

### Test Coverage Report
```
Name                                          Stmts   Miss  Cover
-----------------------------------------------------------------
src/application/use_cases/                      631    192   70%
src/domain/entities/                             91     14   85%
src/domain/value_objects/                       259     40   85%
src/infrastructure/repositories/                563    261   54%
src/infrastructure/cache/                       168     82   51%
src/infrastructure/security/                    287    150   48%
-----------------------------------------------------------------
TOTAL                                          3694   1681   54%
```

## 🔒 Security Features

### Rate Limiting
```python
from src.infrastructure.security.rate_limiter import RateLimiter

rate_limiter = RateLimiter()

# Check if user action is allowed
if rate_limiter.is_allowed(user_id, action="order_create"):
    # Process order
    pass
else:
    # Rate limit exceeded
    pass
```

### Input Validation
```python
from src.infrastructure.utilities.security import SecurityValidator

validator = SecurityValidator()

# Validate and sanitize input
if validator.validate_input(user_input):
    safe_input = validator.sanitize_input(user_input)
    # Process safe input
```

### XSS Protection
All user inputs are automatically sanitized to prevent XSS attacks:
- HTML tags are escaped
- JavaScript injection attempts are blocked
- SQL injection patterns are detected and prevented

## 📈 Performance Monitoring

### Real-time Metrics
```python
from src.infrastructure.performance.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()
monitor.start_monitoring(interval=5.0)

# Record custom metrics
monitor.record_request(response_time=0.150, success=True)
monitor.record_db_query(query_time=0.025)

# Get performance summary
summary = monitor.get_performance_summary()
```

### Load Testing
```bash
# Run load tests
python -m pytest tests/test_load_testing.py::TestLoadTesting::test_concurrent_customer_registration -v

# Performance benchmarks
python -m pytest tests/test_load_testing.py::TestLoadTesting::test_high_volume_cart_operations -v
```

## 🛠️ Development Guide

### Project Structure
```
samna_salta/
├── src/
│   ├── domain/                    # Domain layer (business logic)
│   │   ├── entities/             # Business entities
│   │   ├── value_objects/        # Value objects
│   │   └── repositories/         # Repository interfaces
│   ├── application/              # Application layer
│   │   ├── use_cases/           # Business use cases
│   │   └── dtos/                # Data transfer objects
│   └── infrastructure/          # Infrastructure layer
│       ├── database/            # Database implementations
│       ├── cache/               # Caching layer
│       ├── security/            # Security features
│       ├── performance/         # Performance optimization
│       └── utilities/           # Helper utilities
├── tests/                       # Test suite
├── docs/                        # Documentation
└── requirements.txt             # Dependencies
```

### Adding New Features

1. **Domain First**: Define entities and value objects
2. **Use Cases**: Implement business logic
3. **Infrastructure**: Add repository implementations
4. **Tests**: Write comprehensive tests
5. **Documentation**: Update docs

### Code Style
- Follow PEP 8 conventions
- Use type hints throughout
- Document all public methods
- Write descriptive commit messages

## 📊 Menu Items

### Traditional Dishes

| Dish | Description | Price (ILS) |
|------|-------------|-------------|
| **Jachnun** | Traditional pastry with grated tomato and zhug | 25.00 |
| **Malawach** | Fried flatbread with tomato and hard-boiled egg | 28.00 |
| **Sabich** | Pita with fried eggplant, egg, and tahini | 32.00 |
| **Kubaneh** | Sweet bread traditionally baked overnight | 22.00 |
| **Hilbeh** | Fenugreek soup (available specific days) | 18.00 |

### Beverages

| Drink | Description | Price (ILS) |
|-------|-------------|-------------|
| **Adeni Tea** | Traditional spiced tea | 12.00 |
| **Coffee** | Turkish-style coffee | 15.00 |
| **Fresh Juice** | Seasonal fruit juices | 18.00 |

## 🚀 Deployment

### Docker Deployment
```bash
# Build image
docker build -t samna-salta .

# Run with docker-compose
docker-compose up -d
```

### Production Configuration
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  app:
    image: samna-salta:latest
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://user:pass@db:5432/samna_salta
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: samna_salta
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Health Checks
```bash
# Check application health
curl http://localhost:8000/health

# Check database connectivity
curl http://localhost:8000/health/db

# Check cache connectivity
curl http://localhost:8000/health/cache
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests before committing
python -m pytest tests/ --cov=src
```

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check database configuration
python -c "from src.infrastructure.database.operations import get_engine; print(get_engine())"
```

**Telegram Bot Not Responding**
```bash
# Verify bot token
python -c "import telegram; bot = telegram.Bot('YOUR_TOKEN'); print(bot.get_me())"
```

**Performance Issues**
```bash
# Enable performance monitoring
export MONITORING_ENABLED=true
export PERFORMANCE_ALERTS=true
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Traditional Yemenite cuisine recipes and cultural guidance
- Clean Architecture principles by Robert C. Martin
- Domain-Driven Design concepts by Eric Evans
- The Python and Telegram Bot API communities

## 📞 Support

- **Documentation**: [Full documentation](./docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/samna_salta/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/samna_salta/discussions)

---

**Made with ❤️ for preserving Yemenite culinary traditions** 🇾🇪 