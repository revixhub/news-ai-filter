import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
import structlog

from src.database import DatabaseManager
from src.models import Source, SourceType, RawContent, ParsedContent
from src.collectors.telegram_collector import TelegramCollector
from src.collectors.web_collector import WebCollector
from src.collectors.youtube_collector import YouTubeCollector
from src.analyzers.ai_analyzer import AIAnalyzer
from src.digest.digest_generator import DigestGenerator
import config

logger = structlog.get_logger()

class DigestService:
    """Основной сервис для генерации дайджестов"""
    
    def __init__(self):
        self.db = DatabaseManager(config.DATABASE_PATH)
        self.ai_analyzer = AIAnalyzer()
        self.digest_generator = DigestGenerator()
        self._init_default_sources()
    
    def _init_default_sources(self):
        """Инициализация источников по умолчанию"""
        default_sources = [
            # Telegram каналы
            Source(None, SourceType.TELEGRAM, "Маркетинг", "@marketing_news", True),
            Source(None, SourceType.TELEGRAM, "Digital Agency", "@digitalagency", True),
            Source(None, SourceType.TELEGRAM, "Sostav", "@sostav", True),
            
            # Веб-сайты
            Source(None, SourceType.WEBSITE, "Sostav.ru", "https://sostav.ru/rss/", True),
            Source(None, SourceType.WEBSITE, "VC.ru Marketing", "https://vc.ru/marketing/rss", True),
            Source(None, SourceType.WEBSITE, "Cossa", "https://www.cossa.ru/rss/", True),
            
            # YouTube каналы
            Source(None, SourceType.YOUTUBE, "Маркетинг ТВ", "UCMarketingTV", True),
        ]
        
        # Добавляем источники, если их еще нет
        existing_sources = self.db.get_active_sources()
        if not existing_sources:
            for source in default_sources:
                try:
                    self.db.add_source(source)
                    logger.info("Added default source", name=source.name, type=source.type.value)
                except Exception as e:
                    logger.warning("Failed to add default source", name=source.name, error=str(e))
    
    async def generate_daily_digest(self, user_id: int) -> Optional[str]:
        """Генерация ежедневного дайджеста"""
        start_time = datetime.now()
        
        try:
            logger.info("Starting digest generation", user_id=user_id)
            
            # 1. Сбор данных из всех источников
            raw_content = await self._collect_from_all_sources()
            logger.info("Raw content collected", count=len(raw_content))
            
            if not raw_content:
                return self._generate_empty_digest()
            
            # 2. Парсинг и очистка
            parsed_content = await self._parse_and_filter_content(raw_content)
            logger.info("Content parsed", count=len(parsed_content))
            
            if not parsed_content:
                return self._generate_empty_digest()
            
            # 3. AI анализ
            analyzed_content = await self.ai_analyzer.analyze_batch(parsed_content)
            logger.info("Content analyzed", count=len(analyzed_content))
            
            # 4. Сохранение в БД
            self._save_analyzed_content(analyzed_content)
            
            # 5. Генерация инсайтов
            top_content = sorted(analyzed_content, key=lambda x: x.importance_score, reverse=True)[:5]
            insights = await self.ai_analyzer.generate_insights(top_content)
            
            # 6. Формирование дайджеста
            digest = self.digest_generator.generate_digest(analyzed_content, insights, user_id)
            
            # 7. Сохранение дайджеста
            digest_id = self.db.save_digest(digest)
            digest.id = digest_id
            
            # 8. Сохранение в файл
            self.digest_generator.save_to_file(digest)
            
            # 9. Форматирование для Telegram
            telegram_text = self.digest_generator.format_for_telegram(digest)
            
            # 10. Сохранение метрик
            processing_time = (datetime.now() - start_time).total_seconds()
            self._save_metrics(digest_id, processing_time, len(raw_content), len(analyzed_content))
            
            logger.info("Digest generation completed", 
                       user_id=user_id, 
                       processing_time=processing_time,
                       items_count=len(analyzed_content))
            
            return telegram_text
            
        except Exception as e:
            logger.error("Digest generation failed", user_id=user_id, error=str(e))
            return None
    
    async def _collect_from_all_sources(self) -> List[RawContent]:
        """Сбор данных из всех источников"""
        sources = self.db.get_active_sources()
        all_content = []
        
        # Группируем источники по типам для параллельной обработки
        telegram_sources = [s for s in sources if s.type == SourceType.TELEGRAM]
        web_sources = [s for s in sources if s.type == SourceType.WEBSITE]
        youtube_sources = [s for s in sources if s.type == SourceType.YOUTUBE]
        
        # Собираем данные параллельно
        tasks = []
        
        # Telegram
        for source in telegram_sources:
            collector = TelegramCollector(source)
            tasks.append(self._safe_collect(collector, source.name))
        
        # Web
        for source in web_sources:
            collector = WebCollector(source)
            tasks.append(self._safe_collect(collector, source.name))
        
        # YouTube
        for source in youtube_sources:
            collector = YouTubeCollector(source)
            tasks.append(self._safe_collect(collector, source.name))
        
        # Выполняем все задачи параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собираем результаты
        for result in results:
            if isinstance(result, list):
                all_content.extend(result)
            elif isinstance(result, Exception):
                logger.error("Collection task failed", error=str(result))
        
        return all_content
    
    async def _safe_collect(self, collector, source_name: str) -> List[RawContent]:
        """Безопасный сбор с обработкой ошибок"""
        try:
            return await collector.collect()
        except Exception as e:
            logger.error("Collection failed", source=source_name, error=str(e))
            return []
    
    async def _parse_and_filter_content(self, raw_content: List[RawContent]) -> List[ParsedContent]:
        """Парсинг и фильтрация контента"""
        parsed_items = []
        
        for item in raw_content:
            # Проверка на дубликаты
            if self.db.check_duplicate(item.title, item.source_id):
                continue
            
            # Проверка на рекламный контент
            parsed_item = ParsedContent(
                id=None,
                source_id=item.source_id,
                source_name=item.source_name,
                title=item.title,
                content=item.content,
                url=item.url,
                published_at=item.published_at,
                processed_at=datetime.now(),
                is_duplicate=False,
                is_ad=await self.ai_analyzer.check_for_ad_content(
                    ParsedContent(None, item.source_id, item.source_name, 
                                item.title, item.content, item.url, item.published_at)
                )
            )
            
            # Сохраняем в БД
            content_id = self.db.save_content(parsed_item)
            parsed_item.id = content_id
            
            parsed_items.append(parsed_item)
        
        return parsed_items
    
    def _save_analyzed_content(self, analyzed_content: List):
        """Сохранение результатов анализа в БД"""
        for item in analyzed_content:
            if item.id:
                self.db.update_content_analysis(
                    item.id, 
                    item.importance_score, 
                    item.category.value,
                    item.explanation
                )
    
    def _save_metrics(self, digest_id: Optional[int], processing_time: float, 
                     raw_count: int, processed_count: int):
        """Сохранение метрик обработки"""
        from src.models import ProcessingMetrics
        
        metrics = ProcessingMetrics(
            digest_id=digest_id,
            processing_time=processing_time,
            sources_count=len(self.db.get_active_sources()),
            raw_items_count=raw_count,
            processed_items_count=processed_count,
            top_items_count=min(5, processed_count),
            errors_count=0,  # TODO: подсчет ошибок
            created_at=datetime.now()
        )
        
        self.db.save_metrics(metrics)
    
    def _generate_empty_digest(self) -> str:
        """Генерация пустого дайджеста"""
        return """
🤖 *Маркетинг Дайджест — {}*

😔 Сегодня не найдено новых важных новостей\\. 

Возможные причины:
• Источники временно недоступны
• Нет новых публикаций за последние 24 часа
• Все новости оказались неважными \\(< 30 баллов\\)

🔄 Попробуйте команду /digest через час или завтра утром\\!
        """.format(datetime.now().strftime('%d\\.%m\\.%Y'))
    
    async def get_sources_info(self) -> str:
        """Получение информации об источниках"""
        sources = self.db.get_active_sources()
        
        if not sources:
            return "❌ Нет активных источников"
        
        telegram_sources = [s for s in sources if s.type == SourceType.TELEGRAM]
        web_sources = [s for s in sources if s.type == SourceType.WEBSITE]
        youtube_sources = [s for s in sources if s.type == SourceType.YOUTUBE]
        
        text = f"📋 *Активные источники \\({len(sources)} шт\\.\\):*\n\n"
        
        if telegram_sources:
            text += "📱 *Telegram каналы:*\n"
            for source in telegram_sources:
                text += f"  • {self._escape_markdown(source.name)}\n"
            text += "\n"
        
        if web_sources:
            text += "🌐 *Веб\\-сайты:*\n"
            for source in web_sources:
                text += f"  • {self._escape_markdown(source.name)}\n"
            text += "\n"
        
        if youtube_sources:
            text += "📺 *YouTube каналы:*\n"
            for source in youtube_sources:
                text += f"  • {self._escape_markdown(source.name)}\n"
            text += "\n"
        
        text += f"🔄 Последний сбор: сегодня в {config.DIGEST_TIME}\n"
        text += "⏰ Следующий сбор: завтра в то же время"
        
        return text
    
    async def get_stats(self) -> str:
        """Получение статистики работы"""
        try:
            # Получаем статистику за последние 7 дней
            recent_content = self.db.get_recent_content(hours=24*7)
            
            if not recent_content:
                return "📊 *Статистика:* нет данных за последние 7 дней"
            
            # Группируем по дням
            by_day = {}
            for item in recent_content:
                day = item.published_at.strftime('%Y-%m-%d')
                if day not in by_day:
                    by_day[day] = 0
                by_day[day] += 1
            
            avg_per_day = len(recent_content) / 7
            
            text = "📊 *Статистика за 7 дней:*\n\n"
            text += f"📈 Всего обработано: {len(recent_content)} новостей\n"
            text += f"📊 В среднем за день: {avg_per_day:.1f} новостей\n"
            text += f"🎯 Активных источников: {len(self.db.get_active_sources())}\n\n"
            
            text += "*По дням:*\n"
            for day, count in sorted(by_day.items())[-3:]:  # Последние 3 дня
                date_formatted = datetime.strptime(day, '%Y-%m-%d').strftime('%d\\.%m')
                text += f"  • {date_formatted}: {count} новостей\n"
            
            return text
            
        except Exception as e:
            logger.error("Stats generation failed", error=str(e))
            return "❌ Ошибка получения статистики"
    
    def _escape_markdown(self, text: str) -> str:
        """Экранирование markdown символов"""
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text 