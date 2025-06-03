from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum

class SourceType(Enum):
    TELEGRAM = "telegram"
    WEBSITE = "website"
    YOUTUBE = "youtube"

class ContentCategory(Enum):
    TRENDS = "Тренды потребления"
    CHANNELS = "Каналы продвижения"
    CASES = "Кейсы брендов"
    TECHNOLOGY = "Маркетинг технологии"
    RESEARCH = "Исследования рынка"
    CREATIVE = "Реклама и креатив"
    OTHER = "Другое"

@dataclass
class Source:
    id: Optional[int]
    type: SourceType
    name: str
    url: str
    is_active: bool = True
    created_at: Optional[datetime] = None

@dataclass
class RawContent:
    source_id: int
    source_name: str
    title: str
    content: str
    url: Optional[str]
    published_at: datetime
    metadata: Optional[dict] = None

@dataclass
class ParsedContent:
    id: Optional[int]
    source_id: int
    source_name: str
    title: str
    content: str
    url: Optional[str]
    published_at: datetime
    processed_at: Optional[datetime] = None
    is_duplicate: bool = False
    is_ad: bool = False

@dataclass
class AnalyzedContent:
    id: Optional[int]
    source_id: int
    source_name: str
    title: str
    content: str
    url: Optional[str]
    published_at: datetime
    importance_score: int
    category: ContentCategory
    explanation: str
    processed_at: Optional[datetime] = None

@dataclass
class DigestItem:
    title: str
    content: str
    url: Optional[str]
    source: str
    importance_score: int
    category: ContentCategory
    explanation: str

@dataclass
class Digest:
    id: Optional[int]
    user_id: int
    title: str
    top_items: List[DigestItem]
    other_items: List[DigestItem]
    insights: List[str]
    created_at: datetime
    sent_at: Optional[datetime] = None

@dataclass
class ProcessingMetrics:
    digest_id: Optional[int]
    processing_time: float
    sources_count: int
    raw_items_count: int
    processed_items_count: int
    top_items_count: int
    errors_count: int
    created_at: datetime 