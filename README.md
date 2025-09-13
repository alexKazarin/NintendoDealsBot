# Nintendo Deals Bot

Telegram bot for tracking Nintendo Switch game deals. Get notifications about price drops on your favorite games!

## 🚀 Features

- ✅ Search games by title
- ✅ Add games to personal wishlist
- ✅ Real-time price tracking
- ✅ Personal discount notifications
- ✅ Set price thresholds for notifications
- ✅ Support for different regions (US, EU, JP)
- ✅ Premium subscription (up to 100 games)
- ✅ Price history for each game

## 📋 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start using the bot |
| `/help` | Show help |
| `/add <game>` | Add game to wishlist |
| `/list` | Show your wishlist |
| `/remove <number>` | Remove game from wishlist |
| `/setthreshold <price>` | Set price threshold |
| `/region <region>` | Change region (us/eu/jp) |
| `/subscribe` | Get premium subscription |
| `/donate` | Support the project |

## 🎮 User Interface

The bot features a modern **inline keyboard interface** with buttons for easy navigation:

- **Main Menu**: Access all functions through interactive buttons
- **Wishlist Management**: Add/remove games with one click
- **Price Alerts**: Set custom price thresholds
- **Region Settings**: Switch between US/EU/JP regions
- **Premium Features**: Upgrade to premium for extended limits
- **Rich Formatting**: All messages use HTML formatting with bold headers and structured layout

## 🛠 Installation and Setup

### Local Development Setup

#### 1. Clone the repository
```bash
git clone <repository-url>
cd NintendoDealsBot
```

#### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure environment variables

Create a `.env` file and add your Telegram bot token:

```env
BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=sqlite:///./nintendo_deals.db
DEFAULT_REGION=us
```

#### 5. Create Telegram Bot

1. Open [@BotFather](https://t.me/botfather) in Telegram
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token and paste it in `.env`

#### 6. Initialize database
```bash
python init_db.py
```

#### 7. Run the bot locally
```bash
python main.py
```

#### 8. Testing
```bash
python test_bot.py
```

### Quick Local Start (after setup)
```bash
source venv/bin/activate
python main.py
```

## 🗄 Project Structure

```
NintendoDealsBot/
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── .env                    # Environment variables
├── README.md              # Documentation
├── blueprint.md           # Project specification
├── src/                   # Main code
│   ├── __init__.py
│   ├── models/            # Database models
│   │   ├── __init__.py
│   │   ├── database.py    # Database setup
│   │   └── models.py      # SQLAlchemy models
│   ├── providers/         # Data providers
│   │   ├── __init__.py
│   │   ├── base_provider.py
│   │   └── deku_deals_provider.py
│   └── bot/               # Telegram bot code
│       ├── __init__.py
│       ├── bot.py         # Main bot logic
│       └── scheduler.py   # Price check scheduler
```

## 🗃 Database Schema

### users
- `id` - Primary key
- `telegram_id` - User's Telegram ID
- `telegram_username` - User's Telegram username
- `region` - User's region
- `is_premium` - Premium subscription status

### games
- `id` - Primary key
- `source_id` - Game ID in source (DekuDeals)
- `title` - Game title
- `platform` - Platform
- `last_price_cents` - Last known price
- `last_checked` - Last check time

### user_wishlist
- `id` - Primary key
- `user_id` - User ID
- `game_id` - Game ID
- `desired_price_cents` - Desired price
- `last_notified_price_cents` - Last notification price

### price_history
- `id` - Primary key
- `game_id` - Game ID
- `price_cents` - Price
- `currency` - Currency
- `recorded_at` - Recording time

### notifications
- `id` - Primary key
- `user_id` - User ID
- `game_id` - Game ID
- `price_cents` - Price at notification time
- `sent_at` - Sent time
- `rule` - Notification rule

## 🔧 Production Configuration

### Environment Variables
```env
BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:password@localhost/nintendo_deals
REDIS_URL=redis://localhost:6379  # For caching states
LOG_LEVEL=INFO
```

### Using PostgreSQL
1. Install PostgreSQL
2. Create a database
3. Update `DATABASE_URL` in `.env`
4. Modify `models/database.py` to use PostgreSQL

### Deploy to Server
Recommended platforms:
- **Railway** - Simple deploy from GitHub
- **Render** - Free tier for small projects
- **Heroku** - Classic solution
- **VPS** - For full control

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## 📞 Support

If you have questions or issues:
1. Check the [Issues](../../issues) section
2. Create a new issue with detailed description
3. Contact the developer

## 🙏 Acknowledgments

- [aiogram](https://github.com/aiogram/aiogram) - Telegram bot framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [DekuDeals](https://www.dekudeals.com/) - Deal data source
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing

---

⭐ If you find this project useful, please star it on GitHub!
