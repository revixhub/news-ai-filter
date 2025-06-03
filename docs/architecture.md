# Архитектура Marketing Digest Bot

## 🏗 Общая архитектура

### Компонентная схема
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Источники    │     │    Источники    │     │    Источники    │
│    Telegram     │     │    Websites     │     │    YouTube      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Collector Service    │
                    │  (Сервис сбора данных)  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Parser Service      │
                    │ (Обработка и очистка)   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      AI Analyzer        │
                    │  (OpenAI/Claude API)    │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Digest Generator      │
                    │ (Формирование сводки)   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Telegram Bot API     │
                    │      (Доставка)         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      Пользователь       │
                    └─────────────────────────┘
```

## 📦 Модули системы

### 1. Collector Service (src/collectors/)
**Назначение**: Сбор данных из различных источников

**Компоненты**:
- `telegram_collector.py` - сбор из Telegram каналов
- `web_collector.py` - парсинг веб-сайтов и RSS
- `youtube_collector.py` - интеграция с MCP сервером
- `base_collector.py` - базовый класс коллектора

**Ключевые методы**:
```python
class BaseCollector:
    async def collect(self) -> List[RawContent]
    async def check_source_availability(self) -> bool
    def get_last_update_time(self) -> datetime
```

### 2. Parser Service (src/parsers/)
**Назначение**: Обработка и структурирование сырых данных

**Компоненты**:
- `content_parser.py` - основной парсер
- `deduplicator.py` - удаление дубликатов
- `content_filter.py` - фильтрация контента
- `normalizer.py` - нормализация текста

**Структура данных**:
```python
@dataclass
class ParsedContent:
    id: str
    source: str
    title: str
    content: str
    url: str
    published_at: datetime
    category: Optional[str]
    is_ad: bool
```

### 3. AI Analyzer (src/analyzers/)
**Назначение**: Анализ важности и генерация выводов

**Компоненты**:
- `importance_scorer.py` - оценка важности (0-100)
- `categorizer.py` - категоризация контента
- `insights_generator.py` - генерация инсайтов
- `llm_client.py` - клиент для работы с LLM API

**Промпт для анализа**:
```python
IMPORTANCE_PROMPT = """
Оцени важность новости для специалиста по стратегическому маркетингу (РФ/СНГ).
Критерии:
1. Применимость в работе прямо сейчас
2. Потенциал изменить индустрию
3. Масштаб охвата (бюджеты, аудитория)
4. Новизна подхода/инструмента

Оценка от 0 до 100.
"""
```

### 4. Digest Generator (src/digest/)
**Назначение**: Формирование финального дайджеста

**Компоненты**:
- `digest_builder.py` - сборка дайджеста
- `formatter.py` - форматирование для Telegram
- `template_engine.py` - шаблоны сообщений

**Структура дайджеста**:
```
🔥 Топ-5 инсайтов дня

1. [Заголовок]
   📝 [Краткое описание]
   💡 [Вывод AI]
   🔗 [Читать источник]

📊 Остальные новости
[Категоризированный список]

🎯 Выводы дня
[Общие тренды и рекомендации]
```

### 5. Bot Service (src/bot/)
**Назначение**: Интерфейс взаимодействия через Telegram

**Компоненты**:
- `bot.py` - основная логика бота
- `handlers.py` - обработчики команд
- `scheduler.py` - планировщик задач
- `user_manager.py` - управление пользователями

### 6. Database Layer (src/database/)
**Назначение**: Хранение и управление данными

**Схема БД (SQLite)**:
```sql
-- Источники
CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP
);

-- Контент
CREATE TABLE content (
    id INTEGER PRIMARY KEY,
    source_id INTEGER,
    title TEXT,
    content TEXT,
    url TEXT,
    importance_score INTEGER,
    category TEXT,
    published_at TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);

-- Дайджесты
CREATE TABLE digests (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    content TEXT,
    created_at TIMESTAMP
);

-- Метрики
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY,
    digest_id INTEGER,
    processing_time REAL,
    sources_count INTEGER,
    items_count INTEGER,
    FOREIGN KEY (digest_id) REFERENCES digests(id)
);
```

## 🔄 Поток данных

### Ежедневный процесс (9:30 - 10:00)
1. **9:30** - Scheduler запускает процесс сбора
2. **9:30-9:50** - Collectors собирают данные параллельно
3. **9:50-9:55** - Parser обрабатывает и дедуплицирует
4. **9:55-9:58** - AI Analyzer оценивает и категоризирует
5. **9:58-9:59** - Digest Generator формирует сводку
6. **10:00** - Bot отправляет дайджест пользователю

### Ручной запрос (/digest)
1. Проверка кеша (если < 30 минут с последнего)
2. Если кеш устарел - запуск полного цикла
3. Отправка результата пользователю

## 🛡 Безопасность и надежность

### Обработка ошибок
```python
class ErrorHandler:
    - Retry механизм (3 попытки с exponential backoff)
    - Fallback на кешированные данные
    - Логирование всех ошибок
    - Уведомление админа о критических сбоях
```

### Защита данных
- API ключи в переменных окружения
- Ограничение доступа по user_id
- Локальное хранение чувствительных данных
- Отсутствие публичных endpoints

## 📊 Мониторинг и логирование

### Уровни логов
- **DEBUG**: Детальная информация о работе
- **INFO**: Ключевые события (старт/стоп, отправка)
- **WARNING**: Некритичные проблемы
- **ERROR**: Ошибки, требующие внимания

### Метрики производительности
- Время обработки каждого источника
- Количество обработанных элементов
- Использование API квот
- Размер генерируемых дайджестов

## 🔧 Конфигурация

### Переменные окружения (.env)
```bash
# API Keys
TELEGRAM_BOT_TOKEN=xxx
OPENAI_API_KEY=xxx

# Settings
DIGEST_TIME=10:00
TIMEZONE=Europe/Moscow
MAX_CONTENT_AGE_DAYS=1

# Limits
MAX_SOURCES_PER_TYPE=50
MAX_CONTENT_LENGTH=4000
AI_TIMEOUT_SECONDS=30
```

### Настройки источников (sources.json)
```json
{
  "telegram": {
    "channels": ["@channel1", "@channel2"],
    "check_interval": 300
  },
  "websites": {
    "urls": ["https://site.com/rss"],
    "check_interval": 600
  },
  "youtube": {
    "channels": ["UC_xxx"],
    "mcp_server_url": "http://localhost:8080"
  }
}
```

## 🚀 Масштабирование

### Текущие ограничения
- Однопользовательская система
- Локальное выполнение
- Синхронная обработка источников

### План масштабирования
1. **Фаза 1**: Асинхронная обработка источников
2. **Фаза 2**: Redis для кеширования
3. **Фаза 3**: Celery для фоновых задач
4. **Фаза 4**: PostgreSQL вместо SQLite
5. **Фаза 5**: Микросервисная архитектура

## 🔌 Интеграции

### YouTube MCP Server
```python
class YouTubeMCPClient:
    async def process_video(video_id: str) -> VideoSummary:
        response = await mcp_request("/process", {
            "video_id": video_id,
            "summary_length": "short"
        })
        return VideoSummary.from_dict(response)
```

### LLM API абстракция
```python
class LLMProvider(ABC):
    @abstractmethod
    async def analyze(prompt: str, content: str) -> AnalysisResult
    
class OpenAIProvider(LLMProvider):
    # Реализация для OpenAI
    
class ClaudeProvider(LLMProvider):
    # Реализация для Claude
```

## 📝 Соглашения по коду

### Структура модулей
- Один класс = один файл
- Dependency Injection для тестируемости
- Type hints везде
- Docstrings для публичных методов

### Асинхронность
- asyncio для I/O операций
- aiohttp для HTTP запросов
- aiogram для Telegram Bot API
- asyncpg для БД (в будущем)