from flask import Flask, jsonify, render_template, request, make_response
import sqlite3
from datetime import datetime, timedelta, date
import json
import time

app = Flask(__name__)

# Add after_request handler for cache control
@app.after_request
def add_header(response):
    # Disable caching for HTML pages
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    # Set cache for static assets (handled by query string versioning)
    elif response.content_type and ('css' in response.content_type or 'javascript' in response.content_type):
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year
    return response

def get_db_connection():
    conn = sqlite3.connect('client_exploration.db')
    conn.row_factory = sqlite3.Row
    return conn

def apply_text_filters(data_list, fund_ticker_filter='', client_name_filter='', account_number_filter=''):
    """Apply text filters to a list of data items"""
    if not fund_ticker_filter and not client_name_filter and not account_number_filter:
        return data_list
    
    filtered = []
    for item in data_list:
        match = True
        
        # Filter by fund ticker
        if fund_ticker_filter:
            fund_ticker = item.get('fund_ticker', '')
            fund_name = item.get('fund_name', '')
            if fund_ticker or fund_name:
                match = match and (
                    fund_ticker_filter.lower() in fund_ticker.lower() or
                    fund_ticker_filter.lower() in fund_name.lower()
                )
            else:
                # For account_details, we can't filter by fund since they don't have fund info
                # So we keep them all when fund filter is applied
                pass
        
        # Filter by client name
        if client_name_filter and match:
            client_name = item.get('client_name', '')
            if client_name:
                match = match and client_name_filter.lower() in client_name.lower()
            else:
                # If item has no client info but filter is specified, skip it
                match = False
        
        # Filter by account number
        if account_number_filter and match:
            account_id = item.get('account_id', '')
            if account_id:
                match = match and account_number_filter.lower() in account_id.lower()
            else:
                # If item has no account info but filter is specified, skip it
                match = False
        
        if match:
            filtered.append(item)
    
    return filtered

def get_text_filters():
    """Get text filter parameters from request"""
    return {
        'fund_ticker_filter': request.args.get('fund_ticker', '').strip(),
        'client_name_filter': request.args.get('client_name', '').strip(),
        'account_number_filter': request.args.get('account_number', '').strip()
    }

def apply_filters_to_response(data):
    """Apply text filters to all data arrays in a response"""
    filters = get_text_filters()
    
    # Only apply filters if at least one is specified
    if not any(filters.values()):
        return data
    
    # Apply filters to each data type if present
    if 'client_balances' in data:
        data['client_balances'] = apply_text_filters(data['client_balances'], **filters)
    
    if 'fund_balances' in data:
        data['fund_balances'] = apply_text_filters(data['fund_balances'], **filters)
    
    if 'account_details' in data:
        data['account_details'] = apply_text_filters(data['account_details'], **filters)
    
    return data

@app.route('/')
def index():
    # Generate cache bust parameter based on current timestamp
    cache_bust = int(time.time())
    return render_template('index.html', cache_bust=cache_bust)

@app.route('/api/overview')
def get_overview():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    
    # Get aggregated balance over time for different periods
    end_date = (datetime.now() - timedelta(days=1)).date()  # Yesterday
    
    # 90-day history for recent chart
    start_date_90 = end_date - timedelta(days=90)
    query_90 = '''
        SELECT 
            balance_date,
            SUM(balance) as total_balance
        FROM account_balances
        WHERE balance_date >= ? AND balance_date <= ?
        GROUP BY balance_date
        ORDER BY balance_date
    '''
    cursor.execute(query_90, (start_date_90.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    recent_history = [dict(row) for row in cursor.fetchall()]
    
    # 3-year history for long-term chart
    start_date_3y = end_date - timedelta(days=365*3)
    query_3y = '''
        SELECT 
            balance_date,
            SUM(balance) as total_balance
        FROM account_balances
        WHERE balance_date >= ? AND balance_date <= ?
        GROUP BY balance_date
        ORDER BY balance_date
    '''
    cursor.execute(query_3y, (start_date_3y.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    long_term_history = [dict(row) for row in cursor.fetchall()]
    
    # Calculate QTD and YTD start dates
    today = end_date
    current_quarter = (today.month - 1) // 3
    qtd_start = date(today.year, current_quarter * 3 + 1, 1)
    ytd_start = date(today.year, 1, 1)
    
    # Get client aggregated balances with QTD and YTD changes
    query = '''
        WITH current_balances AS (
            SELECT 
                cm.client_name,
                cm.client_id,
                SUM(ab.balance) as current_balance
            FROM client_mapping cm
            JOIN account_balances ab ON cm.account_id = ab.account_id
            WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            GROUP BY cm.client_name, cm.client_id
        ),
        qtd_start_balances AS (
            SELECT 
                cm.client_id,
                SUM(ab.balance) as qtd_start_balance
            FROM client_mapping cm
            JOIN account_balances ab ON cm.account_id = ab.account_id
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY cm.client_id
        ),
        ytd_start_balances AS (
            SELECT 
                cm.client_id,
                SUM(ab.balance) as ytd_start_balance
            FROM client_mapping cm
            JOIN account_balances ab ON cm.account_id = ab.account_id
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY cm.client_id
        )
        SELECT 
            cb.client_name,
            cb.client_id,
            cb.current_balance as total_balance,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.client_id = qsb.client_id
        LEFT JOIN ytd_start_balances ysb ON cb.client_id = ysb.client_id
        ORDER BY cb.current_balance DESC
    '''
    
    cursor.execute(query, (qtd_start.strftime('%Y-%m-%d'), ytd_start.strftime('%Y-%m-%d')))
    client_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get fund aggregated balances with QTD and YTD changes
    query = '''
        WITH current_balances AS (
            SELECT 
                ab.fund_name,
                f.fund_ticker,
                SUM(ab.balance) as current_balance,
                COUNT(DISTINCT ab.account_id) as account_count
            FROM account_balances ab
            LEFT JOIN funds f ON ab.fund_name = f.fund_name
            WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            GROUP BY ab.fund_name, f.fund_ticker
        ),
        qtd_start_balances AS (
            SELECT 
                fund_name,
                SUM(balance) as qtd_start_balance
            FROM account_balances
            WHERE balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY fund_name
        ),
        ytd_start_balances AS (
            SELECT 
                fund_name,
                SUM(balance) as ytd_start_balance
            FROM account_balances
            WHERE balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY fund_name
        )
        SELECT 
            cb.fund_name,
            cb.fund_ticker,
            cb.current_balance as total_balance,
            cb.account_count,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.fund_name = qsb.fund_name
        LEFT JOIN ytd_start_balances ysb ON cb.fund_name = ysb.fund_name
        ORDER BY cb.current_balance DESC
    '''
    
    cursor.execute(query, (qtd_start.strftime('%Y-%m-%d'), ytd_start.strftime('%Y-%m-%d')))
    fund_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get account details with QTD and YTD - aggregated at account level
    query = '''
        WITH current_balances AS (
            SELECT 
                ab.account_id,
                cm.client_name,
                SUM(ab.balance) as current_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            GROUP BY ab.account_id, cm.client_name
        ),
        qtd_start_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as qtd_start_balance
            FROM account_balances ab
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY ab.account_id
        ),
        ytd_start_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as ytd_start_balance
            FROM account_balances ab
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY ab.account_id
        )
        SELECT 
            cb.account_id,
            cb.client_name,
            cb.current_balance as total_balance,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.account_id = qsb.account_id
        LEFT JOIN ytd_start_balances ysb ON cb.account_id = ysb.account_id
        ORDER BY cb.current_balance DESC
    '''
    
    cursor.execute(query, (qtd_start.strftime('%Y-%m-%d'), ytd_start.strftime('%Y-%m-%d')))
    account_details = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Build response and apply filters
    response_data = {
        'recent_history': recent_history,
        'long_term_history': long_term_history,
        'client_balances': client_balances,
        'fund_balances': fund_balances,
        'account_details': account_details
    }
    
    return jsonify(apply_filters_to_response(response_data))

@app.route('/api/client/<client_id>')
def get_client_data(client_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    
    # Get client balance history for different periods
    end_date = (datetime.now() - timedelta(days=1)).date()  # Yesterday
    
    # 90-day history
    start_date_90 = end_date - timedelta(days=90)
    query_90 = '''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        WHERE cm.client_id = ? AND ab.balance_date >= ? AND ab.balance_date <= ?
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    cursor.execute(query_90, (client_id, start_date_90.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    recent_history = [dict(row) for row in cursor.fetchall()]
    
    # 3-year history
    start_date_3y = end_date - timedelta(days=365*3)
    query_3y = '''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        WHERE cm.client_id = ? AND ab.balance_date >= ? AND ab.balance_date <= ?
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    cursor.execute(query_3y, (client_id, start_date_3y.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    long_term_history = [dict(row) for row in cursor.fetchall()]
    
    # Calculate QTD and YTD start dates
    today = end_date
    current_quarter = (today.month - 1) // 3
    qtd_start = date(today.year, current_quarter * 3 + 1, 1)
    ytd_start = date(today.year, 1, 1)
    
    # Get client's fund balances with QTD and YTD
    query = '''
        WITH current_balances AS (
            SELECT 
                ab.fund_name,
                f.fund_ticker,
                SUM(ab.balance) as current_balance,
                COUNT(DISTINCT ab.account_id) as account_count
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            LEFT JOIN funds f ON ab.fund_name = f.fund_name
            WHERE cm.client_id = ? AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            GROUP BY ab.fund_name, f.fund_ticker
        ),
        qtd_start_balances AS (
            SELECT 
                ab.fund_name,
                SUM(ab.balance) as qtd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY ab.fund_name
        ),
        ytd_start_balances AS (
            SELECT 
                ab.fund_name,
                SUM(ab.balance) as ytd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY ab.fund_name
        )
        SELECT 
            cb.fund_name,
            cb.fund_ticker,
            cb.current_balance as total_balance,
            cb.account_count,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.fund_name = qsb.fund_name
        LEFT JOIN ytd_start_balances ysb ON cb.fund_name = ysb.fund_name
        ORDER BY cb.current_balance DESC
    '''
    
    cursor.execute(query, (client_id, client_id, qtd_start.strftime('%Y-%m-%d'), client_id, ytd_start.strftime('%Y-%m-%d')))
    fund_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get client's account details with QTD and YTD - aggregated at account level
    query = '''
        WITH current_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as current_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            GROUP BY ab.account_id
        ),
        qtd_start_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as qtd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY ab.account_id
        ),
        ytd_start_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as ytd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY ab.account_id
        )
        SELECT 
            cb.account_id,
            cb.current_balance as total_balance,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.account_id = qsb.account_id
        LEFT JOIN ytd_start_balances ysb ON cb.account_id = ysb.account_id
        ORDER BY cb.current_balance DESC
    '''
    
    cursor.execute(query, (client_id, client_id, qtd_start.strftime('%Y-%m-%d'), client_id, ytd_start.strftime('%Y-%m-%d')))
    account_details = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Build response and apply filters
    response_data = {
        'recent_history': recent_history,
        'long_term_history': long_term_history,
        'fund_balances': fund_balances,
        'account_details': account_details
    }
    
    return jsonify(apply_filters_to_response(response_data))

@app.route('/api/fund/<fund_name>')
def get_fund_data(fund_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    
    # Get fund balance history for different periods
    end_date = (datetime.now() - timedelta(days=1)).date()  # Yesterday
    
    # 90-day history
    start_date_90 = end_date - timedelta(days=90)
    query_90 = '''
        SELECT 
            balance_date,
            SUM(balance) as total_balance
        FROM account_balances
        WHERE fund_name = ? AND balance_date >= ? AND balance_date <= ?
        GROUP BY balance_date
        ORDER BY balance_date
    '''
    cursor.execute(query_90, (fund_name, start_date_90.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    recent_history = [dict(row) for row in cursor.fetchall()]
    
    # 3-year history
    start_date_3y = end_date - timedelta(days=365*3)
    query_3y = '''
        SELECT 
            balance_date,
            SUM(balance) as total_balance
        FROM account_balances
        WHERE fund_name = ? AND balance_date >= ? AND balance_date <= ?
        GROUP BY balance_date
        ORDER BY balance_date
    '''
    cursor.execute(query_3y, (fund_name, start_date_3y.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    long_term_history = [dict(row) for row in cursor.fetchall()]
    
    # Calculate QTD and YTD start dates
    today = end_date
    current_quarter = (today.month - 1) // 3
    qtd_start = date(today.year, current_quarter * 3 + 1, 1)
    ytd_start = date(today.year, 1, 1)
    
    # Get client balances for this fund with QTD and YTD
    query = '''
        WITH current_balances AS (
            SELECT 
                cm.client_name,
                cm.client_id,
                SUM(ab.balance) as current_balance,
                COUNT(DISTINCT ab.account_id) as account_count
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.fund_name = ? AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            GROUP BY cm.client_name, cm.client_id
        ),
        qtd_start_balances AS (
            SELECT 
                cm.client_id,
                SUM(ab.balance) as qtd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.fund_name = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY cm.client_id
        ),
        ytd_start_balances AS (
            SELECT 
                cm.client_id,
                SUM(ab.balance) as ytd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.fund_name = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY cm.client_id
        )
        SELECT 
            cb.client_name,
            cb.client_id,
            cb.current_balance as total_balance,
            cb.account_count,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.client_id = qsb.client_id
        LEFT JOIN ytd_start_balances ysb ON cb.client_id = ysb.client_id
        ORDER BY cb.current_balance DESC
    '''
    
    cursor.execute(query, (fund_name, fund_name, qtd_start.strftime('%Y-%m-%d'), fund_name, ytd_start.strftime('%Y-%m-%d')))
    client_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get account details for this fund with QTD and YTD
    query = '''
        WITH current_balances AS (
            SELECT 
                ab.account_id,
                cm.client_name,
                ab.balance as current_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.fund_name = ? AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
        ),
        qtd_start_balances AS (
            SELECT 
                ab.account_id,
                ab.balance as qtd_start_balance
            FROM account_balances ab
            WHERE ab.fund_name = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
        ),
        ytd_start_balances AS (
            SELECT 
                ab.account_id,
                ab.balance as ytd_start_balance
            FROM account_balances ab
            WHERE ab.fund_name = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
        )
        SELECT 
            cb.account_id,
            cb.client_name,
            cb.current_balance as balance,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.account_id = qsb.account_id
        LEFT JOIN ytd_start_balances ysb ON cb.account_id = ysb.account_id
        ORDER BY cb.client_name, cb.account_id
    '''
    
    cursor.execute(query, (fund_name, fund_name, qtd_start.strftime('%Y-%m-%d'), fund_name, ytd_start.strftime('%Y-%m-%d')))
    account_details = [dict(row) for row in cursor.fetchall()]
    
    # Get fund info with ticker
    cursor.execute('SELECT fund_name, fund_ticker FROM funds WHERE fund_name = ?', (fund_name,))
    fund_row = cursor.fetchone()
    fund_info = dict(fund_row) if fund_row else {'fund_name': fund_name, 'fund_ticker': None}
    
    conn.close()
    
    # Build response and apply filters
    response_data = {
        'fund_info': fund_info,
        'recent_history': recent_history,
        'long_term_history': long_term_history,
        'client_balances': client_balances,
        'account_details': account_details
    }
    
    return jsonify(apply_filters_to_response(response_data))

@app.route('/api/account/<account_id>')
@app.route('/api/account/<account_id>/fund/<fund_name>')
def get_account_data(account_id, fund_name=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get account balance history for different periods
    end_date = (datetime.now() - timedelta(days=1)).date()  # Yesterday
    
    # Build fund filter clause
    fund_filter = " AND fund_name = ?" if fund_name else ""
    fund_params = [fund_name] if fund_name else []
    
    # 90-day history
    start_date_90 = end_date - timedelta(days=90)
    query_90 = f'''
        SELECT 
            balance_date,
            fund_name,
            balance
        FROM account_balances
        WHERE account_id = ? AND balance_date >= ? AND balance_date <= ?
              {fund_filter}
        ORDER BY balance_date, fund_name
    '''
    params_90 = [account_id, start_date_90.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')] + fund_params
    cursor.execute(query_90, params_90)
    results_90 = cursor.fetchall()
    
    # Group by date for recent history
    balance_by_date_90 = {}
    for row in results_90:
        date = row['balance_date']
        if date not in balance_by_date_90:
            balance_by_date_90[date] = {'balance_date': date, 'total_balance': 0}
        balance_by_date_90[date]['total_balance'] += row['balance']
    recent_history = list(balance_by_date_90.values())
    
    # 3-year history
    start_date_3y = end_date - timedelta(days=365*3)
    query_3y = f'''
        SELECT 
            balance_date,
            fund_name,
            balance
        FROM account_balances
        WHERE account_id = ? AND balance_date >= ? AND balance_date <= ?
              {fund_filter}
        ORDER BY balance_date, fund_name
    '''
    params_3y = [account_id, start_date_3y.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')] + fund_params
    cursor.execute(query_3y, params_3y)
    results_3y = cursor.fetchall()
    
    # Group by date for long-term history
    balance_by_date_3y = {}
    for row in results_3y:
        date = row['balance_date']
        if date not in balance_by_date_3y:
            balance_by_date_3y[date] = {'balance_date': date, 'total_balance': 0}
        balance_by_date_3y[date]['total_balance'] += row['balance']
    long_term_history = list(balance_by_date_3y.values())
    
    # Get current fund allocation
    query = f'''
        SELECT 
            fund_name,
            balance
        FROM account_balances
        WHERE account_id = ? AND balance_date = (SELECT MAX(balance_date) FROM account_balances)
              {fund_filter}
        ORDER BY balance DESC
    '''
    
    params = [account_id] + fund_params
    cursor.execute(query, params)
    fund_allocation = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Build response and apply filters
    response_data = {
        'recent_history': recent_history,
        'long_term_history': long_term_history,
        'fund_allocation': fund_allocation
    }
    
    return jsonify(apply_filters_to_response(response_data))

@app.route('/api/client/<client_id>/fund/<fund_name>')
def get_client_fund_data(client_id, fund_name):
    """Get data for a specific client-fund combination"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get balance history for this client-fund combination
    end_date = (datetime.now() - timedelta(days=1)).date()
    
    # 90-day history
    start_date_90 = end_date - timedelta(days=90)
    query_90 = '''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        WHERE cm.client_id = ? AND ab.fund_name = ? 
              AND ab.balance_date >= ? AND ab.balance_date <= ?
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    cursor.execute(query_90, (client_id, fund_name, start_date_90.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    recent_history = [dict(row) for row in cursor.fetchall()]
    
    # 3-year history
    start_date_3y = end_date - timedelta(days=365*3)
    query_3y = '''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        WHERE cm.client_id = ? AND ab.fund_name = ?
              AND ab.balance_date >= ? AND ab.balance_date <= ?
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    cursor.execute(query_3y, (client_id, fund_name, start_date_3y.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    long_term_history = [dict(row) for row in cursor.fetchall()]
    
    # Get client info
    cursor.execute('SELECT client_name FROM client_mapping WHERE client_id = ? LIMIT 1', (client_id,))
    client_row = cursor.fetchone()
    client_name = dict(client_row)['client_name'] if client_row else 'Unknown'
    
    # Calculate QTD and YTD
    today = end_date
    current_quarter = (today.month - 1) // 3
    qtd_start = date(today.year, current_quarter * 3 + 1, 1)
    ytd_start = date(today.year, 1, 1)
    
    # Get fund balance with QTD and YTD for this client-fund combination
    query = '''
        WITH current_balance AS (
            SELECT 
                SUM(ab.balance) as current_balance,
                COUNT(DISTINCT ab.account_id) as account_count
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.fund_name = ? 
                  AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
        ),
        qtd_start_balance AS (
            SELECT 
                SUM(ab.balance) as qtd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.fund_name = ?
                  AND ab.balance_date = (
                      SELECT MAX(balance_date) FROM account_balances 
                      WHERE balance_date <= ?
                  )
        ),
        ytd_start_balance AS (
            SELECT 
                SUM(ab.balance) as ytd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.fund_name = ?
                  AND ab.balance_date = (
                      SELECT MAX(balance_date) FROM account_balances 
                      WHERE balance_date <= ?
                  )
        )
        SELECT 
            cb.current_balance as total_balance,
            cb.account_count,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balance cb
        CROSS JOIN qtd_start_balance qsb
        CROSS JOIN ytd_start_balance ysb
    '''
    
    cursor.execute(query, (client_id, fund_name, client_id, fund_name, qtd_start.strftime('%Y-%m-%d'), 
                          client_id, fund_name, ytd_start.strftime('%Y-%m-%d')))
    fund_data_row = cursor.fetchone()
    fund_data = dict(fund_data_row) if fund_data_row else {}
    
    # Get account details for this client-fund combination with QTD and YTD
    query = '''
        WITH current_balances AS (
            SELECT 
                ab.account_id,
                ab.balance as current_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.fund_name = ?
                  AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
        ),
        qtd_start_balances AS (
            SELECT 
                ab.account_id,
                ab.balance as qtd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.fund_name = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
        ),
        ytd_start_balances AS (
            SELECT 
                ab.account_id,
                ab.balance as ytd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE cm.client_id = ? AND ab.fund_name = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
        )
        SELECT 
            cb.account_id,
            cb.current_balance as balance,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.account_id = qsb.account_id
        LEFT JOIN ytd_start_balances ysb ON cb.account_id = ysb.account_id
        ORDER BY cb.account_id
    '''
    
    cursor.execute(query, (client_id, fund_name, client_id, fund_name, qtd_start.strftime('%Y-%m-%d'), 
                          client_id, fund_name, ytd_start.strftime('%Y-%m-%d')))
    account_details = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'recent_history': recent_history,
        'long_term_history': long_term_history,
        'client_balance': {
            'client_name': client_name,
            'client_id': client_id,
            'total_balance': fund_data.get('total_balance', 0)
        },
        'fund_balance': {
            'fund_name': fund_name,
            'total_balance': fund_data.get('total_balance', 0),
            'account_count': fund_data.get('account_count', 0),
            'qtd_change': fund_data.get('qtd_change'),
            'ytd_change': fund_data.get('ytd_change')
        },
        'account_details': [{'account_id': acc['account_id'], 
                           'client_name': client_name,
                           'fund_name': fund_name,
                           'balance': acc['balance']} for acc in account_details]
    })

@app.route('/api/date/<date_string>')
def get_date_data(date_string):
    """Get all data for a specific date"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Validate date format
    try:
        selected_date = datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Calculate QTD and YTD start dates relative to selected date
    current_quarter = (selected_date.month - 1) // 3
    qtd_start = date(selected_date.year, current_quarter * 3 + 1, 1)
    
    # If selected date is before quarter start, go to previous quarter
    if selected_date < qtd_start:
        if current_quarter == 0:
            qtd_start = date(selected_date.year - 1, 10, 1)  # Q4 of previous year
        else:
            qtd_start = date(selected_date.year, (current_quarter - 1) * 3 + 1, 1)
    
    # Get last day of previous quarter for QTD calculation
    qtd_comparison_date = qtd_start - timedelta(days=1)
    
    # YTD always starts from beginning of the year
    ytd_start = date(selected_date.year, 1, 1)
    ytd_comparison_date = date(selected_date.year - 1, 12, 31)
    
    # Get client balances for the selected date with QTD and YTD
    query = '''
        WITH current_balances AS (
            SELECT 
                cm.client_name,
                cm.client_id,
                SUM(ab.balance) as current_balance
            FROM client_mapping cm
            JOIN account_balances ab ON cm.account_id = ab.account_id
            WHERE ab.balance_date = ?
            GROUP BY cm.client_name, cm.client_id
        ),
        qtd_start_balances AS (
            SELECT 
                cm.client_id,
                SUM(ab.balance) as qtd_start_balance
            FROM client_mapping cm
            JOIN account_balances ab ON cm.account_id = ab.account_id
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY cm.client_id
        ),
        ytd_start_balances AS (
            SELECT 
                cm.client_id,
                SUM(ab.balance) as ytd_start_balance
            FROM client_mapping cm
            JOIN account_balances ab ON cm.account_id = ab.account_id
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY cm.client_id
        )
        SELECT 
            cb.client_name,
            cb.client_id,
            cb.current_balance as total_balance,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.client_id = qsb.client_id
        LEFT JOIN ytd_start_balances ysb ON cb.client_id = ysb.client_id
        ORDER BY cb.current_balance DESC
    '''
    cursor.execute(query, (date_string, qtd_comparison_date.strftime('%Y-%m-%d'), ytd_comparison_date.strftime('%Y-%m-%d')))
    client_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get fund balances for the selected date with QTD and YTD
    query = '''
        WITH current_balances AS (
            SELECT 
                ab.fund_name,
                f.fund_ticker,
                SUM(ab.balance) as current_balance,
                COUNT(DISTINCT ab.account_id) as account_count
            FROM account_balances ab
            LEFT JOIN funds f ON ab.fund_name = f.fund_name
            WHERE ab.balance_date = ?
            GROUP BY ab.fund_name, f.fund_ticker
        ),
        qtd_start_balances AS (
            SELECT 
                fund_name,
                SUM(balance) as qtd_start_balance
            FROM account_balances
            WHERE balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY fund_name
        ),
        ytd_start_balances AS (
            SELECT 
                fund_name,
                SUM(balance) as ytd_start_balance
            FROM account_balances
            WHERE balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY fund_name
        )
        SELECT 
            cb.fund_name,
            cb.fund_ticker,
            cb.current_balance as total_balance,
            cb.account_count,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.fund_name = qsb.fund_name
        LEFT JOIN ytd_start_balances ysb ON cb.fund_name = ysb.fund_name
        ORDER BY cb.current_balance DESC
    '''
    cursor.execute(query, (date_string, qtd_comparison_date.strftime('%Y-%m-%d'), ytd_comparison_date.strftime('%Y-%m-%d')))
    fund_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get account details for the selected date with QTD and YTD - aggregated at account level
    query = '''
        WITH current_balances AS (
            SELECT 
                ab.account_id,
                cm.client_name,
                SUM(ab.balance) as current_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.balance_date = ?
            GROUP BY ab.account_id, cm.client_name
        ),
        qtd_start_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as qtd_start_balance
            FROM account_balances ab
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY ab.account_id
        ),
        ytd_start_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as ytd_start_balance
            FROM account_balances ab
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            GROUP BY ab.account_id
        )
        SELECT 
            cb.account_id,
            cb.client_name,
            cb.current_balance as total_balance,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL OR qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL OR ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances qsb ON cb.account_id = qsb.account_id
        LEFT JOIN ytd_start_balances ysb ON cb.account_id = ysb.account_id
        ORDER BY cb.current_balance DESC
    '''
    cursor.execute(query, (date_string, qtd_comparison_date.strftime('%Y-%m-%d'), ytd_comparison_date.strftime('%Y-%m-%d')))
    account_details = [dict(row) for row in cursor.fetchall()]
    
    # Get history data (same as overview for charts context)
    end_date = (datetime.now() - timedelta(days=1)).date()
    
    # 90-day history
    start_date_90 = end_date - timedelta(days=90)
    query_90 = '''
        SELECT 
            balance_date,
            SUM(balance) as total_balance
        FROM account_balances
        WHERE balance_date >= ? AND balance_date <= ?
        GROUP BY balance_date
        ORDER BY balance_date
    '''
    cursor.execute(query_90, (start_date_90.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    recent_history = [dict(row) for row in cursor.fetchall()]
    
    # 3-year history
    start_date_3y = end_date - timedelta(days=365*3)
    query_3y = '''
        SELECT 
            balance_date,
            SUM(balance) as total_balance
        FROM account_balances
        WHERE balance_date >= ? AND balance_date <= ?
        GROUP BY balance_date
        ORDER BY balance_date
    '''
    cursor.execute(query_3y, (start_date_3y.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    long_term_history = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'selected_date': date_string,
        'recent_history': recent_history,
        'long_term_history': long_term_history,
        'client_balances': client_balances,
        'fund_balances': fund_balances,
        'account_details': account_details
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('FLASK_PORT', 9095))
    app.run(debug=True, host='0.0.0.0', port=port)