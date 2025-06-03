from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional
import structlog

from src.models import RawContent, Source

logger = structlog.get_logger()

class BaseCollector(ABC):
    """Базовый класс для всех коллекторов"""
    
    def __init__(self, source: Source):
        self.source = source
        self.logger = logger.bind(source=source.name, type=source.type.value)
    
    @abstractmethod
    async def collect(self) -> List[RawContent]:
        """Сбор контента из источника"""
        pass
    
    @abstractmethod
    async def check_availability(self) -> bool:
        """Проверка доступности источника"""
        pass
    
    def get_last_update_time(self) -> Optional[datetime]:
        """Время последнего обновления (переопределить если нужно)"""
        return None
    
    def filter_content_by_date(self, content_list: List[RawContent], 
                             max_age_hours: int = 24) -> List[RawContent]:
        """Фильтрация контента по дате"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        return [content for content in content_list 
                if content.published_at >= cutoff_time]
    
    def log_collection_result(self, collected_count: int, filtered_count: int):
        """Логирование результатов сбора"""
        self.logger.info(
            "Content collected",
            collected=collected_count,
            filtered=filtered_count,
            source=self.source.name
        ) 