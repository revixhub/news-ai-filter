import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
SOURCES_FILE = DATA_DIR / "sources.json"

# Create directories
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = [int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()]

# AI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4")

# Telegram API (for channel reading)
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")

# Schedule
DIGEST_TIME = os.getenv("DIGEST_TIME", "10:00")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
MAX_CONTENT_AGE_HOURS = int(os.getenv("MAX_CONTENT_AGE_HOURS", "24"))

# Database
DATABASE_PATH = DATA_DIR / "digest.db"

# Limits
MAX_SOURCES_PER_TYPE = int(os.getenv("MAX_SOURCES_PER_TYPE", "50"))
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "4000"))
CONCURRENT_SOURCES = int(os.getenv("CONCURRENT_SOURCES", "10"))
AI_REQUEST_TIMEOUT = int(os.getenv("AI_REQUEST_TIMEOUT", "30"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "digest.log"

# MCP Server
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
MCP_API_KEY = os.getenv("MCP_API_KEY")

# AI Prompts
IMPORTANCE_PROMPT = """
Оцени важность этой новости для специалиста по стратегическому маркетингу в России/СНГ.

Критерии оценки:
1. Применимость в работе прямо сейчас (0-25 баллов)
2. Потенциал изменить индустрию/подходы (0-25 баллов)
3. Масштаб охвата (бюджеты, аудитория) (0-25 баллов)  
4. Новизна подхода/инструмента (0-25 баллов)

Дай оценку от 0 до 100 и краткое объяснение (2-3 предложения).

Новость: {content}

Ответь в формате:
Оценка: XX
Объяснение: текст
"""

CATEGORIZATION_PROMPT = """
Определи категорию этой новости по маркетингу:

Возможные категории:
- Тренды потребления
- Каналы продвижения  
- Кейсы брендов
- Маркетинг технологии
- Исследования рынка
- Реклама и креатив
- Другое

Новость: {content}

Ответь только название категории.
"""

INSIGHTS_PROMPT = """
На основе топ-5 новостей дня сформулируй 3 ключевых инсайта для маркетолога:

Новости:
{content}

Формат ответа:
1. [Инсайт 1]
2. [Инсайт 2] 
3. [Инсайт 3]

Каждый инсайт - 1-2 предложения с практическим выводом.
""" 