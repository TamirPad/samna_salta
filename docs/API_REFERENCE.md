# API Reference

Complete API documentation for the Samna Salta project.

## Table of Contents

- [Use Cases](#use-cases)
- [Value Objects](#value-objects)
- [Entities](#entities)
- [Repositories](#repositories)
- [Infrastructure Services](#infrastructure-services)
- [DTOs](#dtos)
- [Error Handling](#error-handling)

## Use Cases

### CustomerRegistrationUseCase

Handles customer registration and profile management.

```python
class CustomerRegistrationUseCase:
    async def register_customer(
        self, 
        telegram_id: TelegramId, 
        customer_name: CustomerName, 
        phone_number: PhoneNumber,
        delivery_address: Optional[DeliveryAddress] = None
    ) -> CustomerRegistrationResponse
```

**Parameters:**
- `telegram_id`: Unique Telegram user identifier
- `customer_name`: Customer's display name (2-100 characters)
- `phone_number`: International format phone number
- `delivery_address`: Optional delivery address

**Returns:**
- `CustomerRegistrationResponse` with success status and customer data

**Example:**
```python
response = await customer_use_case.register_customer(
    telegram_id=TelegramId(123456789),
    customer_name=CustomerName("Ahmed Al-Yemeni"),
    phone_number=PhoneNumber("+972501234567"),
    delivery_address=DeliveryAddress("123 Main St, Tel Aviv")
)

if response.success:
    print(f"Customer registered: {response.customer.name}")
else:
    print(f"Registration failed: {response.error_message}")
```

### CartManagementUseCase

Manages shopping cart operations.

```python
class CartManagementUseCase:
    async def add_to_cart(self, request: AddToCartRequest) -> CartOperationResponse
    async def get_cart(self, telegram_id: int) -> CartOperationResponse
    async def clear_cart(self, telegram_id: int) -> CartOperationResponse
```

#### add_to_cart

**Parameters:**
- `request.telegram_id`: Customer's Telegram ID
- `request.product_id`: Product to add
- `request.quantity`: Quantity to add (default: 1)
- `request.options`: Product customization options

**Example:**
```python
request = AddToCartRequest(
    telegram_id=123456789,
    product_id=1,
    quantity=2,
    options={
        "spice_level": "medium",
        "extra_sauce": "zhug"
    }
)

response = await cart_use_case.add_to_cart(request)

if response.success:
    print(f"Cart total: {response.cart_summary.total}")
```

### OrderCreationUseCase

Handles order creation and processing.

```python
class OrderCreationUseCase:
    async def create_order(self, order_data: Dict[str, Any]) -> OrderCreationResponse
```

**Parameters:**
- `order_data.customer_id`: Customer identifier
- `order_data.delivery_method`: "pickup" or "delivery"
- `order_data.delivery_address`: Required for delivery orders
- `order_data.special_instructions`: Optional instructions
- `order_data.payment_method`: Payment method

**Example:**
```python
order_data = {
    "customer_id": 1,
    "delivery_method": "pickup",
    "special_instructions": "Extra zhug sauce",
    "payment_method": "cash"
}

response = await order_use_case.create_order(order_data)

if response.success:
    print(f"Order created: {response.order.order_number}")
```

### OrderAnalyticsUseCase

Provides business analytics and reporting.

```python
class OrderAnalyticsUseCase:
    async def get_daily_summary(self, date: str) -> AnalyticsResponse
    async def get_weekly_trends(self, start_date: str) -> AnalyticsResponse
    async def get_popular_products(self) -> AnalyticsResponse
    async def get_customer_insights(self) -> AnalyticsResponse
    async def get_business_overview(self) -> AnalyticsResponse
```

**Example:**
```python
# Daily sales summary
daily = await analytics_use_case.get_daily_summary("2024-01-15")
print(f"Daily revenue: {daily.data['total_revenue']}")

# Popular products
popular = await analytics_use_case.get_popular_products()
for product in popular.data['products']:
    print(f"{product['name']}: {product['order_count']} orders")
```

### ProductCatalogUseCase

Manages product catalog operations.

```python
class ProductCatalogUseCase:
    async def get_products_by_category(self, request: ProductCatalogRequest) -> ProductCatalogResponse
    async def get_all_active_products(self) -> ProductCatalogResponse
    async def check_availability(self, request: ProductCatalogRequest) -> ProductCatalogResponse
```

**Example:**
```python
# Get main dishes
request = ProductCatalogRequest(category="main")
response = await catalog_use_case.get_products_by_category(request)

for product in response.products:
    print(f"{product.name}: {product.base_price} ILS")
```

## Value Objects

### Money

Represents monetary amounts with currency.

```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "ILS"
```

**Methods:**
```python
# Creation
money = Money(Decimal("25.50"), "ILS")
money = Money.from_float(25.50, "ILS")
money = Money.zero("ILS")

# Arithmetic operations
total = price + tax          # Addition
change = paid - total        # Subtraction
with_tax = price * 1.17      # Multiplication

# Comparison
is_expensive = price > Money(Decimal("30.00"))
is_equal = price == other_price

# Display
print(money.format_display())    # "25.50 ILS"
print(str(money))               # "25.50 ILS"
float_value = money.to_float()  # 25.50
```

### TelegramId

Represents Telegram user identifier.

```python
@dataclass(frozen=True)
class TelegramId:
    value: int
```

**Validation:**
- Must be positive integer
- Telegram IDs are typically 9-10 digits

**Example:**
```python
telegram_id = TelegramId(123456789)
print(int(telegram_id))  # 123456789
```

### PhoneNumber

Represents international phone numbers.

```python
@dataclass(frozen=True)
class PhoneNumber:
    value: str
```

**Validation:**
- Must start with "+"
- Must contain country code
- Automatically normalized

**Example:**
```python
# Valid formats
phone = PhoneNumber("+972501234567")
phone = PhoneNumber("+1-555-123-4567")

# Invalid formats (will raise ValueError)
# PhoneNumber("050-123-4567")  # Missing country code
# PhoneNumber("123456789")     # Missing + prefix
```

### CustomerName

Represents customer display name.

```python
@dataclass(frozen=True)
class CustomerName:
    value: str
```

**Validation:**
- 2-100 characters
- Automatically trimmed
- Non-empty after trimming

**Example:**
```python
name = CustomerName("  Ahmed Al-Yemeni  ")
print(name.value)  # "Ahmed Al-Yemeni" (trimmed)
```

### DeliveryAddress

Represents delivery address.

```python
@dataclass(frozen=True)
class DeliveryAddress:
    value: str
```

**Validation:**
- 5-200 characters
- Non-empty after trimming

### ProductId

Represents product identifier.

```python
@dataclass(frozen=True)
class ProductId:
    value: int
```

**Validation:**
- Must be positive integer

### OrderId

Represents order identifier.

```python
@dataclass(frozen=True)
class OrderId:
    value: int
```

**Validation:**
- Must be positive integer

### OrderNumber

Represents human-readable order number.

```python
@dataclass(frozen=True)
class OrderNumber:
    value: str
```

**Format:**
- "SS" + 14 digits (e.g., "SS20240115123456")

## Entities

### Customer

Domain entity representing a customer.

```python
@dataclass
class Customer:
    id: CustomerId
    telegram_id: TelegramId
    name: CustomerName
    phone_number: PhoneNumber
    delivery_address: Optional[DeliveryAddress] = None
```

**Methods:**
```python
# Check if customer requires delivery address
needs_address = customer.requires_delivery_address()

# Update customer information
customer.update_name(CustomerName("New Name"))
customer.update_phone(PhoneNumber("+972501234567"))
customer.set_delivery_address(DeliveryAddress("New Address"))
```

### Product

Domain entity representing a menu item.

```python
@dataclass  
class Product:
    id: ProductId
    name: ProductName
    description: str
    base_price: Money
    category: str
    is_active: bool = True
    options: Optional[Dict[str, Any]] = None
```

**Methods:**
```python
# Check availability
if product.is_available():
    # Product can be ordered
    pass

# Get price with options
total_price = product.calculate_price_with_options({"size": "large"})
```

## Repositories

### CustomerRepository

Repository interface for customer data access.

```python
class CustomerRepository(ABC):
    @abstractmethod
    async def find_by_telegram_id(self, telegram_id: TelegramId) -> Optional[Customer]
    
    @abstractmethod
    async def find_by_phone_number(self, phone_number: PhoneNumber) -> Optional[Customer]
    
    @abstractmethod
    async def save(self, customer: Customer) -> bool
    
    @abstractmethod
    async def delete(self, customer_id: CustomerId) -> bool
```

### ProductRepository

Repository interface for product data access.

```python
class ProductRepository(ABC):
    @abstractmethod
    async def find_by_id(self, product_id: ProductId) -> Optional[Product]
    
    @abstractmethod
    async def find_by_category(self, category: str) -> List[Product]
    
    @abstractmethod
    async def find_all_active(self) -> List[Product]
```

### CartRepository

Repository interface for cart data access.

```python
class CartRepository(ABC):
    @abstractmethod
    async def get_or_create_cart(self, telegram_id: TelegramId) -> Dict[str, Any]
    
    @abstractmethod
    async def add_item(self, telegram_id: TelegramId, product_id: ProductId, 
                      quantity: int, options: Dict[str, Any]) -> bool
    
    @abstractmethod
    async def clear_cart(self, telegram_id: TelegramId) -> bool
```

### OrderRepository

Repository interface for order data access.

```python
class OrderRepository(ABC):
    @abstractmethod
    async def create_order(self, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]
    
    @abstractmethod
    async def get_order_by_id(self, order_id: OrderId) -> Optional[Dict[str, Any]]
    
    @abstractmethod
    async def update_order_status(self, order_id: OrderId, status: str) -> bool
```

## Infrastructure Services

### CacheManager

High-performance caching service.

```python
class CacheManager:
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool
    def get(self, key: str) -> Optional[Any]
    def delete(self, key: str) -> bool
    def clear(self) -> bool
    def get_stats(self) -> Dict[str, Any]
```

**Example:**
```python
cache = CacheManager()

# Store data
cache.set("user:123", user_data, ttl=1800)  # 30 minutes

# Retrieve data
user_data = cache.get("user:123")

# Cache statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2f}%")
```

### RateLimiter

Rate limiting and DoS protection.

```python
class RateLimiter:
    def is_allowed(self, user_id: str, action: str = "default") -> bool
    def get_stats(self, user_id: str) -> Dict[str, Any]
    def reset_user_limits(self, user_id: str) -> None
```

**Example:**
```python
rate_limiter = RateLimiter()

# Check if action is allowed
if rate_limiter.is_allowed("user123", "order_create"):
    # Process order
    pass
else:
    # Rate limit exceeded
    return "Too many requests, please try again later"
```

### PerformanceMonitor

Real-time performance monitoring.

```python
class PerformanceMonitor:
    def start_monitoring(self, interval: float = 5.0) -> None
    def stop_monitoring(self) -> None
    def record_request(self, response_time: float, success: bool = True) -> None
    def get_performance_summary(self) -> Dict[str, Any]
```

**Example:**
```python
monitor = get_performance_monitor()
monitor.start_monitoring()

# Record request metrics
monitor.record_request(response_time=0.150, success=True)

# Get performance report
summary = monitor.get_performance_summary()
print(f"System health: {summary['system_health']}")
```

### SecurityValidator

Input validation and sanitization.

```python
class SecurityValidator:
    def validate_input(self, input_data: str) -> bool
    def sanitize_input(self, input_data: str) -> str
    def validate_phone_number(self, phone: str) -> bool
```

**Example:**
```python
validator = SecurityValidator()

# Validate user input
if validator.validate_input(user_input):
    safe_input = validator.sanitize_input(user_input)
    # Process safe input
else:
    # Reject malicious input
    return "Invalid input detected"
```

## DTOs

### AddToCartRequest

```python
@dataclass
class AddToCartRequest:
    telegram_id: int
    product_id: int
    quantity: int = 1
    options: Optional[Dict[str, Any]] = None
```

### CartOperationResponse

```python
@dataclass
class CartOperationResponse:
    success: bool
    cart_summary: Optional[CartSummary] = None
    error_message: Optional[str] = None
```

### ProductCatalogRequest

```python
@dataclass
class ProductCatalogRequest:
    category: Optional[str] = None
    search_term: Optional[str] = None
    product_id: Optional[int] = None
```

### CustomerRegistrationResponse

```python
@dataclass
class CustomerRegistrationResponse:
    success: bool
    customer: Optional[Customer] = None
    error_message: Optional[str] = None
```

## Error Handling

### Common Exceptions

```python
# Domain exceptions
class InvalidPhoneNumberError(ValueError):
    """Raised when phone number format is invalid"""

class InvalidMoneyAmountError(ValueError):
    """Raised when money amount is negative or invalid"""

class CustomerNotFoundError(Exception):
    """Raised when customer cannot be found"""

class ProductNotAvailableError(Exception):
    """Raised when product is not available for ordering"""

# Application exceptions  
class OrderCreationError(Exception):
    """Raised when order creation fails"""

class CartEmptyError(Exception):
    """Raised when trying to checkout empty cart"""

# Infrastructure exceptions
class DatabaseConnectionError(Exception):
    """Raised when database connection fails"""

class CacheError(Exception):
    """Raised when cache operations fail"""
```

### Error Response Format

All use case responses follow this pattern:

```python
{
    "success": bool,
    "data": Optional[Any],
    "error_message": Optional[str],
    "error_code": Optional[str]
}
```

**Example error handling:**
```python
try:
    response = await use_case.some_operation()
    if not response.success:
        logger.error(f"Operation failed: {response.error_message}")
        return {"error": response.error_message}
    
    return {"data": response.data}
    
except CustomerNotFoundError:
    return {"error": "Customer not found"}
except ProductNotAvailableError as e:
    return {"error": f"Product unavailable: {e}"}
except Exception as e:
    logger.exception("Unexpected error")
    return {"error": "Internal server error"}
```

## Usage Patterns

### Async/Await Pattern

All use cases are async and should be awaited:

```python
# ✅ Correct
result = await use_case.operation()

# ❌ Incorrect
result = use_case.operation()  # Returns coroutine, not result
```

### Error Handling Pattern

Always check response success before using data:

```python
# ✅ Correct
response = await use_case.operation()
if response.success:
    process_data(response.data)
else:
    handle_error(response.error_message)

# ❌ Incorrect
response = await use_case.operation()
process_data(response.data)  # May be None if operation failed
```

### Value Object Creation

Always handle validation errors:

```python
# ✅ Correct
try:
    phone = PhoneNumber(user_input)
except ValueError as e:
    return f"Invalid phone number: {e}"

# ❌ Incorrect
phone = PhoneNumber(user_input)  # May raise unhandled exception
```

## Performance Considerations

### Database Queries

- Use async repository methods
- Implement proper error handling
- Consider query optimization for large datasets

### Caching

- Cache frequently accessed data
- Set appropriate TTL values
- Handle cache misses gracefully

### Memory Usage

- Use generators for large datasets
- Clear references to large objects
- Monitor memory usage in production

### Rate Limiting

- Implement per-user rate limits
- Consider different limits for different operations
- Provide clear error messages when limits exceeded

## Testing

### Unit Testing

```python
@pytest.mark.asyncio
async def test_customer_registration():
    # Arrange
    customer_repo = AsyncMock()
    use_case = CustomerRegistrationUseCase(customer_repo)
    
    # Act
    response = await use_case.register_customer(
        TelegramId(123456789),
        CustomerName("Test User"),
        PhoneNumber("+972501234567")
    )
    
    # Assert
    assert response.success
    assert response.customer.name.value == "Test User"
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_full_order_workflow():
    # Test complete customer journey from registration to order
    # Uses real repository implementations with test database
    pass
```

For more examples, see the [test suite](../tests/) directory. 