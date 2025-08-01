#!/usr/bin/env python3
"""
Cache warming script for the Client Exploration Tool.
Run this after nightly data updates to pre-compute common queries.
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from services.dashboard_service import DashboardService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CacheWarmer:
    def __init__(self, db_path="client_exploration.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.service = DashboardService(db_path)
        
    def setup_cache_tables(self):
        """Create cache tables if they don't exist."""
        logger.info("Setting up cache tables...")
        with open('cache_tables.sql', 'r') as f:
            self.conn.executescript(f.read())
        self.conn.commit()
        
    def get_latest_date(self):
        """Get the latest date in the database."""
        cursor = self.conn.execute("SELECT MAX(balance_date) FROM account_balances")
        return cursor.fetchone()[0]
        
    def clear_old_cache(self, as_of_date):
        """Clear old cache entries for the given date."""
        logger.info(f"Clearing old cache for date: {as_of_date}")
        tables = [
            'cached_overview',
            'cached_client_balances', 
            'cached_fund_balances',
            'cached_account_details',
            'cached_chart_data'
        ]
        for table in tables:
            self.conn.execute(f"DELETE FROM {table} WHERE as_of_date = ?", (as_of_date,))
        self.conn.commit()
        
    def warm_overview_cache(self, as_of_date):
        """Cache overview data (no filters)."""
        logger.info("Warming overview cache...")
        data = self.service.get_dashboard_data(date=as_of_date, include_charts=False)
        
        # Extract KPI metrics
        kpi = data['kpi_metrics']
        
        # Calculate average YTD growth
        ytd_sum = 0
        ytd_count = 0
        for client in data['client_balances']:
            if client['ytd_change'] is not None:
                ytd_sum += client['ytd_change']
                ytd_count += 1
        avg_ytd = ytd_sum / ytd_count if ytd_count > 0 else 0
        
        # Insert into cache
        self.conn.execute("""
            INSERT INTO cached_overview (
                cache_key, as_of_date, total_clients, total_funds, 
                total_accounts, total_aum, aum_30d_ago, aum_30d_change, avg_ytd_growth
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'overview', as_of_date, kpi['active_clients'], kpi['active_funds'],
            kpi['active_accounts'], kpi['total_aum'], kpi.get('balance_30d_ago', 0),
            kpi.get('change_30d', 0), avg_ytd
        ))
        
    def warm_client_balances_cache(self, as_of_date):
        """Cache client balances with QTD/YTD."""
        logger.info("Warming client balances cache...")
        data = self.service.get_dashboard_data(date=as_of_date, include_charts=False)
        
        for client in data['client_balances']:
            self.conn.execute("""
                INSERT INTO cached_client_balances (
                    client_id, as_of_date, client_name, total_balance, qtd_change, ytd_change
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                client['client_id'], as_of_date, client['client_name'],
                client['total_balance'], client['qtd_change'], client['ytd_change']
            ))
            
    def warm_fund_balances_cache(self, as_of_date):
        """Cache fund balances with QTD/YTD."""
        logger.info("Warming fund balances cache...")
        data = self.service.get_dashboard_data(date=as_of_date, include_charts=False)
        
        for fund in data['fund_balances']:
            self.conn.execute("""
                INSERT INTO cached_fund_balances (
                    fund_name, as_of_date, fund_ticker, total_balance, qtd_change, ytd_change
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                fund['fund_name'], as_of_date, fund['fund_ticker'],
                fund['total_balance'], fund['qtd_change'], fund['ytd_change']
            ))
            
    def warm_account_details_cache(self, as_of_date):
        """Cache account details with QTD/YTD."""
        logger.info("Warming account details cache...")
        data = self.service.get_dashboard_data(date=as_of_date, include_charts=False)
        
        for account in data['account_details']:
            self.conn.execute("""
                INSERT INTO cached_account_details (
                    account_id, as_of_date, client_id, client_name, balance, qtd_change, ytd_change
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                account['account_id'], as_of_date, account['client_id'],
                account['client_name'], account['balance'], 
                account['qtd_change'], account['ytd_change']
            ))
            
    def warm_chart_data_cache(self, as_of_date):
        """Cache chart data for 90-day and 3-year views."""
        logger.info("Warming chart data cache...")
        data = self.service.get_dashboard_data(date=as_of_date, include_charts=True)
        
        # Cache 90-day chart data
        for point in data['charts']['recent_history']:
            self.conn.execute("""
                INSERT INTO cached_chart_data (cache_key, as_of_date, data_date, balance)
                VALUES (?, ?, ?, ?)
            """, ('chart_90d', as_of_date, point['date'], point['balance']))
            
        # Cache 3-year chart data
        for point in data['charts']['long_term_history']:
            self.conn.execute("""
                INSERT INTO cached_chart_data (cache_key, as_of_date, data_date, balance)
                VALUES (?, ?, ?, ?)
            """, ('chart_3y', as_of_date, point['date'], point['balance']))
            
    def warm_all_caches(self):
        """Warm all caches for the latest date."""
        try:
            # Get latest date
            as_of_date = self.get_latest_date()
            logger.info(f"Warming caches for date: {as_of_date}")
            
            # Clear old cache for this date
            self.clear_old_cache(as_of_date)
            
            # Warm each cache
            self.warm_overview_cache(as_of_date)
            self.warm_client_balances_cache(as_of_date)
            self.warm_fund_balances_cache(as_of_date)
            self.warm_account_details_cache(as_of_date)
            self.warm_chart_data_cache(as_of_date)
            
            # Commit all changes
            self.conn.commit()
            logger.info("Cache warming completed successfully!")
            
            # Show cache statistics
            self.show_cache_stats(as_of_date)
            
        except Exception as e:
            logger.error(f"Error warming cache: {e}")
            self.conn.rollback()
            raise
            
    def show_cache_stats(self, as_of_date):
        """Display cache statistics."""
        stats = []
        
        # Count cached entries
        tables = [
            ('cached_overview', 'overview entries'),
            ('cached_client_balances', 'client entries'),
            ('cached_fund_balances', 'fund entries'),
            ('cached_account_details', 'account entries'),
            ('cached_chart_data', 'chart data points')
        ]
        
        for table, desc in tables:
            cursor = self.conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE as_of_date = ?", 
                (as_of_date,)
            )
            count = cursor.fetchone()[0]
            stats.append(f"{desc}: {count}")
            
        logger.info("Cache statistics:")
        for stat in stats:
            logger.info(f"  - {stat}")
            
    def close(self):
        """Close database connection."""
        self.conn.close()
        

if __name__ == "__main__":
    warmer = CacheWarmer()
    try:
        warmer.setup_cache_tables()
        warmer.warm_all_caches()
    finally:
        warmer.close()