import asyncio
from datetime import datetime
from typing import Optional
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
import structlog

from src.core.digest_service import DigestService
import config

logger = structlog.get_logger()

class TelegramBot:
    """Telegram бот для отправки дайджестов"""
    
    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.allowed_users = set(config.ALLOWED_USER_IDS)
        self.digest_service = DigestService()
        self.application = None
    
    async def start(self):
        """Запуск бота"""
        self.application = Application.builder().token(self.token).build()
        
        # Добавляем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("digest", self.digest_command))
        self.application.add_handler(CommandHandler("sources", self.sources_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Устанавливаем команды бота
        await self._set_bot_commands()
        
        # Запускаем бота
        await self.application.initialize()
        await self.application.start()
        
        logger.info("Telegram bot started")
    
    async def stop(self):
        """Остановка бота"""
        if self.application:
            await self.application.stop()
            logger.info("Telegram bot stopped")
    
    async def send_digest_to_user(self, user_id: int, digest_text: str) -> bool:
        """Отправка дайджеста пользователю"""
        try:
            # Проверяем, что сообщение не превышает лимит Telegram
            if len(digest_text) > 4096:
                # Разбиваем на части
                parts = self._split_message(digest_text)
                for i, part in enumerate(parts):
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=part,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True
                    )
                    if i < len(parts) - 1:
                        await asyncio.sleep(1)  # Пауза между сообщениями
            else:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=digest_text,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    disable_web_page_preview=True
                )
            
            logger.info("Digest sent to user", user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("Failed to send digest", user_id=user_id, error=str(e))
            return False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            await update.message.reply_text("❌ У вас нет доступа к этому боту.")
            return
        
        welcome_text = """
🤖 *Добро пожаловать в Marketing Digest Bot\\!*

Я помогу вам экономить время на мониторинге маркетинговых новостей\\.

📈 *Что я умею:*
• Собираю новости из 30\\+ источников
• Анализирую важность с помощью AI
• Формирую топ\\-5 инсайтов дня
• Отправляю дайджест каждый день в 10:00

🚀 *Команды:*
/digest \\- получить дайджест сейчас
/sources \\- список источников
/stats \\- статистика работы
/help \\- справка

Ваш первый дайджест будет готов завтра утром\\!
        """
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        if not self._is_authorized(update.effective_user.id):
            return
        
        help_text = """
📋 *Справка по командам:*

/start \\- запуск и приветствие
/digest \\- сформировать дайджест прямо сейчас
/sources \\- показать список источников
/stats \\- статистика обработки
/help \\- эта справка

⏰ *Автоматическая отправка:* каждый день в 10:00

🔧 *Настройки:*
• Источники обновляются автоматически
• AI анализирует важность по 4 критериям
• Топ\\-5 формируется по оценке важности

💡 *Совет:* Используйте /digest если хотите получить свежие новости прямо сейчас\\!
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    
    async def digest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /digest"""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            return
        
        # Показываем индикатор генерации
        await update.message.reply_text("⏳ Генерирую дайджест... Это займет 1-2 минуты.")
        
        try:
            # Генерируем дайджест
            digest_text = await self.digest_service.generate_daily_digest(user_id)
            
            if digest_text:
                await self.send_digest_to_user(user_id, digest_text)
            else:
                await update.message.reply_text(
                    "😔 Не удалось сформировать дайджест. Попробуйте позже."
                )
                
        except Exception as e:
            logger.error("Digest command failed", user_id=user_id, error=str(e))
            await update.message.reply_text(
                "❌ Произошла ошибка при генерации дайджеста. Попробуйте позже."
            )
    
    async def sources_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /sources"""
        if not self._is_authorized(update.effective_user.id):
            return
        
        try:
            sources_text = await self.digest_service.get_sources_info()
            await update.message.reply_text(
                sources_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error("Sources command failed", error=str(e))
            await update.message.reply_text("❌ Ошибка получения списка источников.")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        if not self._is_authorized(update.effective_user.id):
            return
        
        try:
            stats_text = await self.digest_service.get_stats()
            await update.message.reply_text(
                stats_text,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        except Exception as e:
            logger.error("Stats command failed", error=str(e))
            await update.message.reply_text("❌ Ошибка получения статистики.")
    
    def _is_authorized(self, user_id: int) -> bool:
        """Проверка авторизации пользователя"""
        return user_id in self.allowed_users
    
    def _split_message(self, text: str, max_length: int = 4096) -> list:
        """Разбивка длинного сообщения на части"""
        parts = []
        current_part = ""
        
        lines = text.split('\n')
        
        for line in lines:
            if len(current_part) + len(line) + 1 <= max_length:
                current_part += line + '\n'
            else:
                if current_part:
                    parts.append(current_part.rstrip())
                current_part = line + '\n'
        
        if current_part:
            parts.append(current_part.rstrip())
        
        return parts
    
    async def _set_bot_commands(self):
        """Установка команд бота в меню"""
        commands = [
            BotCommand("start", "Запуск бота"),
            BotCommand("digest", "Получить дайджест сейчас"),
            BotCommand("sources", "Список источников"),
            BotCommand("stats", "Статистика работы"),
            BotCommand("help", "Справка по командам")
        ]
        
        await self.application.bot.set_my_commands(commands) 