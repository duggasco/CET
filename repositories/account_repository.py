"""Repository for account-related data access."""
from typing import Dict, List, Optional
from .base import BaseRepository


class AccountRepository(BaseRepository):
    """Repository for account data operations."""
    
    def get_account_by_id(self, account_id: str) -> Optional[Dict]:
        """Get account details by ID."""
        sql = """
        SELECT 
            cm.account_id,
            cm.client_name,
            cm.client_id
        FROM client_mapping cm
        WHERE cm.account_id = :account_id
        """
        results = self.execute_query(sql, {"account_id": account_id})
        return results[0] if results else None
    
    def get_account_current_balance(self, account_id: str, date: Optional[str] = None) -> float:
        """Get total current balance for an account across all funds."""
        date_condition = "AND balance_date = :date" if date else """
            AND balance_date = (SELECT MAX(balance_date) FROM account_balances)
        """
        
        sql = f"""
        SELECT 
            COALESCE(SUM(balance), 0) as total_balance
        FROM account_balances
        WHERE account_id = :account_id
        {date_condition}
        """
        
        params = {"account_id": account_id}
        if date:
            params["date"] = date
            
        return self.execute_scalar(sql, params) or 0
    
    def get_account_fund_balances(self, account_id: str, date: Optional[str] = None) -> List[Dict]:
        """Get fund-level balances for a specific account."""
        date_condition = "AND balance_date = :date" if date else """
            AND balance_date = (SELECT MAX(balance_date) FROM account_balances)
        """
        
        sql = f"""
        SELECT 
            fund_name,
            SUBSTR(fund_name, 1, 3) as fund_ticker,
            balance
        FROM account_balances
        WHERE account_id = :account_id
        {date_condition}
        AND balance > 0
        ORDER BY fund_name
        """
        
        params = {"account_id": account_id}
        if date:
            params["date"] = date
            
        return self.execute_query(sql, params)
    
    def get_accounts_with_balances(self, account_ids: Optional[List[str]] = None,
                                  client_ids: Optional[List[str]] = None,
                                  fund_names: Optional[List[str]] = None,
                                  date: Optional[str] = None) -> List[Dict]:
        """Get accounts with their current balances, optionally filtered."""
        # Build filters
        join_conditions = []
        where_conditions = []
        params = {}
        
        # Always need the date condition
        date_condition = "AND ab.balance_date = :date" if date else """
            AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
        """
        if date:
            params["date"] = date
        
        # Handle filters
        if account_ids:
            placeholders = ", ".join([f":_account_{i}" for i in range(len(account_ids))])
            where_conditions.append(f"ab.account_id IN ({placeholders})")
            for i, aid in enumerate(account_ids):
                params[f"_account_{i}"] = aid
        
        if client_ids:
            placeholders = ", ".join([f":_client_{i}" for i in range(len(client_ids))])
            where_conditions.append(f"cm.client_id IN ({placeholders})")
            for i, cid in enumerate(client_ids):
                params[f"_client_{i}"] = cid
        
        if fund_names:
            placeholders = ", ".join([f":_fund_{i}" for i in range(len(fund_names))])
            where_conditions.append(f"ab.fund_name IN ({placeholders})")
            for i, fname in enumerate(fund_names):
                params[f"_fund_{i}"] = fname
        
        where_clause = " AND " + " AND ".join(where_conditions) if where_conditions else ""
        
        sql = f"""
        SELECT 
            ab.account_id,
            cm.client_name,
            cm.client_id,
            SUM(ab.balance) as balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        WHERE 1=1
        {date_condition}
        {where_clause}
        GROUP BY ab.account_id, cm.client_name, cm.client_id
        HAVING SUM(ab.balance) > 0
        ORDER BY ab.account_id
        """
        
        return self.execute_query(sql, params)