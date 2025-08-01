"""Base repository class for data access layer."""
import sqlite3
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common database operations."""
    
    def __init__(self, db_path: str = "client_exploration.db"):
        self.db_path = db_path
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def execute_scalar(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a query and return a single scalar value."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def build_where_clause(self, filters: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Build WHERE clause from filters dict."""
        if not filters:
            return "", {}
        
        conditions = []
        params = {}
        
        for key, value in filters.items():
            if value is not None:
                if isinstance(value, list):
                    placeholders = ", ".join([f":_{key}_{i}" for i in range(len(value))])
                    conditions.append(f"{key} IN ({placeholders})")
                    for i, v in enumerate(value):
                        params[f"_{key}_{i}"] = v
                else:
                    conditions.append(f"{key} = :{key}")
                    params[key] = value
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, params