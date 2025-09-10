# Nintendo Deals Bot

Telegram-бот для отслеживания скидок на игры Nintendo Switch. Получайте уведомления о снижении цен на ваши любимые игры!

## 🚀 Возможности

- ✅ Поиск игр по названию
- ✅ Добавление игр в персональный виш-лист
- ✅ Отслеживание цен в реальном времени
- ✅ Персональные уведомления о скидках
- ✅ Установка порогов цен для уведомлений
- ✅ Поддержка разных регионов (US, EU, JP)
- ✅ Премиум подписка (до 100 игр)
- ✅ История цен для каждой игры

## 📋 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начать работу с ботом |
| `/help` | Показать справку |
| `/add <игра>` | Добавить игру в виш-лист |
| `/list` | Показать ваш виш-лист |
| `/remove <номер>` | Удалить игру из виш-листа |
| `/setthreshold <цена>` | Установить порог цены |
| `/region <регион>` | Изменить регион (us/eu/jp) |
| `/subscribe` | Оформить премиум подписку |
| `/donate` | Поддержать проект |

## 🛠 Установка и запуск

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd NintendoDealsBot
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Создайте файл `.env` и добавьте ваш токен Telegram бота:

```env
BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=sqlite:///./nintendo_deals.db
DEFAULT_REGION=us
```

### 4. Создание Telegram бота

1. Откройте [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте токен и вставьте в `.env`

### 5. Инициализация базы данных
```bash
python init_db.py
```

### 6. Запуск бота
```bash
python main.py
```

### 7. Тестирование
```bash
python test_bot.py
```

## 🗄 Структура проекта

```
NintendoDealsBot/
├── main.py                 # Точка входа
├── requirements.txt        # Зависимости
├── .env                    # Переменные окружения
├── README.md              # Документация
├── blueprint.md           # Спецификация проекта
├── src/                   # Основной код
│   ├── __init__.py
│   ├── models/            # Модели базы данных
│   │   ├── __init__.py
│   │   ├── database.py    # Настройка БД
│   │   └── models.py      # SQLAlchemy модели
│   ├── providers/         # Провайдеры данных
│   │   ├── __init__.py
│   │   ├── base_provider.py
│   │   └── deku_deals_provider.py
│   └── bot/               # Код Telegram бота
│       ├── __init__.py
│       ├── bot.py         # Основная логика бота
│       └── scheduler.py   # Планировщик проверок цен
```

## 🗃 Схема базы данных

### users
- `id` - Первичный ключ
- `telegram_id` - ID пользователя в Telegram
- `telegram_username` - Username в Telegram
- `region` - Регион пользователя
- `is_premium` - Статус премиум подписки

### games
- `id` - Первичный ключ
- `source_id` - ID игры в источнике (DekuDeals)
- `title` - Название игры
- `platform` - Платформа
- `last_price_cents` - Последняя известная цена
- `last_checked` - Время последней проверки

### user_wishlist
- `id` - Первичный ключ
- `user_id` - ID пользователя
- `game_id` - ID игры
- `desired_price_cents` - Желаемая цена
- `last_notified_price_cents` - Последняя цена уведомления

### price_history
- `id` - Первичный ключ
- `game_id` - ID игры
- `price_cents` - Цена
- `currency` - Валюта
- `recorded_at` - Время записи

### notifications
- `id` - Первичный ключ
- `user_id` - ID пользователя
- `game_id` - ID игры
- `price_cents` - Цена на момент уведомления
- `sent_at` - Время отправки
- `rule` - Правило уведомления

## 🔧 Настройка для продакшена

### Переменные окружения
```env
BOT_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:password@localhost/nintendo_deals
REDIS_URL=redis://localhost:6379  # Для кэширования состояний
LOG_LEVEL=INFO
```

### Использование PostgreSQL
1. Установите PostgreSQL
2. Создайте базу данных
3. Обновите `DATABASE_URL` в `.env`
4. Измените `models/database.py` для использования PostgreSQL

### Деплой на сервер
Рекомендуемые платформы:
- **Railway** - Простой деплой из GitHub
- **Render** - Бесплатный tier для небольших проектов
- **Heroku** - Классическое решение
- **VPS** - Для полного контроля

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## 📞 Поддержка

Если у вас возникли вопросы или проблемы:
1. Проверьте раздел [Issues](../../issues)
2. Создайте новый issue с подробным описанием
3. Свяжитесь с разработчиком

## 🙏 Благодарности

- [aiogram](https://github.com/aiogram/aiogram) - Фреймворк для Telegram ботов
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM для работы с БД
- [DekuDeals](https://www.dekudeals.com/) - Источник данных о скидках
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) - Парсинг HTML

---

⭐ Если проект оказался полезным, поставьте звезду на GitHub!
