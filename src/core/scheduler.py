import asyncio
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import structlog

from src.core.digest_service import DigestService
from src.bot.telegram_bot import TelegramBot
import config

logger = structlog.get_logger()

class DigestScheduler:
    """Планировщик для автоматической генерации и отправки дайджестов"""
    
    def __init__(self, bot: TelegramBot):
        self.bot = bot
        self.digest_service = DigestService()
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Настройка задач планировщика"""
        # Парсим время из конфига
        digest_time = datetime.strptime(config.DIGEST_TIME, "%H:%M").time()
        
        # Ежедневная отправка дайджеста
        self.scheduler.add_job(
            self._send_daily_digest,
            CronTrigger(hour=digest_time.hour, minute=digest_time.minute),
            id="daily_digest",
            name="Daily Digest Send",
            replace_existing=True
        )
        
        # Еженедельная очистка старых данных (воскресенье в 2:00)
        self.scheduler.add_job(
            self._cleanup_old_data,
            CronTrigger(day_of_week=6, hour=2, minute=0),
            id="weekly_cleanup",
            name="Weekly Data Cleanup",
            replace_existing=True
        )
        
        logger.info("Scheduler jobs configured", 
                   digest_time=config.DIGEST_TIME,
                   timezone=config.TIMEZONE)
    
    async def start(self):
        """Запуск планировщика"""
        self.scheduler.start()
        logger.info("Scheduler started")
    
    async def stop(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    async def _send_daily_digest(self):
        """Отправка ежедневного дайджеста всем пользователям"""
        try:
            logger.info("Starting scheduled digest generation")
            
            # Получаем список разрешенных пользователей
            for user_id in config.ALLOWED_USER_IDS:
                try:
                    # Генерируем дайджест для пользователя
                    digest_text = await self.digest_service.generate_daily_digest(user_id)
                    
                    if digest_text:
                        # Отправляем через бота
                        success = await self.bot.send_digest_to_user(user_id, digest_text)
                        
                        if success:
                            logger.info("Scheduled digest sent", user_id=user_id)
                        else:
                            logger.error("Failed to send scheduled digest", user_id=user_id)
                    else:
                        # Отправляем сообщение об отсутствии новостей
                        empty_message = self.digest_service._generate_empty_digest()
                        await self.bot.send_digest_to_user(user_id, empty_message)
                        logger.info("Sent empty digest", user_id=user_id)
                
                except Exception as e:
                    logger.error("Failed to process user digest", 
                               user_id=user_id, error=str(e))
                
                # Небольшая пауза между пользователями
                await asyncio.sleep(1)
            
            logger.info("Scheduled digest generation completed")
            
        except Exception as e:
            logger.error("Scheduled digest generation failed", error=str(e))
    
    async def _cleanup_old_data(self):
        """Еженедельная очистка старых данных"""
        try:
            logger.info("Starting weekly data cleanup")
            
            # Очищаем старый контент (старше 7 дней)
            deleted_count = self.digest_service.db.cleanup_old_content(days=7)
            
            logger.info("Weekly cleanup completed", deleted_items=deleted_count)
            
        except Exception as e:
            logger.error("Weekly cleanup failed", error=str(e))
    
    def get_next_run_time(self) -> datetime:
        """Получение времени следующего запуска"""
        job = self.scheduler.get_job("daily_digest")
        if job:
            return job.next_run_time
        return None
    
    def is_running(self) -> bool:
        """Проверка, запущен ли планировщик"""
        return self.scheduler.running 