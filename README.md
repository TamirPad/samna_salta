# Samna Salta - Telegram Ordering Bot

A comprehensive Telegram bot for traditional Yemenite food ordering, designed for small hometown businesses. Built with Clean Architecture principles for reliability and maintainability.

## Features

### Customer Experience
- **Smart Onboarding**: Automated customer registration with returning customer recognition
- **Flexible Delivery**: Self-pickup or delivery options with address collection
- **Interactive Menu**: Multi-level navigation with product categories and customization
- **Shopping Cart**: Add items, modify quantities, and review orders
- **Order Confirmation**: Complete order review before submission
- **Business Hours**: Automatic handling of special availability (Hilbeh: Wed-Fri only)

### Business Management
- **Order Notifications**: Real-time order alerts to admin
- **Customer Database**: Automatic customer tracking and history
- **Product Management**: Easy product catalog management
- **Analytics**: Order tracking and popular product insights
- **Logging**: Comprehensive logging for debugging and monitoring

## Product Catalog

- **Kubaneh** (Traditional Yemenite Bread): Classic/Seeded/Herb/Aromatic with butter options
- **Samneh** (Clarified Butter): Smoked/Regular in Small/Large sizes
- **Red Bisbas** (Fenugreek Paste): Small/Large containers
- **Hawaij Spices**: Soup and Coffee varieties
- **White Coffee**: Traditional preparation
- **Hilbeh** (Fenugreek Dip): Available Wednesday-Friday only

## Architecture

Built with Clean Architecture principles for maintainability and testability:

```
samna_salta/
├── src/
│   ├── domain/                    # Business logic core
│   │   ├── entities/              # Core business entities
│   │   ├── repositories/          # Data access interfaces
│   │   └── value_objects/         # Value objects and constraints
│   ├── application/               # Application layer
│   │   ├── dtos/                  # Data transfer objects
│   │   └── use_cases/             # Business use cases
│   ├── infrastructure/            # External concerns
│   │   ├── database/              # Database operations
│   │   ├── logging/               # Logging configuration
│   │   ├── configuration/         # App configuration
│   │   ├── security/              # Security measures
│   │   └── container/             # Dependency injection
│   └── presentation/              # User interface
│       └── telegram_bot/          # Telegram bot interface
├── data/                          # Database storage
├── logs/                          # Application logs
├── tests/                         # Test suite
├── main.py                        # Application entry point
├── render.yaml                    # Render deployment config
└── requirements.txt               # Python dependencies
```

## Quick Start

### Prerequisites
- Python 3.8+ (3.11 recommended for Render free tier)
- Telegram Bot Token (get from @BotFather)
- Admin Telegram Chat ID

### Local Development

1. **Setup**
   ```bash
   git clone <repository-url>
   cd samna_salta
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp env.example .env
   # Edit .env with your bot token and admin chat ID
   ```

3. **Run**
   ```bash
   python main.py
   ```

### Production Deployment (Render)

Ready for deployment on Render free tier:

1. **Fork/Clone** this repository
2. **Connect** to Render and create a new Web Service
3. **Configure** environment variables:
   - `BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_CHAT_ID`: Your admin chat ID
4. **Deploy** - Render will automatically use `render.yaml` configuration

## Configuration

### Environment Variables
```env
# Required
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_CHAT_ID=your_admin_chat_id_here

# Optional (defaults provided)
DATABASE_URL=sqlite:///data/samna_salta.db
LOG_LEVEL=INFO
ENVIRONMENT=production
DELIVERY_CHARGE=5.00
CURRENCY=ILS
HILBEH_AVAILABLE_DAYS=wednesday,thursday,friday
HILBEH_AVAILABLE_HOURS=09:00-18:00
```

### Business Customization
- Modify product catalog in database initialization
- Adjust delivery charges and currency
- Update business hours for special products
- Customize order notification format

## Commands

### Customer Commands
- `/start` - Begin ordering process
- `/menu` - View product catalog
- `/cart` - View current cart
- `/help` - Get assistance

### Admin Commands
- `/orders` - View recent orders
- `/analytics` - View order statistics
- `/products` - Manage product catalog

## Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src

# Run specific test category
python -m pytest tests/test_use_cases/
```

## Monitoring

The application includes comprehensive logging:
- **Application logs**: `logs/samna_salta.log`
- **Error logs**: `logs/errors.log`
- **Performance logs**: `logs/performance.log`
- **Security logs**: `logs/security.log`

## Support

For small business support:
- Check logs for debugging
- Review order notifications
- Monitor customer interactions
- Track popular products

## License

MIT License - Perfect for small business use.

---

*Built with ❤️ for hometown businesses* 