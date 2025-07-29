import sqlite3
from datetime import datetime, timedelta
import random
from uuid import uuid4

def create_database():
    conn = sqlite3.connect('client_exploration.db')
    cursor = conn.cursor()
    
    # Create client_mapping table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS client_mapping (
            account_id TEXT PRIMARY KEY,
            client_name TEXT NOT NULL,
            client_id TEXT NOT NULL
        )
    ''')
    
    # Create account_balances table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_balances (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            fund_name TEXT NOT NULL,
            balance_date DATE NOT NULL,
            balance DECIMAL(15,2) NOT NULL,
            FOREIGN KEY (account_id) REFERENCES client_mapping(account_id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_balances_date ON account_balances(balance_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_account_balances_account ON account_balances(account_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_client_mapping_client ON client_mapping(client_id)')
    
    conn.commit()
    conn.close()

def generate_sample_data():
    conn = sqlite3.connect('client_exploration.db')
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute('DELETE FROM account_balances')
    cursor.execute('DELETE FROM client_mapping')
    
    # Sample clients and funds
    clients = [
        'Acme Corporation', 'Global Trade Inc', 'Tech Innovations LLC', 
        'Financial Solutions Ltd', 'Investment Partners Corp', 'Growth Ventures Inc',
        'Capital Management', 'Wealth Advisors LLC', 'Strategic Investments',
        'Portfolio Management Inc'
    ]
    
    funds = [
        'Government Money Market', 'Prime Money Market', 'Treasury Fund',
        'Municipal Money Market', 'Corporate Bond Fund', 'Institutional Fund'
    ]
    
    # Generate client mapping and fund allocations
    account_client_map = {}
    account_fund_map = {}  # Track which funds each account invests in
    
    for i, client in enumerate(clients):
        client_id = str(uuid4())
        num_accounts = random.randint(2, 5)
        
        for j in range(num_accounts):
            account_id = f"{client[:3].upper()}-{i:03d}-{j:03d}"
            cursor.execute(
                'INSERT INTO client_mapping (account_id, client_name, client_id) VALUES (?, ?, ?)',
                (account_id, client, client_id)
            )
            account_client_map[account_id] = client
            
            # Assign 1-3 funds to this account (will stay consistent throughout time)
            num_funds = random.randint(1, 3)
            selected_funds = random.sample(funds, num_funds)
            account_fund_map[account_id] = selected_funds
    
    # Generate balance data for the last 3 years (1095 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*3)
    
    accounts = list(account_client_map.keys())
    
    # Generate initial balances for each account-fund combination
    initial_balances = {}
    for account_id in accounts:
        for fund in account_fund_map[account_id]:
            initial_balances[(account_id, fund)] = {
                'base': random.uniform(500000, 5000000),
                'growth_rate': random.uniform(0.02, 0.05) / 365,  # 2-5% annual
            }
    
    # Generate balances
    current_date = start_date
    while current_date <= end_date:
        for account_id in accounts:
            # Use the pre-assigned funds for this account
            for fund in account_fund_map[account_id]:
                # Generate realistic balance with some growth
                days_elapsed = (current_date - start_date).days
                base_info = initial_balances[(account_id, fund)]
                volatility = random.uniform(-0.001, 0.001)  # Daily volatility
                
                balance = base_info['base'] * (1 + base_info['growth_rate'] * days_elapsed) * (1 + volatility)
                
                cursor.execute('''
                    INSERT INTO account_balances (id, account_id, fund_name, balance_date, balance)
                    VALUES (?, ?, ?, ?, ?)
                ''', (str(uuid4()), account_id, fund, current_date.strftime('%Y-%m-%d'), round(balance, 2)))
        
        current_date += timedelta(days=1)
    
    conn.commit()
    conn.close()
    print("Sample data generated successfully!")

if __name__ == '__main__':
    create_database()
    generate_sample_data()