import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List
import feedparser
from bs4 import BeautifulSoup
import html2text
import structlog

from src.models import RawContent, Source, SourceType
from src.collectors.base_collector import BaseCollector
import config

logger = structlog.get_logger()

class WebCollector(BaseCollector):
    """Коллектор для веб-сайтов и RSS"""
    
    def __init__(self, source: Source):
        if source.type != SourceType.WEBSITE:
            raise ValueError("Source must be of type WEBSITE")
        super().__init__(source)
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
    
    async def collect(self) -> List[RawContent]:
        """Сбор контента с веб-сайта"""
        try:
            # Определяем тип источника по URL
            if '/rss' in self.source.url or '/feed' in self.source.url or self.source.url.endswith('.xml'):
                return await self._collect_rss()
            else:
                return await self._collect_webpage()
                
        except Exception as e:
            self.logger.error("Failed to collect from web", error=str(e))
            return []
    
    async def _collect_rss(self) -> List[RawContent]:
        """Сбор из RSS фида"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.source.url) as response:
                if response.status != 200:
                    self.logger.error("RSS feed not accessible", status=response.status)
                    return []
                
                content = await response.text()
                feed = feedparser.parse(content)
                
                if feed.bozo:
                    self.logger.warning("RSS feed has issues", url=self.source.url)
                
                items = []
                cutoff_time = datetime.now() - timedelta(hours=config.MAX_CONTENT_AGE_HOURS)
                
                for entry in feed.entries:
                    # Парсим дату публикации
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_at = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published_at = datetime(*entry.updated_parsed[:6])
                    else:
                        published_at = datetime.now()  # Fallback
                    
                    if published_at < cutoff_time:
                        continue
                    
                    # Извлекаем контент
                    content_text = ""
                    if hasattr(entry, 'content') and entry.content:
                        content_text = self.html_converter.handle(entry.content[0].value)
                    elif hasattr(entry, 'description'):
                        content_text = self.html_converter.handle(entry.description)
                    elif hasattr(entry, 'summary'):
                        content_text = self.html_converter.handle(entry.summary)
                    
                    if len(content_text.strip()) < 100:  # Слишком короткий контент
                        continue
                    
                    item = RawContent(
                        source_id=self.source.id,
                        source_name=self.source.name,
                        title=entry.title if hasattr(entry, 'title') else "Без заголовка",
                        content=content_text[:config.MAX_CONTENT_LENGTH],
                        url=entry.link if hasattr(entry, 'link') else None,
                        published_at=published_at,
                        metadata={
                            "author": getattr(entry, 'author', ''),
                            "tags": [tag.term for tag in getattr(entry, 'tags', [])]
                        }
                    )
                    items.append(item)
                
                self.log_collection_result(len(items), len(items))
                return items
    
    async def _collect_webpage(self) -> List[RawContent]:
        """Сбор с обычной веб-страницы"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.source.url) as response:
                if response.status != 200:
                    self.logger.error("Webpage not accessible", status=response.status)
                    return []
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Удаляем ненужные элементы
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()
                
                # Ищем статьи или основной контент
                articles = self._find_articles(soup)
                
                items = []
                for article in articles:
                    title = self._extract_title(article)
                    content = self._extract_content(article)
                    link = self._extract_link(article)
                    
                    if len(content.strip()) < 200:  # Слишком короткий контент
                        continue
                    
                    item = RawContent(
                        source_id=self.source.id,
                        source_name=self.source.name,
                        title=title,
                        content=content[:config.MAX_CONTENT_LENGTH],
                        url=link or self.source.url,
                        published_at=datetime.now(),  # Для обычных страниц используем текущее время
                        metadata={"scraped": True}
                    )
                    items.append(item)
                
                self.log_collection_result(len(items), len(items))
                return items
    
    def _find_articles(self, soup: BeautifulSoup) -> List:
        """Поиск статей на странице"""
        # Ищем по тегам article, или элементам с классами новостей
        articles = soup.find_all(['article'])
        
        if not articles:
            # Пробуем найти по классам
            news_classes = ['news', 'post', 'article', 'content', 'entry']
            for class_name in news_classes:
                elements = soup.find_all(['div', 'section'], class_=lambda x: x and any(cls in x.lower() for cls in news_classes))
                if elements:
                    articles = elements[:5]  # Берем максимум 5 элементов
                    break
        
        if not articles:
            # Fallback - основной контент
            main_content = soup.find(['main', 'div'], {'id': ['content', 'main']})
            if main_content:
                articles = [main_content]
        
        return articles[:3]  # Максимум 3 статьи с одной страницы
    
    def _extract_title(self, article) -> str:
        """Извлечение заголовка статьи"""
        for tag in ['h1', 'h2', 'h3']:
            title_elem = article.find(tag)
            if title_elem:
                return title_elem.get_text().strip()
        
        return f"Статья с {self.source.name}"
    
    def _extract_content(self, article) -> str:
        """Извлечение текста статьи"""
        # Удаляем ненужные элементы
        for element in article.find_all(['script', 'style', 'aside', 'nav']):
            element.decompose()
        
        return self.html_converter.handle(str(article)).strip()
    
    def _extract_link(self, article) -> str:
        """Извлечение ссылки на статью"""
        link_elem = article.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('http'):
                return href
            elif href.startswith('/'):
                from urllib.parse import urljoin
                return urljoin(self.source.url, href)
        
        return None
    
    async def check_availability(self) -> bool:
        """Проверка доступности сайта"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.source.url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.warning("Website not available", error=str(e))
            return False 