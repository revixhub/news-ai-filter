import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
import structlog

from src.models import Source, SourceType, ParsedContent, AnalyzedContent, Digest, ProcessingMetrics

logger = structlog.get_logger()

class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Создание таблиц БД"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    source_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    url TEXT,
                    published_at TIMESTAMP NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    importance_score INTEGER,
                    category TEXT,
                    explanation TEXT,
                    is_duplicate BOOLEAN DEFAULT 0,
                    is_ad BOOLEAN DEFAULT 0,
                    FOREIGN KEY (source_id) REFERENCES sources(id)
                );
                
                CREATE TABLE IF NOT EXISTS digests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    insights TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    digest_id INTEGER,
                    processing_time REAL NOT NULL,
                    sources_count INTEGER NOT NULL,
                    raw_items_count INTEGER NOT NULL,
                    processed_items_count INTEGER NOT NULL,
                    top_items_count INTEGER NOT NULL,
                    errors_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (digest_id) REFERENCES digests(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_content_published_at ON content(published_at);
                CREATE INDEX IF NOT EXISTS idx_content_source_id ON content(source_id);
                CREATE INDEX IF NOT EXISTS idx_content_importance ON content(importance_score);
            """)
        logger.info("Database initialized", db_path=str(self.db_path))
    
    def add_source(self, source: Source) -> int:
        """Добавление источника"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO sources (type, name, url, is_active) VALUES (?, ?, ?, ?)",
                (source.type.value, source.name, source.url, source.is_active)
            )
            return cursor.lastrowid
    
    def get_active_sources(self, source_type: Optional[SourceType] = None) -> List[Source]:
        """Получение активных источников"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if source_type:
                rows = conn.execute(
                    "SELECT * FROM sources WHERE is_active = 1 AND type = ?",
                    (source_type.value,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sources WHERE is_active = 1"
                ).fetchall()
            
            return [Source(
                id=row["id"],
                type=SourceType(row["type"]),
                name=row["name"],
                url=row["url"],
                is_active=bool(row["is_active"]),
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
            ) for row in rows]
    
    def save_content(self, content: ParsedContent) -> int:
        """Сохранение контента"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO content 
                (source_id, source_name, title, content, url, published_at, is_duplicate, is_ad)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content.source_id, content.source_name, content.title, 
                content.content, content.url, content.published_at,
                content.is_duplicate, content.is_ad
            ))
            return cursor.lastrowid
    
    def update_content_analysis(self, content_id: int, importance_score: int, 
                              category: str, explanation: str):
        """Обновление анализа контента"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE content 
                SET importance_score = ?, category = ?, explanation = ?
                WHERE id = ?
            """, (importance_score, category, explanation, content_id))
    
    def get_recent_content(self, hours: int = 24) -> List[ParsedContent]:
        """Получение контента за последние N часов"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM content 
                WHERE published_at >= ? AND is_duplicate = 0
                ORDER BY published_at DESC
            """, (cutoff_time,)).fetchall()
            
            return [ParsedContent(
                id=row["id"],
                source_id=row["source_id"],
                source_name=row["source_name"],
                title=row["title"],
                content=row["content"],
                url=row["url"],
                published_at=datetime.fromisoformat(row["published_at"]),
                processed_at=datetime.fromisoformat(row["processed_at"]) if row["processed_at"] else None,
                is_duplicate=bool(row["is_duplicate"]),
                is_ad=bool(row["is_ad"])
            ) for row in rows]
    
    def get_analyzed_content(self, hours: int = 24, min_importance: int = 0) -> List[AnalyzedContent]:
        """Получение проанализированного контента"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM content 
                WHERE published_at >= ? 
                AND is_duplicate = 0 
                AND importance_score IS NOT NULL
                AND importance_score >= ?
                ORDER BY importance_score DESC, published_at DESC
            """, (cutoff_time, min_importance)).fetchall()
            
            return [AnalyzedContent(
                id=row["id"],
                source_id=row["source_id"],
                source_name=row["source_name"],
                title=row["title"],
                content=row["content"],
                url=row["url"],
                published_at=datetime.fromisoformat(row["published_at"]),
                importance_score=row["importance_score"],
                category=row["category"],
                explanation=row["explanation"],
                processed_at=datetime.fromisoformat(row["processed_at"]) if row["processed_at"] else None
            ) for row in rows]
    
    def save_digest(self, digest: Digest) -> int:
        """Сохранение дайджеста"""
        content_json = json.dumps({
            "top_items": [item.__dict__ for item in digest.top_items],
            "other_items": [item.__dict__ for item in digest.other_items]
        }, ensure_ascii=False, default=str)
        
        insights_json = json.dumps(digest.insights, ensure_ascii=False)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO digests (user_id, title, content, insights, created_at, sent_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                digest.user_id, digest.title, content_json, insights_json,
                digest.created_at, digest.sent_at
            ))
            return cursor.lastrowid
    
    def save_metrics(self, metrics: ProcessingMetrics) -> int:
        """Сохранение метрик"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO metrics 
                (digest_id, processing_time, sources_count, raw_items_count, 
                 processed_items_count, top_items_count, errors_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.digest_id, metrics.processing_time, metrics.sources_count,
                metrics.raw_items_count, metrics.processed_items_count,
                metrics.top_items_count, metrics.errors_count, metrics.created_at
            ))
            return cursor.lastrowid
    
    def cleanup_old_content(self, days: int = 7):
        """Очистка старого контента"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM content WHERE published_at < ?",
                (cutoff_time,)
            )
            deleted_count = cursor.rowcount
            
        logger.info("Cleaned up old content", deleted_count=deleted_count)
        return deleted_count
    
    def check_duplicate(self, title: str, source_id: int, hours: int = 24) -> bool:
        """Проверка на дубликат"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT COUNT(*) FROM content 
                WHERE title = ? AND source_id = ? AND published_at >= ?
            """, (title, source_id, cutoff_time)).fetchone()
            
            return result[0] > 0 