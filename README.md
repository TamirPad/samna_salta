# Samna Salta - Professional Telegram Food Ordering Bot

A comprehensive, production-ready Telegram bot for traditional Yemenite food ordering. Built with enterprise-grade Clean Architecture for reliability, scalability, and ease of maintenance.

## 🎯 Business Value

**Streamline Your Food Business Operations**
- **Automated Order Management**: Eliminate manual order taking and reduce errors
- **Customer Database**: Automatic customer tracking with order history
- **Real-time Notifications**: Instant order alerts to your phone
- **Professional Experience**: Polished, user-friendly interface for customers
- **24/7 Availability**: Customers can browse and order anytime
- **Delivery Management**: Integrated pickup/delivery options with address collection

## ✨ Key Features

### 🛒 **Customer Experience**
- **Smart Onboarding**: Automatic customer registration with returning customer recognition
- **Interactive Menu**: Multi-level product browsing with customization options
- **Shopping Cart**: Add/remove items, modify quantities, clear cart functionality
- **Delivery Options**: Choose between pickup (free) or delivery (+5₪) per order
- **Address Management**: Collect and update delivery addresses as needed
- **Order Preview**: Review delivery method, address, and total before confirming
- **Multi-language Support**: Hebrew (default) and English translations

### 👑 **Business Management**
- **Instant Order Alerts**: Real-time notifications to admin with full order details
- **Customer Database**: Automatic tracking of customer information and preferences
- **Order Analytics**: Track popular products and business performance
- **Comprehensive Logging**: Full audit trail for debugging and monitoring
- **Business Rules**: Special availability handling (e.g., Hilbeh: Wed-Fri only)

### 🍞 **Product Catalog**
- **Kubaneh** (Traditional Yemenite Bread) - 25₪
  - Classic, Seeded, Herb, Aromatic varieties
- **Samneh** (Clarified Butter) - 15₪
  - Smoked or Regular
- **Red Bisbas** (Spicy Sauce) - 12₪
  - Small or Large containers
- **Hilbeh** (Fenugreek Dip) - 18₪
  - Available Wednesday-Friday only
- **Hawaij Spices** - 8₪ each
  - Soup and Coffee varieties
- **White Coffee** (Traditional Drink) - 10₪

## 🏗️ Technical Architecture

Built with **Clean Architecture** principles ensuring:
- **Maintainability**: Easy to modify and extend
- **Testability**: Comprehensive test suite included
- **Reliability**: Robust error handling and logging
- **Scalability**: Ready for business growth

```
samna_salta/
├── main.py              # 🎯 Unified entry point (polling + webhook)
├── render.yaml          # 🚀 Render deployment config
├── render-build.sh      # 🔨 Build script
├── pyproject.toml       # 📦 Dependencies (Poetry)
├── src/                 # 📁 Source code
│   ├── handlers/        # Telegram bot handlers
│   ├── services/        # Business logic services
│   ├── db/             # Database models and operations
│   ├── utils/          # Utilities and helpers
│   └── config.py       # Configuration management
├── scripts/            # 🔧 Utilities and scripts
├── tests/              # 🧪 Test suite
├── docs/               # 📚 Documentation
├── data/               # 📊 Database storage
└── logs/               # 📝 Application logs
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Poetry (will be installed automatically if missing)
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))

### Installation

**Option 1: Automatic Setup (Recommended)**
```bash
git clone <your-repository>
cd samna_salta
./setup.sh
```

**Option 2: Manual Setup**
```bash
git clone <your-repository>
cd samna_salta

# Install Poetry if not installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Create environment file
cp env.example .env
# Edit .env with your bot token and admin chat ID

# Create necessary directories
mkdir -p data logs
```

### Configuration

Edit the `.env` file with your settings:
```env
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_CHAT_ID=your_admin_chat_id_here
```

### Running the Bot

**Local Development (Polling Mode):**
```bash
python main.py
```

**Production Deployment (Webhook Mode):**
```bash
# Set production environment variables
export WEBHOOK_URL=https://your-app.onrender.com
export PORT=8000
python main.py
```

## 🚀 Quick Reference

### Development Commands
```bash
# Run bot locally
python main.py

# Run tests
poetry run pytest

# Format code
poetry run black .

# Lint code
poetry run flake8

# Type checking
poetry run mypy src
```

### Deployment Commands
```bash
# Set webhook for production
python scripts/setup_webhook.py set

# Remove webhook (switch to polling)
python scripts/setup_webhook.py remove

# Check bot status
curl https://your-app.onrender.com/health
```

## 🚀 Deployment to Render

### Quick Deployment
1. **Fork** this repository to your GitHub account
2. **Connect** to [Render.com](https://render.com) and create a Web Service
3. **Configure** the service:
   - Build Command: `./render-build.sh`
   - Start Command: `python main.py`
   - Health Check Path: `/health`
4. **Set Environment Variables**:
   - `BOT_TOKEN`: Your bot token from @BotFather
   - `ADMIN_CHAT_ID`: Your Telegram chat ID
   - `WEBHOOK_MODE`: `true`
5. **Deploy** - Render automatically handles the rest!

### Detailed Deployment Guide
For comprehensive deployment instructions, troubleshooting, and optimization tips, see [DEPLOYMENT.md](DEPLOYMENT.md).

### Post-Deployment
After successful deployment:
1. Test the bot by sending `/start` to your bot
2. Check the health endpoint: `https://your-app.onrender.com/health`
3. Monitor logs in Render Dashboard for any issues

## ⚙️ Configuration

### Required Environment Variables
```env
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_CHAT_ID=your_admin_chat_id_here
```

### Optional Configuration
```env
DATABASE_URL=sqlite:///data/samna_salta.db
LOG_LEVEL=INFO
ENVIRONMENT=production
DELIVERY_CHARGE=5.00
CURRENCY=ILS
DEFAULT_LANGUAGE=he
HILBEH_AVAILABLE_DAYS=["wednesday", "thursday", "friday"]
HILBEH_AVAILABLE_HOURS=09:00-18:00
```

### Business Customization
- **Product Catalog**: Modify prices and descriptions in the database
- **Delivery Charges**: Adjust delivery fees in configuration
- **Business Hours**: Set special availability for seasonal products
- **Languages**: Customize Hebrew/English translations

## 📱 How Customers Use the Bot

1. **Start**: Customer sends `/start` to your bot
2. **Registration**: Bot collects name, phone, and delivery preferences
3. **Browse Menu**: Interactive product categories and options
4. **Add to Cart**: Select products with customization options
5. **Review Cart**: View items, change delivery method, or clear cart
6. **Confirm Order**: Review delivery details and confirm
7. **Notification**: You receive instant order notification with all details

## 👑 Admin Features

### Commands
- View pending and active orders
- Access business analytics
- Monitor system health
- Manage customer database

### Automatic Notifications
You'll receive instant notifications for:
- New orders with full customer and item details
- Order status updates
- System alerts and errors

## 🧪 Quality Assurance

The application includes comprehensive testing:

### Test Suite
- **Unit Tests**: Core business logic validation
- **Integration Tests**: Database and service integration
- **Domain Tests**: Business rule verification
- **Infrastructure Tests**: External service reliability

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src

# Run specific test categories
poetry run pytest tests/unit/
poetry run pytest tests/integration/
```

## 📊 Monitoring & Logging

### Log Files
- `logs/app.log`: General application activity
- `logs/errors.log`: Error tracking and debugging
- `logs/performance.log`: Performance metrics
- `logs/security.log`: Security events

### Health Monitoring
- Automatic error detection and logging
- Performance metrics tracking
- Database connection monitoring
- Telegram API status monitoring

### Health Check Endpoints
```bash
# Check if bot is running
curl https://your-app.onrender.com/health

# Check root endpoint
curl https://your-app.onrender.com/
```

## 🔧 Maintenance

### Regular Tasks
- Monitor log files for errors
- Review order analytics for business insights
- Update product catalog as needed
- Backup database periodically

### Updates
The codebase is designed for easy updates:
- Modular architecture allows feature additions
- Database migrations handle schema changes
- Configuration-driven business rules
- Comprehensive test suite ensures stability

## 📞 Support & Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check bot token and internet connection
   - Verify webhook is set correctly
   - Check Render logs for errors

2. **Orders not received**
   - Verify admin chat ID is correct
   - Check notification service logs

3. **Database errors**
   - Check file permissions and disk space
   - Verify database URL configuration

4. **Webhook conflicts**
   - If you see "terminated by other getUpdates request" errors:
     - Ensure only one bot instance is running
     - Use webhook mode for production (Render deployment)
     - Run `python scripts/setup_webhook.py remove` to clear any existing webhooks
     - Then run `python scripts/setup_webhook.py set` to set the correct webhook

### Logs Analysis
- Check `logs/errors.log` for specific error messages
- Review `logs/app.log` for general activity
- Monitor `logs/performance.log` for slow operations

### Debugging Commands
```bash
# Check webhook status
python scripts/setup_webhook.py set

# Test bot locally
python main.py

# Check environment variables
python -c "from src.config import get_config; print(get_config())"
```

## 🔒 Security Features

- Input validation and sanitization
- Rate limiting for API calls
- Secure environment variable handling
- Comprehensive error handling
- Data privacy compliance

## 📈 Business Analytics

Track your business performance:
- Daily/weekly order volumes
- Popular product analysis
- Customer behavior insights
- Revenue tracking
- Delivery vs pickup preferences

## 🎨 Customization Options

### Visual Customization
- Modify Hebrew/English translations in `locales/`
- Adjust message formatting and emojis
- Customize order confirmation templates

### Business Logic
- Add new product categories
- Implement seasonal availability
- Adjust pricing and delivery charges
- Create customer loyalty features

## 📋 Production Checklist

✅ **Deployment Ready**
- Clean codebase with no development artifacts
- Comprehensive error handling
- Production logging configuration
- Database optimization
- Security best practices implemented

✅ **Business Ready**
- Complete product catalog
- Customer onboarding flow
- Order management system
- Admin notification system
- Analytics and reporting

✅ **Maintenance Ready**
- Comprehensive documentation
- Test suite for quality assurance
- Monitoring and logging
- Easy configuration management
- Scalable architecture

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
poetry install --with dev

# Install pre-commit hooks
poetry run pre-commit install

# Run tests before committing
poetry run pytest tests/ --cov=src
```

## 📄 License

MIT License - Perfect for commercial use.

---

**Professional Telegram Bot Solution**
*Delivered with enterprise-grade quality and comprehensive support documentation*
