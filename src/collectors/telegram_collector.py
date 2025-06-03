import asyncio
from datetime import datetime, timedelta
from typing import List
from telethon import TelegramClient
from telethon.tl.types import Channel
import structlog

from src.models import RawContent, Source, SourceType
from src.collectors.base_collector import BaseCollector
import config

logger = structlog.get_logger()

class TelegramCollector(BaseCollector):
    """Коллектор для Telegram каналов"""
    
    def __init__(self, source: Source):
        if source.type != SourceType.TELEGRAM:
            raise ValueError("Source must be of type TELEGRAM")
        super().__init__(source)
        self.client = None
    
    async def _init_client(self):
        """Инициализация Telegram клиента"""
        if not self.client:
            self.client = TelegramClient(
                session=f"session_{self.source.id}",
                api_id=config.TELEGRAM_API_ID,
                api_hash=config.TELEGRAM_API_HASH
            )
            await self.client.start(phone=config.TELEGRAM_PHONE)
    
    async def collect(self) -> List[RawContent]:
        """Сбор сообщений из Telegram канала"""
        try:
            await self._init_client()
            
            # Получение сущности канала
            channel = await self.client.get_entity(self.source.url)
            if not isinstance(channel, Channel):
                self.logger.error("Source is not a channel", url=self.source.url)
                return []
            
            # Сбор сообщений за последние 24 часа
            cutoff_time = datetime.now() - timedelta(hours=config.MAX_CONTENT_AGE_HOURS)
            messages = []
            
            async for message in self.client.iter_messages(
                channel, 
                offset_date=cutoff_time,
                limit=None
            ):
                if message.date < cutoff_time:
                    break
                    
                if message.text and len(message.text.strip()) > 50:  # Фильтр коротких сообщений
                    content = RawContent(
                        source_id=self.source.id,
                        source_name=self.source.name,
                        title=self._extract_title(message.text),
                        content=message.text,
                        url=f"https://t.me/{channel.username}/{message.id}" if channel.username else None,
                        published_at=message.date,
                        metadata={
                            "message_id": message.id,
                            "views": getattr(message, "views", 0),
                            "forwards": getattr(message, "forwards", 0),
                            "has_media": bool(message.media)
                        }
                    )
                    messages.append(content)
            
            self.log_collection_result(len(messages), len(messages))
            return messages
            
        except Exception as e:
            self.logger.error("Failed to collect from Telegram", error=str(e))
            return []
    
    async def check_availability(self) -> bool:
        """Проверка доступности канала"""
        try:
            await self._init_client()
            await self.client.get_entity(self.source.url)
            return True
        except Exception as e:
            self.logger.warning("Channel not available", error=str(e))
            return False
    
    def _extract_title(self, text: str) -> str:
        """Извлечение заголовка из текста сообщения"""
        # Используем первую строку или первые 100 символов
        lines = text.strip().split('\n')
        first_line = lines[0].strip()
        
        if len(first_line) > 100:
            return first_line[:97] + "..."
        
        return first_line if first_line else text[:100] + "..."
    
    async def close(self):
        """Закрытие соединения"""
        if self.client:
            await self.client.disconnect() 