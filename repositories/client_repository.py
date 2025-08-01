"""Repository for client-related data access."""
from typing import Dict, List, Optional
from .base import BaseRepository


class ClientRepository(BaseRepository):
    """Repository for client data operations."""
    
    def get_all_clients(self) -> List[Dict]:
        """Get all unique clients."""
        sql = """
        SELECT DISTINCT 
            cm.client_id,
            cm.client_name
        FROM client_mapping cm
        ORDER BY cm.client_name
        """
        return self.execute_query(sql)
    
    def get_client_by_id(self, client_id: str) -> Optional[Dict]:
        """Get a single client by ID."""
        sql = """
        SELECT DISTINCT 
            cm.client_id,
            cm.client_name
        FROM client_mapping cm
        WHERE cm.client_id = :client_id
        """
        results = self.execute_query(sql, {"client_id": client_id})
        return results[0] if results else None
    
    def get_client_accounts(self, client_id: str) -> List[Dict]:
        """Get all accounts for a specific client."""
        sql = """
        SELECT 
            account_id,
            client_name,
            client_id
        FROM client_mapping
        WHERE client_id = :client_id
        ORDER BY account_id
        """
        return self.execute_query(sql, {"client_id": client_id})
    
    def get_client_current_balance(self, client_id: str, date: Optional[str] = None) -> float:
        """Get total current balance for a client."""
        date_condition = "AND ab.balance_date = :date" if date else """
            AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
        """
        
        sql = f"""
        SELECT 
            COALESCE(SUM(ab.balance), 0) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        WHERE cm.client_id = :client_id
        {date_condition}
        """
        
        params = {"client_id": client_id}
        if date:
            params["date"] = date
            
        return self.execute_scalar(sql, params) or 0
    
    def get_clients_with_current_balances(self, client_ids: Optional[List[str]] = None, 
                                         date: Optional[str] = None) -> List[Dict]:
        """Get clients with their current total balances."""
        filters = {}
        if client_ids:
            filters["cm.client_id"] = client_ids
            
        where_clause, params = self.build_where_clause(filters)
        
        date_condition = "AND ab.balance_date = :date" if date else """
            AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
        """
        if date:
            params["date"] = date
        
        sql = f"""
        SELECT 
            cm.client_id,
            cm.client_name,
            COALESCE(SUM(ab.balance), 0) as total_balance
        FROM client_mapping cm
        LEFT JOIN account_balances ab ON cm.account_id = ab.account_id
        {where_clause}
        {date_condition}
        GROUP BY cm.client_id, cm.client_name
        ORDER BY cm.client_name
        """
        
        return self.execute_query(sql, params)