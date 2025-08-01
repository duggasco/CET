"""Service layer for dashboard data aggregation and business logic."""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from repositories.base import BaseRepository
from repositories.client_repository import ClientRepository
from repositories.fund_repository import FundRepository
from repositories.account_repository import AccountRepository

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for complex dashboard data operations."""
    
    def __init__(self, db_path: str = "client_exploration.db"):
        self.db_path = db_path
        self._base_repo = BaseRepository(db_path)
        self.client_repo = ClientRepository(db_path)
        self.fund_repo = FundRepository(db_path)
        self.account_repo = AccountRepository(db_path)
    
    def get_dashboard_data(self, 
                          client_ids: Optional[List[str]] = None,
                          fund_names: Optional[List[str]] = None,
                          account_ids: Optional[List[str]] = None,
                          date: Optional[str] = None,
                          text_filters: Optional[Dict[str, str]] = None) -> Dict:
        """Get complete dashboard data with all tables and charts."""
        
        # Build filter conditions
        filters = self._build_filters(client_ids, fund_names, account_ids, text_filters)
        
        # Get the reference date
        ref_date = date or self._get_latest_date()
        
        # Get all component data
        result = {
            "metadata": {
                "as_of_date": ref_date,
                "filters_applied": {
                    "client_ids": client_ids,
                    "fund_names": fund_names,
                    "account_ids": account_ids,
                    "text_filters": text_filters
                }
            },
            "client_balances": self._get_client_balances_with_metrics(filters, ref_date),
            "fund_balances": self._get_fund_balances_with_metrics(filters, ref_date),
            "account_details": self._get_account_details_with_metrics(filters, ref_date),
            "charts": {
                "recent_history": self._get_chart_history(filters, ref_date, days=90),
                "long_term_history": self._get_chart_history(filters, ref_date, days=1095)
            },
            "kpi_metrics": self._calculate_kpi_metrics(filters, ref_date)
        }
        
        return result
    
    def _build_filters(self, client_ids: Optional[List[str]], 
                      fund_names: Optional[List[str]], 
                      account_ids: Optional[List[str]],
                      text_filters: Optional[Dict[str, str]]) -> Dict:
        """Build comprehensive filter conditions."""
        filters = {
            "client_ids": client_ids,
            "fund_names": fund_names,
            "account_ids": account_ids
        }
        
        # Apply text filters
        if text_filters:
            if text_filters.get("client_name"):
                filters["client_name_like"] = f"%{text_filters['client_name']}%"
            if text_filters.get("fund_ticker"):
                filters["fund_ticker_like"] = f"{text_filters['fund_ticker']}%"
            if text_filters.get("account_number"):
                filters["account_id_like"] = f"%{text_filters['account_number']}%"
        
        return filters
    
    def _get_latest_date(self) -> str:
        """Get the latest date in the database."""
        sql = "SELECT MAX(balance_date) FROM account_balances"
        return self._base_repo.execute_scalar(sql)
    
    def _get_client_balances_with_metrics(self, filters: Dict, ref_date: str) -> List[Dict]:
        """Get client balances with QTD/YTD metrics."""
        # Build WHERE clause for the intersection
        where_conditions, params = self._build_full_where_clause(filters)
        
        # Get quarter and year start dates
        qtd_start, ytd_start = self._get_period_start_dates(ref_date)
        params.update({
            "ref_date": ref_date,
            "qtd_start": qtd_start,
            "ytd_start": ytd_start
        })
        
        sql = f"""
        WITH current_balances AS (
            SELECT 
                cm.client_id,
                cm.client_name,
                SUM(ab.balance) as total_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.balance_date = :ref_date
            {where_conditions}
            GROUP BY cm.client_id, cm.client_name
        ),
        qtd_start_balances AS (
            SELECT 
                cm.client_id,
                SUM(ab.balance) as start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.balance_date = :qtd_start
            {where_conditions}
            GROUP BY cm.client_id
        ),
        ytd_start_balances AS (
            SELECT 
                cm.client_id,
                SUM(ab.balance) as start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.balance_date = :ytd_start
            {where_conditions}
            GROUP BY cm.client_id
        )
        SELECT 
            cb.client_id,
            cb.client_name,
            cb.total_balance,
            CASE 
                WHEN qsb.start_balance IS NULL OR qsb.start_balance = 0 THEN NULL
                ELSE ((cb.total_balance - qsb.start_balance) / qsb.start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.start_balance IS NULL OR ysb.start_balance = 0 THEN NULL
                ELSE ((cb.total_balance - ysb.start_balance) / ysb.start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.client_id = qsb.client_id
        LEFT JOIN ytd_start_balances ysb ON cb.client_id = ysb.client_id
        ORDER BY cb.client_name
        """
        
        return self._base_repo.execute_query(sql, params)
    
    def _get_fund_balances_with_metrics(self, filters: Dict, ref_date: str) -> List[Dict]:
        """Get fund balances with QTD/YTD metrics."""
        # Build WHERE clause for the intersection
        where_conditions, params = self._build_full_where_clause(filters)
        
        # Get quarter and year start dates
        qtd_start, ytd_start = self._get_period_start_dates(ref_date)
        params.update({
            "ref_date": ref_date,
            "qtd_start": qtd_start,
            "ytd_start": ytd_start
        })
        
        # Need to handle JOIN to client_mapping conditionally
        join_clause = ""
        if any(key in filters for key in ["client_ids", "client_name_like"]):
            join_clause = "JOIN client_mapping cm ON ab.account_id = cm.account_id"
        
        sql = f"""
        WITH current_balances AS (
            SELECT 
                ab.fund_name,
                SUBSTR(ab.fund_name, 1, 3) as fund_ticker,
                SUM(ab.balance) as total_balance
            FROM account_balances ab
            {join_clause}
            WHERE ab.balance_date = :ref_date
            {where_conditions}
            GROUP BY ab.fund_name
        ),
        qtd_start_balances AS (
            SELECT 
                ab.fund_name,
                SUM(ab.balance) as start_balance
            FROM account_balances ab
            {join_clause}
            WHERE ab.balance_date = :qtd_start
            {where_conditions}
            GROUP BY ab.fund_name
        ),
        ytd_start_balances AS (
            SELECT 
                ab.fund_name,
                SUM(ab.balance) as start_balance
            FROM account_balances ab
            {join_clause}
            WHERE ab.balance_date = :ytd_start
            {where_conditions}
            GROUP BY ab.fund_name
        )
        SELECT 
            cb.fund_name,
            cb.fund_ticker,
            cb.total_balance,
            CASE 
                WHEN qsb.start_balance IS NULL OR qsb.start_balance = 0 THEN NULL
                ELSE ((cb.total_balance - qsb.start_balance) / qsb.start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.start_balance IS NULL OR ysb.start_balance = 0 THEN NULL
                ELSE ((cb.total_balance - ysb.start_balance) / ysb.start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.fund_name = qsb.fund_name
        LEFT JOIN ytd_start_balances ysb ON cb.fund_name = ysb.fund_name
        ORDER BY cb.fund_name
        """
        
        return self._base_repo.execute_query(sql, params)
    
    def _get_account_details_with_metrics(self, filters: Dict, ref_date: str) -> List[Dict]:
        """Get account details with QTD/YTD metrics."""
        # Build WHERE clause for the intersection
        where_conditions, params = self._build_full_where_clause(filters)
        
        # Get quarter and year start dates
        qtd_start, ytd_start = self._get_period_start_dates(ref_date)
        params.update({
            "ref_date": ref_date,
            "qtd_start": qtd_start,
            "ytd_start": ytd_start
        })
        
        sql = f"""
        WITH current_balances AS (
            SELECT 
                ab.account_id,
                cm.client_name,
                cm.client_id,
                SUM(ab.balance) as balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.balance_date = :ref_date
            {where_conditions}
            GROUP BY ab.account_id, cm.client_name, cm.client_id
            HAVING SUM(ab.balance) > 0
        ),
        qtd_start_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.balance_date = :qtd_start
            {where_conditions}
            GROUP BY ab.account_id
        ),
        ytd_start_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.balance_date = :ytd_start
            {where_conditions}
            GROUP BY ab.account_id
        )
        SELECT 
            cb.account_id,
            cb.client_name,
            cb.client_id,
            cb.balance,
            CASE 
                WHEN qsb.start_balance IS NULL OR qsb.start_balance = 0 THEN NULL
                ELSE ((cb.balance - qsb.start_balance) / qsb.start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.start_balance IS NULL OR ysb.start_balance = 0 THEN NULL
                ELSE ((cb.balance - ysb.start_balance) / ysb.start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.account_id = qsb.account_id
        LEFT JOIN ytd_start_balances ysb ON cb.account_id = ysb.account_id
        ORDER BY cb.account_id
        """
        
        return self._base_repo.execute_query(sql, params)
    
    def _get_chart_history(self, filters: Dict, ref_date: str, days: int) -> List[Dict]:
        """Get historical balance data for charts."""
        where_conditions, params = self._build_full_where_clause(filters)
        
        # Calculate start date
        ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")
        start_dt = ref_dt - timedelta(days=days)
        
        params.update({
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": ref_date
        })
        
        # Need conditional JOIN
        join_clause = ""
        if any(key in filters for key in ["client_ids", "client_name_like"]):
            join_clause = "JOIN client_mapping cm ON ab.account_id = cm.account_id"
        
        sql = f"""
        SELECT 
            ab.balance_date as date,
            SUM(ab.balance) as balance
        FROM account_balances ab
        {join_clause}
        WHERE ab.balance_date BETWEEN :start_date AND :end_date
        {where_conditions}
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
        """
        
        return self._base_repo.execute_query(sql, params)
    
    def _calculate_kpi_metrics(self, filters: Dict, ref_date: str) -> Dict:
        """Calculate KPI metrics for the dashboard."""
        where_conditions, params = self._build_full_where_clause(filters)
        params["ref_date"] = ref_date
        
        # Need conditional JOIN
        join_clause = ""
        if any(key in filters for key in ["client_ids", "client_name_like"]):
            join_clause = "JOIN client_mapping cm ON ab.account_id = cm.account_id"
        
        # Calculate 30 days ago
        ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")
        days_30_ago = (ref_dt - timedelta(days=30)).strftime("%Y-%m-%d")
        params["days_30_ago"] = days_30_ago
        
        sql = f"""
        WITH current_metrics AS (
            SELECT 
                COUNT(DISTINCT cm.client_id) as active_clients,
                COUNT(DISTINCT ab.fund_name) as active_funds,
                COUNT(DISTINCT ab.account_id) as active_accounts,
                SUM(ab.balance) as total_aum
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.balance_date = :ref_date
            {where_conditions}
        ),
        historical_balance AS (
            SELECT 
                SUM(ab.balance) as balance_30d_ago
            FROM account_balances ab
            {join_clause}
            WHERE ab.balance_date = :days_30_ago
            {where_conditions}
        )
        SELECT 
            cm.active_clients,
            cm.active_funds,
            cm.active_accounts,
            cm.total_aum,
            hb.balance_30d_ago,
            CASE 
                WHEN hb.balance_30d_ago IS NULL OR hb.balance_30d_ago = 0 THEN 0
                ELSE ((cm.total_aum - hb.balance_30d_ago) / hb.balance_30d_ago) * 100
            END as change_30d
        FROM current_metrics cm
        CROSS JOIN historical_balance hb
        """
        
        results = self._base_repo.execute_query(sql, params)
        return results[0] if results else {
            "active_clients": 0,
            "active_funds": 0,
            "active_accounts": 0,
            "total_aum": 0,
            "balance_30d_ago": 0,
            "change_30d": 0
        }
    
    def _build_full_where_clause(self, filters: Dict) -> Tuple[str, Dict]:
        """Build comprehensive WHERE clause from all filters."""
        conditions = []
        params = {}
        
        # Handle list filters
        if filters.get("client_ids"):
            placeholders = ", ".join([f":_client_{i}" for i in range(len(filters["client_ids"]))])
            conditions.append(f"cm.client_id IN ({placeholders})")
            for i, cid in enumerate(filters["client_ids"]):
                params[f"_client_{i}"] = cid
        
        if filters.get("fund_names"):
            placeholders = ", ".join([f":_fund_{i}" for i in range(len(filters["fund_names"]))])
            conditions.append(f"ab.fund_name IN ({placeholders})")
            for i, fname in enumerate(filters["fund_names"]):
                params[f"_fund_{i}"] = fname
        
        if filters.get("account_ids"):
            placeholders = ", ".join([f":_account_{i}" for i in range(len(filters["account_ids"]))])
            conditions.append(f"ab.account_id IN ({placeholders})")
            for i, aid in enumerate(filters["account_ids"]):
                params[f"_account_{i}"] = aid
        
        # Handle text filters
        if filters.get("client_name_like"):
            conditions.append("cm.client_name LIKE :client_name_like")
            params["client_name_like"] = filters["client_name_like"]
        
        if filters.get("fund_ticker_like"):
            conditions.append("ab.fund_name LIKE :fund_ticker_like")
            params["fund_ticker_like"] = filters["fund_ticker_like"]
        
        if filters.get("account_id_like"):
            conditions.append("ab.account_id LIKE :account_id_like")
            params["account_id_like"] = filters["account_id_like"]
        
        where_clause = " AND " + " AND ".join(conditions) if conditions else ""
        return where_clause, params
    
    def _get_period_start_dates(self, ref_date: str) -> Tuple[str, str]:
        """Get quarter and year start dates for a reference date."""
        ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")
        
        # Quarter start
        quarter = (ref_dt.month - 1) // 3
        qtd_start = datetime(ref_dt.year, quarter * 3 + 1, 1)
        
        # Year start
        ytd_start = datetime(ref_dt.year, 1, 1)
        
        return qtd_start.strftime("%Y-%m-%d"), ytd_start.strftime("%Y-%m-%d")