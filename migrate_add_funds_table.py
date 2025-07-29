#!/usr/bin/env python3
"""
Migration script to add funds table to existing database
"""
import sqlite3

def migrate_database():
    conn = sqlite3.connect('client_exploration.db')
    cursor = conn.cursor()
    
    # Check if funds table already exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='funds'
    """)
    
    if cursor.fetchone() is not None:
        print("Funds table already exists. Skipping migration.")
        conn.close()
        return
    
    print("Creating funds table...")
    
    # Create funds table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funds (
            fund_name TEXT PRIMARY KEY,
            fund_ticker TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Fund tickers mapping
    fund_tickers = {
        'Government Money Market': 'GMMF',
        'Prime Money Market': 'PMMF',
        'Treasury Fund': 'TRSF',
        'Municipal Money Market': 'MUNF',
        'Corporate Bond Fund': 'CBND',
        'Institutional Fund': 'INST'
    }
    
    # Insert fund data
    for fund_name, ticker in fund_tickers.items():
        try:
            cursor.execute(
                'INSERT INTO funds (fund_name, fund_ticker) VALUES (?, ?)',
                (fund_name, ticker)
            )
            print(f"Added fund: {fund_name} ({ticker})")
        except sqlite3.IntegrityError:
            print(f"Fund already exists: {fund_name}")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == '__main__':
    migrate_database()