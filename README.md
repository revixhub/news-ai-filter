# Marketing Digest Bot

🤖 **Автоматизированная система сбора, анализа и доставки персонализированного дайджеста новостей по стратегическому маркетингу**

## 📋 О проекте

Система ежедневно обрабатывает 100+ источников информации (Telegram каналы, веб-сайты, YouTube) и формирует краткую сводку с ключевыми инсайтами. AI анализирует важность контента и выделяет топ-5 новостей дня.

**Результат**: экономия 2-3 часов ежедневно на мониторинге новостей.

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- OpenAI API ключ или Anthropic API ключ
- Telegram API credentials (для сбора из каналов)

### Установка

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd marketing-digest-bot
```

2. **Создайте виртуальное окружение:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

4. **Настройте конфигурацию:**
```bash
# Скопируйте файл примера
copy env.example .env

# Отредактируйте .env файл с вашими API ключами
```

5. **Запустите бота:**
```bash
python main.py
```

## ⚙️ Конфигурация

### Обязательные переменные (.env)

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ALLOWED_USER_IDS=123456789,987654321

# AI Provider (openai или anthropic)
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
# или
ANTHROPIC_API_KEY=your_anthropic_api_key

# Telegram API (для сбора из каналов)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890
```

### Дополнительные настройки

```bash
# Расписание
DIGEST_TIME=10:00
TIMEZONE=Europe/Moscow
MAX_CONTENT_AGE_HOURS=24

# Лимиты
MAX_SOURCES_PER_TYPE=50
MAX_CONTENT_LENGTH=4000
CONCURRENT_SOURCES=10

# MCP Server (для YouTube, опционально)
MCP_SERVER_URL=your_mcp_server_url
MCP_API_KEY=your_mcp_api_key
```

## 📱 Команды бота

- `/start` - Активация бота и приветствие
- `/digest` - Получить дайджест прямо сейчас
- `/sources` - Показать список активных источников
- `/stats` - Статистика обработки за последние дни
- `/help` - Справка по командам

## 📊 Функциональность

### ✅ Реализовано (MVP)

- **Сбор данных**: Telegram каналы, RSS веб-сайтов
- **AI анализ**: Оценка важности по 4 критериям (0-100 баллов)
- **Категоризация**: 7 категорий маркетинговых новостей
- **Дайджест**: Топ-5 инсайтов + остальные по категориям
- **Автоматика**: Ежедневная отправка в 10:00
- **История**: Сохранение дайджестов в markdown файлы
- **Команды**: Ручной запрос, просмотр источников, статистика

### 🔄 В планах

- **YouTube интеграция**: Через MCP сервер для анализа видео
- **Расширенная аналитика**: Тренды, недельные отчеты
- **Больше источников**: Подкасты, закрытые каналы
- **Персонализация**: Настройка под интересы пользователя

## 🏗 Архитектура

```
📁 marketing-digest-bot/
├── 🗂 src/
│   ├── 📁 collectors/      # Сборщики данных
│   │   ├── telegram_collector.py
│   │   ├── web_collector.py
│   │   └── youtube_collector.py
│   ├── 📁 analyzers/       # AI анализ
│   │   └── ai_analyzer.py
│   ├── 📁 digest/          # Генерация дайджестов
│   │   └── digest_generator.py
│   ├── 📁 bot/            # Telegram бот
│   │   └── telegram_bot.py
│   ├── 📁 core/           # Основная логика
│   │   ├── digest_service.py
│   │   └── scheduler.py
│   ├── database.py        # SQLite менеджер
│   └── models.py         # Модели данных
├── 📁 data/              # База данных и дайджесты
├── 📁 logs/              # Логи работы
├── config.py             # Конфигурация
├── main.py              # Точка входа
└── requirements.txt     # Зависимости
```

## 📈 Метрики и KPI

### Производительность
- **Время обработки**: < 30 минут на полный цикл
- **Покрытие источников**: 95%+ ежедневно
- **Точность AI**: 80%+ релевантности
- **Время чтения дайджеста**: < 5 минут

### Качество
- **Топ-5 инсайтов**: Самые важные новости дня
- **Фильтрация**: Исключение дубликатов и рекламы
- **Категоризация**: Структурированная подача
- **Выводы**: AI генерирует практические инсайты

## 🛠 Разработка

### Структура проекта

- **Модульная архитектура**: Легко добавлять новые источники
- **Async/await**: Параллельная обработка источников
- **SQLite**: Локальная база данных
- **Structured logging**: JSON логи для мониторинга
- **Error handling**: Graceful degradation при ошибках

### Добавление нового источника

1. Создайте коллектор в `src/collectors/`
2. Наследуйтесь от `BaseCollector`
3. Реализуйте методы `collect()` и `check_availability()`
4. Добавьте в `DigestService._collect_from_all_sources()`

### Тестирование

```bash
# Тест команды дайджеста
python -c "
import asyncio
from src.core.digest_service import DigestService
service = DigestService()
print(asyncio.run(service.generate_daily_digest(123456789)))
"
```

## 📊 Мониторинг

### Логи

Логи сохраняются в `logs/digest.log` в JSON формате:

```json
{
  "event": "Digest generation completed",
  "user_id": 123456789,
  "processing_time": 45.2,
  "items_count": 23,
  "timestamp": "2024-01-15T10:00:00Z"
}
```

### Статистика

- **Через бота**: `/stats` - статистика за 7 дней
- **База данных**: таблица `metrics` с метриками
- **Файлы**: история дайджестов в `data/digests/`

## 🔧 Устранение неполадок

### Частые проблемы

1. **Бот не отвечает**
   - Проверьте `TELEGRAM_BOT_TOKEN`
   - Убедитесь что ваш `user_id` в `ALLOWED_USER_IDS`

2. **Нет новостей в дайджесте**
   - Проверьте доступность источников (`/sources`)
   - Возможно все новости оценены как неважные (< 30 баллов)

3. **Ошибки AI анализа**
   - Проверьте API ключи OpenAI/Anthropic
   - Убедитесь в наличии квот API

4. **Telegram каналы не читаются**
   - Настройте `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`
   - Авторизуйтесь в Telegram API

### Логи и отладка

```bash
# Просмотр логов
tail -f logs/digest.log

# Запуск с подробными логами
LOG_LEVEL=DEBUG python main.py

# Проверка базы данных
sqlite3 data/digest.db ".tables"
```

## 🚀 Deployment

### Локальный запуск

```bash
# Обычный запуск
python main.py

# В фоне (Linux/Mac)
nohup python main.py > logs/app.log 2>&1 &

# Windows Service
# Используйте Task Scheduler для автозапуска
```

### Системный сервис (Linux)

```bash
# Создайте файл /etc/systemd/system/digest-bot.service
sudo nano /etc/systemd/system/digest-bot.service
```

```ini
[Unit]
Description=Marketing Digest Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/marketing-digest-bot
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Активируйте и запустите
sudo systemctl enable digest-bot
sudo systemctl start digest-bot
sudo systemctl status digest-bot
```

## 📝 Лицензия

Личный проект. Для коммерческого использования обратитесь к автору.

## 🤝 Поддержка

- **Issues**: Сообщайте о проблемах через GitHub Issues
- **Вопросы**: Пишите автору через Telegram бота
- **Документация**: Подробности в `/docs` папке

---

⭐ **Если проект полезен, поставьте звезду!**

🚀 **Экономьте время на мониторинге новостей с AI** 