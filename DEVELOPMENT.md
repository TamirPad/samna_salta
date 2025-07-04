# Development Guide

## Project Status

The Samna Salta Telegram Bot has been initialized with a comprehensive project structure. Here's what's been set up and what needs to be implemented next.

## ✅ Completed

### Project Structure
- Modular architecture with separate packages for bot, database, services, and utils
- Configuration management with environment variables
- Database models for all entities (customers, orders, products, carts)
- Basic onboarding flow for customer registration
- Menu keyboard system with product categories
- Logging and utility functions
- Test structure

### Core Components
- **Database**: SQLAlchemy models with SQLite support (PostgreSQL ready)
- **Configuration**: Pydantic-based settings management
- **Onboarding**: Complete customer registration flow
- **Keyboards**: Menu navigation system
- **Utilities**: Phone validation, price formatting, business hours logic

## 🚧 Next Steps

### 1. Complete Menu Handlers
**File**: `src/bot/handlers/menu.py`
- Implement product selection logic
- Add to cart functionality
- Product information display
- Handle multi-level menu navigation

### 2. Complete Cart Handlers
**File**: `src/bot/handlers/cart.py`
- Cart management (add/remove items)
- Cart display with totals
- Order confirmation flow
- Send order to admin

### 3. Complete Admin Handlers
**File**: `src/bot/handlers/admin.py`
- Admin authentication
- Product management (add/edit/delete)
- Order management
- Customer management

### 4. Implement Services
**Files**: `src/services/`
- `cart_service.py`: Cart business logic
- `menu_service.py`: Menu and product logic
- `order_service.py`: Order processing and notifications

### 5. Add Product Images and Descriptions
**File**: `data/products.json`
- Product images
- Detailed descriptions
- Pricing information

## 🔧 Development Setup

### 1. Environment Setup
```bash
# Copy environment file
cp env.example .env

# Edit .env with your bot token and admin chat ID
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_CHAT_ID=your_admin_chat_id_here
```

### 2. Database Initialization
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from src.database.operations import init_db; init_db()"
```

### 3. Run Tests
```bash
python -m pytest tests/
```

## 📋 Implementation Checklist

### Menu System
- [ ] Product category navigation
- [ ] Product option selection (Kubaneh types, Samneh options, etc.)
- [ ] Product information display with images
- [ ] Add to cart functionality
- [ ] Back navigation at all levels

### Cart System
- [ ] Add items to cart
- [ ] View cart contents
- [ ] Modify quantities
- [ ] Remove items
- [ ] Calculate totals
- [ ] Delivery charge calculation

### Order System
- [ ] Order confirmation
- [ ] Customer details review
- [ ] Admin notification
- [ ] Order status tracking
- [ ] Order history

### Admin Features
- [ ] Admin authentication
- [ ] Product management
- [ ] Order management
- [ ] Customer management
- [ ] Sales reports

### Business Logic
- [ ] Hilbeh availability (Wed-Fri only)
- [ ] Delivery charge logic
- [ ] Returning customer recognition
- [ ] Order number generation

## 🧪 Testing Strategy

### Unit Tests
- Database operations
- Utility functions
- Business logic

### Integration Tests
- Bot conversation flows
- Database interactions
- Admin operations

### Manual Testing
- Complete ordering flow
- Admin interface
- Error handling

## 📝 Code Style

- Use Black for code formatting
- Use isort for import sorting
- Follow PEP 8 guidelines
- Add type hints to all functions
- Write docstrings for all classes and functions

## 🚀 Deployment

### Local Development
```bash
python main.py
```

### Production
- Use PostgreSQL instead of SQLite
- Set up proper logging
- Configure webhook or polling
- Set up monitoring and alerts

## 📞 Support

For questions or issues during development:
1. Check the README.md for setup instructions
2. Review the database models in `src/database/models.py`
3. Test the onboarding flow with `/start` command
4. Check logs for debugging information 