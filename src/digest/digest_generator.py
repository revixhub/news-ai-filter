from datetime import datetime
from typing import List, Dict
import structlog
from pathlib import Path

from src.models import AnalyzedContent, Digest, DigestItem, ContentCategory
import config

logger = structlog.get_logger()

class DigestGenerator:
    """Генератор дайджестов"""
    
    def __init__(self):
        self.digests_dir = config.DATA_DIR / "digests"
        self.digests_dir.mkdir(exist_ok=True)
    
    def generate_digest(self, content_list: List[AnalyzedContent], 
                       insights: List[str], user_id: int) -> Digest:
        """Генерация дайджеста"""
        try:
            # Сортируем по важности
            sorted_content = sorted(content_list, 
                                  key=lambda x: x.importance_score, 
                                  reverse=True)
            
            # Топ-5 элементов
            top_items = []
            for item in sorted_content[:5]:
                digest_item = DigestItem(
                    title=item.title,
                    content=self._truncate_content(item.content),
                    url=item.url,
                    source=item.source_name,
                    importance_score=item.importance_score,
                    category=item.category,
                    explanation=item.explanation
                )
                top_items.append(digest_item)
            
            # Остальные элементы по категориям
            other_items = self._categorize_remaining_items(sorted_content[5:])
            
            # Формируем заголовок
            title = f"📊 Маркетинг Дайджест — {datetime.now().strftime('%d.%m.%Y')}"
            
            digest = Digest(
                id=None,
                user_id=user_id,
                title=title,
                top_items=top_items,
                other_items=other_items,
                insights=insights,
                created_at=datetime.now()
            )
            
            logger.info("Digest generated", 
                       top_items=len(top_items),
                       other_items=len(other_items),
                       insights=len(insights))
            
            return digest
            
        except Exception as e:
            logger.error("Failed to generate digest", error=str(e))
            raise
    
    def format_for_telegram(self, digest: Digest) -> str:
        """Форматирование дайджеста для Telegram"""
        try:
            message = f"🔥 *{digest.title}*\n\n"
            
            # Топ-5 инсайтов
            if digest.top_items:
                message += "📈 *Топ\\-5 главных инсайтов дня:*\n\n"
                
                for i, item in enumerate(digest.top_items, 1):
                    message += f"*{i}\\. {self._escape_markdown(item.title)}*\n"
                    message += f"📝 {self._escape_markdown(item.explanation[:200])}...\n"
                    
                    if item.url:
                        message += f"🔗 [Читать источник]({item.url})\n"
                    
                    message += f"📊 Источник: {self._escape_markdown(item.source)}\n\n"
            
            # Общие инсайты дня
            if digest.insights:
                message += "🎯 *Выводы дня:*\n\n"
                for insight in digest.insights:
                    message += f"• {self._escape_markdown(insight)}\n"
                message += "\n"
            
            # Остальные новости по категориям
            if digest.other_items:
                message += "📊 *Остальные новости по категориям:*\n\n"
                
                categorized = self._group_by_category(digest.other_items)
                
                for category, items in categorized.items():
                    if items:
                        emoji = self._get_category_emoji(category)
                        message += f"{emoji} *{category.value}:*\n"
                        
                        for item in items[:3]:  # Максимум 3 на категорию
                            title_short = item.title[:60] + "..." if len(item.title) > 60 else item.title
                            message += f"  • {self._escape_markdown(title_short)}\n"
                            if item.url:
                                message += f"    [Читать]({item.url})\n"
                        message += "\n"
            
            # Футер
            message += "📱 Используйте /digest для получения нового дайджеста\n"
            message += "📋 /sources \\- список источников\n"
            message += f"⏰ Следующий дайджест: завтра в {config.DIGEST_TIME}"
            
            return message
            
        except Exception as e:
            logger.error("Failed to format digest", error=str(e))
            return "Ошибка форматирования дайджеста"
    
    def save_to_file(self, digest: Digest) -> Path:
        """Сохранение дайджеста в файл"""
        try:
            # Создаем папку по дате
            date_str = digest.created_at.strftime("%Y-%m")
            date_dir = self.digests_dir / date_str
            date_dir.mkdir(exist_ok=True)
            
            # Имя файла
            filename = f"digest_{digest.created_at.strftime('%Y%m%d_%H%M')}.md"
            filepath = date_dir / filename
            
            # Контент в markdown
            content = self._format_as_markdown(digest)
            
            # Сохраняем
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("Digest saved to file", filepath=str(filepath))
            return filepath
            
        except Exception as e:
            logger.error("Failed to save digest to file", error=str(e))
            raise
    
    def _truncate_content(self, content: str, max_length: int = 300) -> str:
        """Обрезка контента"""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."
    
    def _categorize_remaining_items(self, items: List[AnalyzedContent]) -> List[DigestItem]:
        """Категоризация оставшихся элементов"""
        result = []
        for item in items:
            if item.importance_score >= 30:  # Только важные
                digest_item = DigestItem(
                    title=item.title,
                    content=self._truncate_content(item.content, 150),
                    url=item.url,
                    source=item.source_name,
                    importance_score=item.importance_score,
                    category=item.category,
                    explanation=item.explanation
                )
                result.append(digest_item)
        
        return result[:15]  # Максимум 15 дополнительных элементов
    
    def _group_by_category(self, items: List[DigestItem]) -> Dict[ContentCategory, List[DigestItem]]:
        """Группировка по категориям"""
        grouped = {}
        for item in items:
            if item.category not in grouped:
                grouped[item.category] = []
            grouped[item.category].append(item)
        
        return grouped
    
    def _get_category_emoji(self, category: ContentCategory) -> str:
        """Эмодзи для категорий"""
        emoji_map = {
            ContentCategory.TRENDS: "📈",
            ContentCategory.CHANNELS: "📢",
            ContentCategory.CASES: "🏆",
            ContentCategory.TECHNOLOGY: "🔧",
            ContentCategory.RESEARCH: "📊",
            ContentCategory.CREATIVE: "🎨",
            ContentCategory.OTHER: "📝"
        }
        return emoji_map.get(category, "📝")
    
    def _escape_markdown(self, text: str) -> str:
        """Экранирование markdown символов для Telegram"""
        # Экранируем специальные символы для MarkdownV2
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    def _format_as_markdown(self, digest: Digest) -> str:
        """Форматирование как markdown для файла"""
        content = f"# {digest.title}\n\n"
        content += f"*Создано: {digest.created_at.strftime('%d.%m.%Y %H:%M')}*\n\n"
        
        # Топ-5
        if digest.top_items:
            content += "## 🔥 Топ-5 главных инсайтов дня\n\n"
            for i, item in enumerate(digest.top_items, 1):
                content += f"### {i}. {item.title}\n\n"
                content += f"**Оценка важности:** {item.importance_score}/100\n\n"
                content += f"**Категория:** {item.category.value}\n\n"
                content += f"**Объяснение:** {item.explanation}\n\n"
                if item.url:
                    content += f"**Источник:** [{item.source}]({item.url})\n\n"
                else:
                    content += f"**Источник:** {item.source}\n\n"
                content += "---\n\n"
        
        # Инсайты
        if digest.insights:
            content += "## 🎯 Выводы дня\n\n"
            for insight in digest.insights:
                content += f"- {insight}\n"
            content += "\n"
        
        # Остальные новости
        if digest.other_items:
            content += "## 📊 Остальные новости\n\n"
            categorized = self._group_by_category(digest.other_items)
            
            for category, items in categorized.items():
                if items:
                    content += f"### {category.value}\n\n"
                    for item in items:
                        content += f"- **{item.title}** ({item.importance_score}/100)\n"
                        if item.url:
                            content += f"  [Читать]({item.url})\n"
                        content += f"  *{item.source}*\n\n"
        
        return content 