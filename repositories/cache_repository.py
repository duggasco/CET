"""Repository for accessing cached dashboard data."""
from typing import Dict, List, Optional
from datetime import datetime
import logging

from repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CacheRepository(BaseRepository):
    """Repository for cached dashboard data."""
    
    def get_cached_overview(self, as_of_date: str) -> Optional[Dict]:
        """Get cached overview data."""
        sql = """
        SELECT * FROM cached_overview 
        WHERE cache_key = 'overview' AND as_of_date = :as_of_date
        """
        results = self.execute_query(sql, {"as_of_date": as_of_date})
        return results[0] if results else None
    
    def get_cached_client_balances(self, as_of_date: str) -> List[Dict]:
        """Get cached client balances."""
        sql = """
        SELECT client_id, client_name, total_balance, qtd_change, ytd_change
        FROM cached_client_balances
        WHERE as_of_date = :as_of_date
        ORDER BY total_balance DESC
        """
        return self.execute_query(sql, {"as_of_date": as_of_date})
    
    def get_cached_fund_balances(self, as_of_date: str) -> List[Dict]:
        """Get cached fund balances."""
        sql = """
        SELECT fund_name, fund_ticker, total_balance, qtd_change, ytd_change
        FROM cached_fund_balances
        WHERE as_of_date = :as_of_date
        ORDER BY total_balance DESC
        """
        return self.execute_query(sql, {"as_of_date": as_of_date})
    
    def get_cached_account_details(self, as_of_date: str) -> List[Dict]:
        """Get cached account details."""
        sql = """
        SELECT account_id, client_id, client_name, balance, qtd_change, ytd_change
        FROM cached_account_details
        WHERE as_of_date = :as_of_date
        ORDER BY balance DESC
        """
        return self.execute_query(sql, {"as_of_date": as_of_date})
    
    def get_cached_chart_data(self, cache_key: str, as_of_date: str) -> List[Dict]:
        """Get cached chart data."""
        sql = """
        SELECT data_date as date, balance
        FROM cached_chart_data
        WHERE cache_key = :cache_key AND as_of_date = :as_of_date
        ORDER BY data_date
        """
        return self.execute_query(sql, {
            "cache_key": cache_key,
            "as_of_date": as_of_date
        })
    
    def is_cache_valid(self, as_of_date: str) -> bool:
        """Check if cache exists for the given date."""
        sql = """
        SELECT COUNT(*) as count FROM cached_overview 
        WHERE as_of_date = :as_of_date
        """
        result = self.execute_query(sql, {"as_of_date": as_of_date})
        return result[0]['count'] > 0 if result else False
    
    def get_cache_timestamp(self, as_of_date: str) -> Optional[str]:
        """Get when the cache was created for a given date."""
        sql = """
        SELECT created_at FROM cached_overview 
        WHERE as_of_date = :as_of_date
        """
        result = self.execute_query(sql, {"as_of_date": as_of_date})
        return result[0]['created_at'] if result else None