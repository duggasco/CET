"""Repository for fund-related data access."""
from typing import Dict, List, Optional
from .base import BaseRepository


class FundRepository(BaseRepository):
    """Repository for fund data operations."""
    
    def get_all_funds(self) -> List[Dict]:
        """Get all unique funds."""
        sql = """
        SELECT DISTINCT 
            fund_name,
            SUBSTR(fund_name, 1, 3) as fund_ticker
        FROM account_balances
        ORDER BY fund_name
        """
        return self.execute_query(sql)
    
    def get_fund_by_name(self, fund_name: str) -> Optional[Dict]:
        """Get a single fund by name."""
        sql = """
        SELECT DISTINCT 
            fund_name,
            SUBSTR(fund_name, 1, 3) as fund_ticker
        FROM account_balances
        WHERE fund_name = :fund_name
        """
        results = self.execute_query(sql, {"fund_name": fund_name})
        return results[0] if results else None
    
    def get_fund_current_balance(self, fund_name: str, date: Optional[str] = None) -> float:
        """Get total current balance for a fund."""
        date_condition = "AND balance_date = :date" if date else """
            AND balance_date = (SELECT MAX(balance_date) FROM account_balances)
        """
        
        sql = f"""
        SELECT 
            COALESCE(SUM(balance), 0) as total_balance
        FROM account_balances
        WHERE fund_name = :fund_name
        {date_condition}
        """
        
        params = {"fund_name": fund_name}
        if date:
            params["date"] = date
            
        return self.execute_scalar(sql, params) or 0
    
    def get_funds_with_current_balances(self, fund_names: Optional[List[str]] = None,
                                       date: Optional[str] = None) -> List[Dict]:
        """Get funds with their current total balances."""
        filters = {}
        if fund_names:
            filters["fund_name"] = fund_names
            
        where_clause, params = self.build_where_clause(filters)
        
        date_condition = "AND balance_date = :date" if date else """
            AND balance_date = (SELECT MAX(balance_date) FROM account_balances)
        """
        if date:
            params["date"] = date
        
        # Add the date condition to WHERE clause
        if where_clause:
            where_clause += f" {date_condition}"
        else:
            where_clause = " WHERE 1=1 " + date_condition
        
        sql = f"""
        SELECT 
            fund_name,
            SUBSTR(fund_name, 1, 3) as fund_ticker,
            COALESCE(SUM(balance), 0) as total_balance
        FROM account_balances
        {where_clause}
        GROUP BY fund_name
        ORDER BY fund_name
        """
        
        return self.execute_query(sql, params)
    
    def get_fund_accounts(self, fund_name: str, date: Optional[str] = None) -> List[Dict]:
        """Get all accounts that hold a specific fund."""
        date_condition = "AND ab.balance_date = :date" if date else """
            AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
        """
        
        sql = f"""
        SELECT DISTINCT
            ab.account_id,
            cm.client_name,
            cm.client_id,
            ab.balance
        FROM account_balances ab
        LEFT JOIN client_mapping cm ON ab.account_id = cm.account_id
        WHERE ab.fund_name = :fund_name
        {date_condition}
        AND ab.balance > 0
        ORDER BY ab.account_id
        """
        
        params = {"fund_name": fund_name}
        if date:
            params["date"] = date
            
        return self.execute_query(sql, params)