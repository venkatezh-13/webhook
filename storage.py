from datetime import datetime, timezone
import sqlite3
import hashlib
import json
from typing import Optional, List, Dict, Any

class AlertStorage:
    """
    SQLite persistence store to track processed alerts and prevent duplicates.
    """

    def __init__(self, db_path: str = "alerts_history.db"):
        self.db_path = db_path
        self._persistent_conn = sqlite3.connect(":memory:") if db_path == ":memory:" else None
        self._init_db()

    def _get_connection(self):
        if self._persistent_conn:
            return self._persistent_conn
        return sqlite3.connect(self.db_path)


    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts_history (
                    alert_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    matched_keywords TEXT,
                    channels_sent TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    @staticmethod
    def generate_hash(title: str, content: str = "") -> str:
        """Generates MD5 hash derived from title and content for deduplication."""
        raw = f"{title.strip().lower()}|{content.strip().lower()}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def is_duplicate(self, alert_id: str) -> bool:
        """Checks if an alert ID or hash has already been processed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM alerts_history WHERE alert_id = ?", (alert_id,))
            return cursor.fetchone() is not None

    def save_alert(
        self,
        alert_id: str,
        title: str,
        content: str = "",
        matched_keywords: Optional[List[str]] = None,
        channels_sent: Optional[List[str]] = None
    ):
        """Records a processed alert into SQLite storage."""
        matched_json = json.dumps(matched_keywords or [])
        channels_json = json.dumps(channels_sent or [])
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO alerts_history
                (alert_id, title, content, matched_keywords, channels_sent, processed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert_id,
                title,
                content,
                matched_json,
                channels_json,
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()


    def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns the most recent processed alerts."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT alert_id, title, content, matched_keywords, channels_sent, processed_at
                FROM alerts_history
                ORDER BY processed_at DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            results = []
            for r in rows:
                results.append({
                    "alert_id": r["alert_id"],
                    "title": r["title"],
                    "content": r["content"],
                    "matched_keywords": json.loads(r["matched_keywords"] or "[]"),
                    "channels_sent": json.loads(r["channels_sent"] or "[]"),
                    "processed_at": r["processed_at"]
                })
            return results
