import asyncio
import signal
import sys
from datetime import datetime
import structlog

from src.bot.telegram_bot import TelegramBot
from src.core.scheduler import DigestScheduler
import config

# Настройка логирования
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class MarketingDigestBot:
    """Главный класс приложения"""
    
    def __init__(self):
        self.bot = None
        self.scheduler = None
        self.running = False
    
    async def start(self):
        """Запуск бота и планировщика"""
        try:
            logger.info("Starting Marketing Digest Bot", version="1.0.0")
            
            # Проверяем конфигурацию
            self._check_config()
            
            # Инициализируем компоненты
            self.bot = TelegramBot()
            self.scheduler = DigestScheduler(self.bot)
            
            # Запускаем бота
            await self.bot.start()
            logger.info("Telegram bot started successfully")
            
            # Запускаем планировщик
            await self.scheduler.start()
            logger.info("Scheduler started successfully")
            
            self.running = True
            logger.info("Marketing Digest Bot fully operational", 
                       digest_time=config.DIGEST_TIME,
                       sources_count=len(config.ALLOWED_USER_IDS))
            
            # Ждем сигнала остановки
            await self._wait_for_shutdown()
            
        except Exception as e:
            logger.error("Failed to start bot", error=str(e))
            sys.exit(1)
    
    async def stop(self):
        """Остановка бота и планировщика"""
        if not self.running:
            return
            
        logger.info("Stopping Marketing Digest Bot...")
        self.running = False
        
        try:
            # Останавливаем планировщик
            if self.scheduler:
                await self.scheduler.stop()
                logger.info("Scheduler stopped")
            
            # Останавливаем бота
            if self.bot:
                await self.bot.stop()
                logger.info("Telegram bot stopped")
            
            logger.info("Marketing Digest Bot stopped successfully")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
    
    def _check_config(self):
        """Проверка конфигурации"""
        required_vars = [
            ("TELEGRAM_BOT_TOKEN", config.TELEGRAM_BOT_TOKEN),
            ("ALLOWED_USER_IDS", config.ALLOWED_USER_IDS),
        ]
        
        # Проверяем AI провайдер
        if config.AI_PROVIDER == "openai":
            required_vars.append(("OPENAI_API_KEY", config.OPENAI_API_KEY))
        elif config.AI_PROVIDER == "anthropic":
            required_vars.append(("ANTHROPIC_API_KEY", config.ANTHROPIC_API_KEY))
        
        # Проверяем Telegram API для коллектора
        if config.TELEGRAM_API_ID and config.TELEGRAM_API_HASH:
            required_vars.extend([
                ("TELEGRAM_API_ID", config.TELEGRAM_API_ID),
                ("TELEGRAM_API_HASH", config.TELEGRAM_API_HASH),
                ("TELEGRAM_PHONE", config.TELEGRAM_PHONE)
            ])
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            logger.error("Missing required configuration variables", 
                        missing=missing_vars)
            print(f"\n❌ Отсутствуют обязательные переменные окружения:")
            for var in missing_vars:
                print(f"   - {var}")
            print(f"\nСкопируйте env.example в .env и заполните значения.")
            sys.exit(1)
        
        logger.info("Configuration validated successfully")
    
    async def _wait_for_shutdown(self):
        """Ожидание сигнала остановки"""
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal", signal=signum)
            asyncio.create_task(self.stop())
        
        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Ждем, пока running = True
        while self.running:
            await asyncio.sleep(1)

async def main():
    """Главная функция"""
    app = MarketingDigestBot()
    
    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
    finally:
        await app.stop()

if __name__ == "__main__":
    # Проверяем версию Python
    if sys.version_info < (3, 10):
        print("❌ Требуется Python 3.10 или выше")
        sys.exit(1)
    
    print("🚀 Запуск Marketing Digest Bot...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1) 