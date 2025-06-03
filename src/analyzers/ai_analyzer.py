import asyncio
from typing import List, Tuple, Optional
import openai
import anthropic
import structlog
import re

from src.models import ParsedContent, AnalyzedContent, ContentCategory
import config

logger = structlog.get_logger()

class AIAnalyzer:
    """AI анализатор контента"""
    
    def __init__(self):
        self.provider = config.AI_PROVIDER
        
        if self.provider == "openai":
            openai.api_key = config.OPENAI_API_KEY
            self.client = openai.AsyncOpenAI()
        elif self.provider == "anthropic":
            self.client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    async def analyze_content(self, content: ParsedContent) -> AnalyzedContent:
        """Анализ одного элемента контента"""
        try:
            # Анализ важности
            importance_score, explanation = await self._analyze_importance(content)
            
            # Категоризация
            category = await self._categorize_content(content)
            
            return AnalyzedContent(
                id=content.id,
                source_id=content.source_id,
                source_name=content.source_name,
                title=content.title,
                content=content.content,
                url=content.url,
                published_at=content.published_at,
                importance_score=importance_score,
                category=category,
                explanation=explanation,
                processed_at=content.processed_at
            )
            
        except Exception as e:
            logger.error("Failed to analyze content", content_id=content.id, error=str(e))
            # Возвращаем с минимальными значениями
            return AnalyzedContent(
                id=content.id,
                source_id=content.source_id,
                source_name=content.source_name,
                title=content.title,
                content=content.content,
                url=content.url,
                published_at=content.published_at,
                importance_score=0,
                category=ContentCategory.OTHER,
                explanation="Ошибка анализа",
                processed_at=content.processed_at
            )
    
    async def analyze_batch(self, content_list: List[ParsedContent]) -> List[AnalyzedContent]:
        """Батч-анализ списка контента"""
        tasks = [self.analyze_content(content) for content in content_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        analyzed_content = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Batch analysis failed", error=str(result))
                continue
            analyzed_content.append(result)
        
        logger.info("Batch analysis completed", 
                   total=len(content_list), 
                   successful=len(analyzed_content))
        
        return analyzed_content
    
    async def _analyze_importance(self, content: ParsedContent) -> Tuple[int, str]:
        """Анализ важности контента"""
        try:
            prompt = config.IMPORTANCE_PROMPT.format(
                content=f"Заголовок: {content.title}\n\nКонтент: {content.content[:1000]}"
            )
            
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=config.AI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.3
                )
                result = response.choices[0].message.content
                
            elif self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=config.AI_MODEL,
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}]
                )
                result = response.content[0].text
            
            # Парсинг ответа
            score, explanation = self._parse_importance_response(result)
            return score, explanation
            
        except Exception as e:
            logger.error("Importance analysis failed", error=str(e))
            return 50, "Не удалось проанализировать"
    
    async def _categorize_content(self, content: ParsedContent) -> ContentCategory:
        """Категоризация контента"""
        try:
            prompt = config.CATEGORIZATION_PROMPT.format(
                content=f"Заголовок: {content.title}\n\nКонтент: {content.content[:500]}"
            )
            
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=config.AI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50,
                    temperature=0.1
                )
                result = response.choices[0].message.content.strip()
                
            elif self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=config.AI_MODEL,
                    max_tokens=50,
                    messages=[{"role": "user", "content": prompt}]
                )
                result = response.content[0].text.strip()
            
            # Маппинг на enum
            category_mapping = {
                "Тренды потребления": ContentCategory.TRENDS,
                "Каналы продвижения": ContentCategory.CHANNELS,
                "Кейсы брендов": ContentCategory.CASES,
                "Маркетинг технологии": ContentCategory.TECHNOLOGY,
                "Исследования рынка": ContentCategory.RESEARCH,
                "Реклама и креатив": ContentCategory.CREATIVE,
            }
            
            return category_mapping.get(result, ContentCategory.OTHER)
            
        except Exception as e:
            logger.error("Categorization failed", error=str(e))
            return ContentCategory.OTHER
    
    def _parse_importance_response(self, response: str) -> Tuple[int, str]:
        """Парсинг ответа на анализ важности"""
        try:
            # Ищем паттерн "Оценка: XX"
            score_match = re.search(r'Оценка:\s*(\d+)', response)
            if score_match:
                score = int(score_match.group(1))
                score = max(0, min(100, score))  # Ограничиваем 0-100
            else:
                score = 50  # Дефолтное значение
            
            # Ищем объяснение после "Объяснение:"
            explanation_match = re.search(r'Объяснение:\s*(.+)', response, re.DOTALL)
            if explanation_match:
                explanation = explanation_match.group(1).strip()
            else:
                explanation = "Нет объяснения"
            
            return score, explanation
            
        except Exception:
            return 50, "Ошибка парсинга ответа"
    
    async def generate_insights(self, top_content: List[AnalyzedContent]) -> List[str]:
        """Генерация общих инсайтов дня"""
        try:
            if not top_content:
                return ["Сегодня не найдено значимых новостей"]
            
            # Формируем контент для анализа
            content_summary = ""
            for i, item in enumerate(top_content[:5], 1):
                content_summary += f"{i}. {item.title}\n{item.explanation[:200]}...\n\n"
            
            prompt = config.INSIGHTS_PROMPT.format(content=content_summary)
            
            if self.provider == "openai":
                response = await self.client.chat.completions.create(
                    model=config.AI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.4
                )
                result = response.choices[0].message.content
                
            elif self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=config.AI_MODEL,
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                result = response.content[0].text
            
            # Парсим инсайты
            insights = []
            lines = result.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and (line.startswith(('1.', '2.', '3.')) or line.startswith('-')):
                    # Убираем нумерацию
                    clean_insight = re.sub(r'^\d+\.\s*', '', line)
                    clean_insight = re.sub(r'^-\s*', '', clean_insight)
                    if clean_insight:
                        insights.append(clean_insight)
            
            return insights[:3] if insights else ["Не удалось сформировать инсайты"]
            
        except Exception as e:
            logger.error("Insights generation failed", error=str(e))
            return ["Ошибка генерации инсайтов"]
    
    async def check_for_ad_content(self, content: ParsedContent) -> bool:
        """Проверка на рекламный контент"""
        # Простая проверка по ключевым словам
        ad_keywords = [
            'реклама', 'промо', 'скидка', 'акция', 'купить',
            'заказать', 'партнер', 'спонсор', 'affiliate'
        ]
        
        text_lower = f"{content.title} {content.content}".lower()
        return any(keyword in text_lower for keyword in ad_keywords) 