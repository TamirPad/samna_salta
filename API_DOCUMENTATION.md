# 🔗 Samna Salta Bot - API Documentation

## Overview

The Samna Salta Bot is a comprehensive Telegram bot application for ordering traditional Yemenite food products. This documentation covers all API endpoints, use cases, and integration points.

## 🏗️ Architecture

The bot follows Clean Architecture principles with clear separation of concerns:

- **Domain Layer**: Business entities and rules
- **Application Layer**: Use cases and business logic
- **Infrastructure Layer**: External services and data persistence
- **Presentation Layer**: Telegram bot handlers and user interface

## 🔧 Health Check Endpoints

### System Health
```
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "uptime": "2:30:45",
  "total_check_time": 0.234,
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database is healthy",
      "response_time": 0.045,
      "metadata": {
        "pool_size": 5,
        "checked_out": 2
      }
    },
    "cache": {
      "status": "healthy",
      "message": "Cache is healthy",
      "response_time": 0.012,
      "metadata": {
        "hit_rate": 0.85,
        "total_requests": 1250
      }
    }
  }
}
```

### Liveness Check
```
GET /health/live
```

**Response**:
```json
{
  "status": "alive",
  "timestamp": "2024-01-01T12:00:00Z",
  "uptime": "2:30:45"
}
```

### Readiness Check
```
GET /health/ready
```

**Response**:
```json
{
  "status": "ready",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "database": "healthy",
    "cache": "healthy"
  }
}
```

## 🔐 Authentication & Security

### Rate Limiting

The bot implements comprehensive rate limiting per user and action:

- **Start Command**: 5 requests per minute
- **Menu Browsing**: 20 requests per minute
- **Cart Operations**: 15 requests per minute
- **Order Placement**: 3 requests per 5 minutes
- **Admin Operations**: 10 requests per minute

### Input Validation

All user inputs are validated against:
- XSS attacks
- SQL injection attempts
- Code execution attempts
- Path traversal attacks

### Phone Number Validation

Israeli phone number format validation:
- Format: `+972XXXXXXXXX` or `05XXXXXXXX`
- Automatic normalization to international format

## 📊 Use Cases

### 1. Customer Registration Use Case

**Purpose**: Register new customers and handle returning customers

**Request**:
```python
CustomerRegistrationRequest(
    telegram_id=123456789,
    full_name="John Doe",
    phone_number="+972501234567",
    delivery_address="Tel Aviv, Israel"
)
```

**Response**:
```python
CustomerRegistrationResponse(
    success=True,
    customer_info=CustomerInfo(
        telegram_id=123456789,
        full_name="John Doe",
        phone_number="+972501234567",
        is_returning_customer=False
    )
)
```

**Business Rules**:
- Phone number must be unique
- Name must be between 2-50 characters
- Address is optional but recommended
- Returning customers are identified by phone number

### 2. Product Catalog Use Case

**Purpose**: Browse and search products by category

**Request**:
```python
ProductCatalogRequest(
    category="bread",  # Optional
    search_term="kubaneh",  # Optional
    include_inactive=False
)
```

**Response**:
```python
ProductCatalogResponse(
    success=True,
    products=[
        ProductInfo(
            id=1,
            name="Kubaneh",
            description="Traditional Yemenite bread",
            price=25.0,
            category="bread",
            is_available=True
        )
    ]
)
```

**Supported Categories**:
- `bread` - Traditional breads (Kubaneh, Lahoh)
- `hilbeh` - Hilbeh preparations
- `samneh` - Clarified butter products
- `red_bisbas` - Red Bisbas sauce

### 3. Cart Management Use Case

**Purpose**: Add, remove, and manage cart items

**Add to Cart**:
```python
AddToCartRequest(
    telegram_id=123456789,
    product_id=1,
    quantity=2
)
```

**Remove from Cart**:
```python
RemoveFromCartRequest(
    telegram_id=123456789,
    product_id=1,
    quantity=1  # Optional, removes all if not specified
)
```

**Response**:
```python
CartResponse(
    success=True,
    cart_info=CartInfo(
        telegram_id=123456789,
        items=[
            CartItemInfo(
                product_id=1,
                product_name="Kubaneh",
                quantity=2,
                unit_price=25.0,
                total_price=50.0
            )
        ],
        total_amount=50.0
    )
)
```

### 4. Order Creation Use Case

**Purpose**: Create orders from cart items

**Request**:
```python
OrderCreationRequest(
    telegram_id=123456789,
    delivery_date="2024-01-15",  # Optional
    special_instructions="Extra spicy"  # Optional
)
```

**Response**:
```python
OrderCreationResponse(
    success=True,
    order_info=OrderInfo(
        order_id="ORD-20240101-001",
        customer_telegram_id=123456789,
        items=[...],
        total_amount=75.0,
        delivery_charge=10.0,
        final_amount=85.0,
        status="pending",
        estimated_delivery="2024-01-15T14:00:00Z"
    )
)
```

### 5. Order Status Management Use Case

**Purpose**: Update order status and send notifications

**Request**:
```python
OrderStatusUpdateRequest(
    order_id="ORD-20240101-001",
    new_status="confirmed",
    admin_notes="Order confirmed and in preparation"
)
```

**Valid Status Transitions**:
- `pending` → `confirmed`, `cancelled`
- `confirmed` → `preparing`, `cancelled`
- `preparing` → `ready`, `cancelled`
- `ready` → `completed`, `cancelled`
- `completed` → (terminal state)
- `cancelled` → (terminal state)

## 🤖 Telegram Bot Commands

### User Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Start the bot and register | `/start` |
| `/menu` | Browse product catalog | `/menu` |
| `/cart` | View current cart | `/cart` |
| `/orders` | View order history | `/orders` |
| `/help` | Get help information | `/help` |

### Admin Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/admin` | Access admin panel | `/admin` |
| `/orders_pending` | View pending orders | `/orders_pending` |
| `/analytics` | View business analytics | `/analytics` |

## 🔄 Callback Queries

### Product Selection
```
product_select_1  # Select product with ID 1
product_add_1_2   # Add 2 units of product 1 to cart
category_bread    # Browse bread category
```

### Cart Management
```
cart_remove_1     # Remove product 1 from cart
cart_clear        # Clear entire cart
cart_checkout     # Proceed to checkout
```

### Order Management
```
order_confirm_ORD-123  # Confirm order
order_cancel_ORD-123   # Cancel order
order_track_ORD-123    # Track order status
```

## 📈 Analytics and Monitoring

### Performance Metrics
- Total requests processed
- Average response time
- Slow request ratio
- Error rate
- Cache hit rate

### Business Analytics
- Total orders by period
- Revenue by category
- Customer growth
- Popular products
- Order completion rate

### Error Tracking
- Error categorization
- Error frequency
- User impact analysis
- Recovery success rate

## 🛠️ Development Tools

### Database Operations
```python
# Connection pooling
from src.infrastructure.database.database_optimizations import DatabaseConnectionManager

manager = DatabaseConnectionManager()
with manager.get_connection() as conn:
    # Database operations
    pass
```

### Caching
```python
# Cache operations
from src.infrastructure.cache.cache_manager import CacheManager

cache = CacheManager()
cache.set("key", "value", ttl=300)
value = cache.get("key")
```

### Error Handling
```python
# Custom error handling
from src.infrastructure.logging.error_handler import handle_errors, BusinessLogicError

@handle_errors(error_category=ErrorCategory.BUSINESS_LOGIC)
async def my_business_function():
    if error_condition:
        raise BusinessLogicError("Something went wrong")
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | - | Yes |
| `DATABASE_URL` | Database connection URL | `sqlite:///data/samna_salta.db` | No |
| `ENVIRONMENT` | Environment (dev/staging/prod) | `development` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `ADMIN_TELEGRAM_ID` | Admin Telegram ID | - | Yes |

### Business Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `DELIVERY_CHARGE` | Delivery charge amount | 10.0 ILS |
| `CURRENCY` | Currency code | ILS |
| `HILBEH_AVAILABLE_DAYS` | Days when Hilbeh is available | Thu,Fri,Sat |
| `HILBEH_AVAILABLE_HOURS` | Hours when Hilbeh is available | 09:00-18:00 |

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_comprehensive.py

# Run with verbose output
pytest -v
```

### Test Categories
- **Unit Tests**: Domain entities, value objects, use cases
- **Integration Tests**: Database, cache, external services
- **End-to-End Tests**: Complete user workflows
- **Performance Tests**: Load testing and benchmarks

## 🚀 Deployment

### Health Check Integration

For container orchestration platforms (Kubernetes, Docker Swarm):

```yaml
# Kubernetes health check example
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Scaling Considerations
- Database connection pooling handles concurrent users
- Cache layer reduces database load
- Rate limiting prevents abuse
- Horizontal scaling supported through stateless design

## 📋 Error Codes

| Code | Category | Description |
|------|----------|-------------|
| `CUSTOMER_NOT_FOUND` | Business | Customer not found in system |
| `PRODUCT_NOT_AVAILABLE` | Business | Product not available |
| `CART_EMPTY` | Business | Cart is empty |
| `ORDER_NOT_FOUND` | Business | Order not found |
| `INVALID_PHONE_NUMBER` | Validation | Phone number format invalid |
| `RATE_LIMIT_EXCEEDED` | Security | Rate limit exceeded |
| `DATABASE_ERROR` | System | Database operation failed |
| `CACHE_ERROR` | System | Cache operation failed |

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check DATABASE_URL environment variable
   - Verify database server is running
   - Check connection pool configuration

2. **Cache Performance Issues**
   - Monitor cache hit rates
   - Adjust TTL values
   - Check cache memory usage

3. **Rate Limiting False Positives**
   - Review rate limit thresholds
   - Check for legitimate high-frequency usage
   - Adjust limits per user type

4. **Order Processing Delays**
   - Check admin notification settings
   - Verify Telegram API connectivity
   - Review order queue processing

## 📞 Support

For technical support and questions:
- Review logs in `/logs` directory
- Check health endpoints for system status
- Monitor error rates and performance metrics
- Use admin panel for operational insights

## 🔄 API Versioning

Current API version: `v1`

Breaking changes will be introduced in new versions with proper migration guides and deprecation notices. 