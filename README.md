# Samna Salta - Telegram Ordering Bot

A comprehensive Telegram bot for food ordering, designed for small businesses in the food sector. The bot guides customers through a complete ordering process from user onboarding to order confirmation.

## Features

### Customer Features
- **User Onboarding**: Collect customer details (name, phone) with returning customer recognition
- **Delivery Options**: Self-pickup or delivery with address collection
- **Dynamic Menu System**: Multi-level menu navigation with product categories and options
- **Shopping Cart**: Add items, view cart, and manage quantities
- **Order Confirmation**: Review and confirm order details before submission

### Admin Features
- **Order Notifications**: Receive detailed order summaries
- **Admin Interface**: Manage products and categories via Telegram commands
- **Customer Database**: Track returning customers and order history

## Product Categories

- **Kubaneh**: Classic/Seeded/Herb/Aromatic with Olive oil/Samneh options
- **Samneh**: Smoked/Not smoked with Small/Large sizes
- **Red Bisbas**: Small/Large sizes
- **Hawaij soup spice**: Direct add to cart
- **Hawaij coffee spice**: Direct add to cart
- **White coffee**: Direct add to cart
- **Hilbeh**: Available Wednesday-Friday only

## Tech Stack

- **Backend**: Python 3.8+
- **Telegram Bot API**: python-telegram-bot
- **Database**: SQLite (with PostgreSQL migration path)
- **Configuration**: Environment variables
- **Logging**: Structured logging

## Project Structure

```
samna_salta/
├── src/
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── cart.py
│   │   │   ├── menu.py
│   │   │   └── onboarding.py
│   │   ├── keyboards/
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── cart.py
│   │   │   └── menu.py
│   │   └── states.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── operations.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cart_service.py
│   │   ├── menu_service.py
│   │   └── order_service.py
│   └── utils/
│       ├── __init__.py
│       ├── config.py
│       └── helpers.py
├── config/
│   └── config.yaml
├── data/
│   └── products.json
├── tests/
│   └── __init__.py
├── requirements.txt
├── main.py
├── .env.example
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Telegram Bot Token (from @BotFather)
- Admin Telegram Chat ID

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
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
   # Edit .env with your bot token and admin chat ID
   ```

5. **Initialize database**
   ```bash
   python -c "from src.database.operations import init_db; init_db()"
   ```

6. **Run the bot**
   ```bash
   python main.py
   ```

## Configuration

Create a `.env` file with the following variables:
```
BOT_TOKEN=your_telegram_bot_token
ADMIN_CHAT_ID=your_admin_chat_id
DATABASE_URL=sqlite:///data/orders.db
LOG_LEVEL=INFO
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Formatting
```bash
black src/ tests/
isort src/ tests/
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 