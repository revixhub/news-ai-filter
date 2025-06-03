import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any
import structlog

from src.models import RawContent, Source, SourceType
from src.collectors.base_collector import BaseCollector
import config

logger = structlog.get_logger()

class YouTubeCollector(BaseCollector):
    """Коллектор для YouTube через MCP сервер"""
    
    def __init__(self, source: Source):
        if source.type != SourceType.YOUTUBE:
            raise ValueError("Source must be of type YOUTUBE")
        super().__init__(source)
    
    async def collect(self) -> List[RawContent]:
        """Сбор контента с YouTube канала через MCP"""
        try:
            if not config.MCP_SERVER_URL:
                self.logger.warning("MCP server URL not configured")
                return []
            
            # Получаем список последних видео
            videos = await self._get_recent_videos()
            
            items = []
            for video in videos:
                # Получаем summary для каждого видео
                summary = await self._get_video_summary(video['video_id'])
                
                if summary and len(summary.strip()) > 100:
                    item = RawContent(
                        source_id=self.source.id,
                        source_name=self.source.name,
                        title=video['title'],
                        content=summary[:config.MAX_CONTENT_LENGTH],
                        url=f"https://youtube.com/watch?v={video['video_id']}",
                        published_at=datetime.fromisoformat(video['published_at'].replace('Z', '+00:00')),
                        metadata={
                            "video_id": video['video_id'],
                            "duration": video.get('duration'),
                            "view_count": video.get('view_count', 0),
                            "channel_name": video.get('channel_name', self.source.name)
                        }
                    )
                    items.append(item)
            
            self.log_collection_result(len(items), len(items))
            return items
            
        except Exception as e:
            self.logger.error("Failed to collect from YouTube", error=str(e))
            return []
    
    async def _get_recent_videos(self) -> List[Dict[str, Any]]:
        """Получение списка последних видео с канала"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{config.MCP_SERVER_URL}/youtube/channel/{self.source.url}/videos"
                headers = {
                    "Authorization": f"Bearer {config.MCP_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                # Параметры запроса - последние 24 часа
                cutoff_time = datetime.now() - timedelta(hours=config.MAX_CONTENT_AGE_HOURS)
                params = {
                    "since": cutoff_time.isoformat(),
                    "limit": 20
                }
                
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('videos', [])
                    else:
                        self.logger.error("Failed to get videos from MCP", status=response.status)
                        return []
                        
        except Exception as e:
            self.logger.error("Error calling MCP server for videos", error=str(e))
            return []
    
    async def _get_video_summary(self, video_id: str) -> str:
        """Получение summary видео через MCP"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{config.MCP_SERVER_URL}/youtube/video/{video_id}/summary"
                headers = {
                    "Authorization": f"Bearer {config.MCP_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                # Параметры для summary
                payload = {
                    "format": "marketing_insights",  # Специальный формат для маркетинговых инсайтов
                    "length": "medium",  # Средняя длина summary
                    "focus": "business_application"  # Фокус на бизнес-применение
                }
                
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('summary', '')
                    else:
                        self.logger.warning("Failed to get video summary", video_id=video_id, status=response.status)
                        return ""
                        
        except Exception as e:
            self.logger.error("Error getting video summary", video_id=video_id, error=str(e))
            return ""
    
    async def check_availability(self) -> bool:
        """Проверка доступности YouTube канала через MCP"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{config.MCP_SERVER_URL}/youtube/channel/{self.source.url}/info"
                headers = {
                    "Authorization": f"Bearer {config.MCP_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                async with session.get(url, headers=headers) as response:
                    return response.status == 200
                    
        except Exception as e:
            self.logger.warning("YouTube channel not available via MCP", error=str(e))
            return False 