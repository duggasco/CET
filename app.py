from flask import Flask, jsonify, render_template, request, make_response, Response
import sqlite3
from datetime import datetime, timedelta, date
import json
import time
import csv
from io import StringIO
from contextlib import closing

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

def generate_qtd_ytd_cte_sql(entity_type, group_by_field, where_clause):
    """
    Generate QTD/YTD CTE SQL fragment for consistent metric calculation
    
    Args:
        entity_type: 'client', 'fund', or 'account' (used for CTE naming)
        group_by_field: Field to group by (e.g., 'cm.client_id', 'ab.fund_name')
        where_clause: WHERE clause to apply (should be full_where_clause for intersection)
    
    Returns:
        SQL string fragment with two CTEs
    """
    client_mapping_join = ''
    if entity_type in ['client', 'account']:
        client_mapping_join = 'JOIN client_mapping cm ON ab.account_id = cm.account_id'
    
    return f'''
        qtd_start_balances_{entity_type} AS (
            SELECT
                {group_by_field} as entity_id,
                SUM(ab.balance) as qtd_start_balance
            FROM account_balances ab
            {client_mapping_join}
            LEFT JOIN funds f ON ab.fund_name = f.fund_name
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances
                WHERE balance_date <= ?
            )
            {where_clause}
            GROUP BY {group_by_field}
        ),
        ytd_start_balances_{entity_type} AS (
            SELECT
                {group_by_field} as entity_id,
                SUM(ab.balance) as ytd_start_balance
            FROM account_balances ab
            {client_mapping_join}
            LEFT JOIN funds f ON ab.fund_name = f.fund_name
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances
                WHERE balance_date <= ?
            )
            {where_clause}
            GROUP BY {group_by_field}
        )'''

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
    # All filtering is now done at SQL level, so just return data as-is
    return data

def build_filter_clause(client_ids=None, fund_names=None, account_ids=None, 
                       fund_ticker_filter='', client_name_filter='', 
                       account_number_filter='', prepend_and=True,
                       exclude_filters=None):
    """Build dynamic WHERE clause for SQL queries based on provided filters.
    
    Note: If using fund_ticker_filter, the query must join the funds table with alias 'f'
    
    Args:
        exclude_filters: List of filter names to exclude (e.g., ['client_ids', 'fund_names', 'account_ids'])
    
    Returns:
        tuple: (where_clause_string, params_list)
    """
    if exclude_filters is None:
        exclude_filters = []
        
    conditions = []
    params = []
    
    # Exact match filters for multi-selection
    if client_ids and 'client_ids' not in exclude_filters:
        placeholders = ','.join(['?' for _ in client_ids])
        conditions.append(f'cm.client_id IN ({placeholders})')
        params.extend(client_ids)
    
    if fund_names and 'fund_names' not in exclude_filters:
        placeholders = ','.join(['?' for _ in fund_names])
        conditions.append(f'ab.fund_name IN ({placeholders})')
        params.extend(fund_names)
    
    if account_ids and 'account_ids' not in exclude_filters:
        placeholders = ','.join(['?' for _ in account_ids])
        conditions.append(f'ab.account_id IN ({placeholders})')
        params.extend(account_ids)
    
    # Text filters (partial match with LIKE)
    if fund_ticker_filter:
        conditions.append('(f.fund_ticker LIKE ? OR ab.fund_name LIKE ?)')
        params.extend([f'%{fund_ticker_filter}%', f'%{fund_ticker_filter}%'])
    
    if client_name_filter:
        conditions.append('cm.client_name LIKE ?')
        params.append(f'%{client_name_filter}%')
    
    if account_number_filter:
        conditions.append('ab.account_id LIKE ?')
        params.append(f'%{account_number_filter}%')
    
    if conditions:
        clause = ' AND '.join(conditions)
        return (' AND ' + clause) if prepend_and else clause, params
    return '', params

@app.route('/')
def index():
    # Generate cache bust parameter based on current timestamp
    cache_bust = int(time.time())
    return render_template('index.html', cache_bust=cache_bust)

@app.route('/api/overview')
def get_overview():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get filter parameters
    filters = get_text_filters()
    fund_ticker_filter = filters.get('fund_ticker_filter', '')
    client_name_filter = filters.get('client_name_filter', '')
    account_number_filter = filters.get('account_number_filter', '')
    
    # Get aggregated balance over time for different periods
    end_date = (datetime.now() - timedelta(days=1)).date()  # Yesterday
    
    # 90-day history for recent chart
    start_date_90 = end_date - timedelta(days=90)
    
    # Build query based on filters
    query_90 = '''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date >= ? AND ab.balance_date <= ?
    '''
    
    params = [start_date_90.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
    
    # Add filter conditions
    if fund_ticker_filter:
        query_90 += ' AND (f.fund_ticker LIKE ? OR ab.fund_name LIKE ?)'
        params.extend([f'%{fund_ticker_filter}%', f'%{fund_ticker_filter}%'])
    
    if client_name_filter:
        query_90 += ' AND cm.client_name LIKE ?'
        params.append(f'%{client_name_filter}%')
    
    if account_number_filter:
        query_90 += ' AND ab.account_id LIKE ?'
        params.append(f'%{account_number_filter}%')
    
    query_90 += '''
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    
    cursor.execute(query_90, tuple(params))
    recent_history = [dict(row) for row in cursor.fetchall()]
    
    # 3-year history for long-term chart
    start_date_3y = end_date - timedelta(days=365*3)
    
    # Build query based on filters
    query_3y = '''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date >= ? AND ab.balance_date <= ?
    '''
    
    params_3y = [start_date_3y.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
    
    # Add filter conditions
    if fund_ticker_filter:
        query_3y += ' AND (f.fund_ticker LIKE ? OR ab.fund_name LIKE ?)'
        params_3y.extend([f'%{fund_ticker_filter}%', f'%{fund_ticker_filter}%'])
    
    if client_name_filter:
        query_3y += ' AND cm.client_name LIKE ?'
        params_3y.append(f'%{client_name_filter}%')
    
    if account_number_filter:
        query_3y += ' AND ab.account_id LIKE ?'
        params_3y.append(f'%{account_number_filter}%')
    
    query_3y += '''
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    
    cursor.execute(query_3y, tuple(params_3y))
    long_term_history = [dict(row) for row in cursor.fetchall()]
    
    # Calculate QTD and YTD start dates
    today = end_date
    current_quarter = (today.month - 1) // 3
    qtd_start = date(today.year, current_quarter * 3 + 1, 1)
    ytd_start = date(today.year, 1, 1)
    
    # Get client aggregated balances with QTD and YTD changes
    # Build dynamic query with filters
    base_current = """
        SELECT 
            cm.client_name,
            cm.client_id,
            SUM(ab.balance) as current_balance
        FROM client_mapping cm
        JOIN account_balances ab ON cm.account_id = ab.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
    """
    
    base_qtd = """
        SELECT 
            cm.client_id,
            SUM(ab.balance) as qtd_start_balance
        FROM client_mapping cm
        JOIN account_balances ab ON cm.account_id = ab.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (
            SELECT MAX(balance_date) FROM account_balances 
            WHERE balance_date <= ?
        )
    """
    
    base_ytd = """
        SELECT 
            cm.client_id,
            SUM(ab.balance) as ytd_start_balance
        FROM client_mapping cm
        JOIN account_balances ab ON cm.account_id = ab.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (
            SELECT MAX(balance_date) FROM account_balances 
            WHERE balance_date <= ?
        )
    """
    
    # Build filter conditions
    filter_conditions = []
    filter_params = []
    
    if fund_ticker_filter:
        filter_conditions.append('(f.fund_ticker LIKE ? OR ab.fund_name LIKE ?)')
        filter_params.extend([f'%{fund_ticker_filter}%', f'%{fund_ticker_filter}%'])
    
    if client_name_filter:
        filter_conditions.append('cm.client_name LIKE ?')
        filter_params.append(f'%{client_name_filter}%')
    
    if account_number_filter:
        filter_conditions.append('ab.account_id LIKE ?')
        filter_params.append(f'%{account_number_filter}%')
    
    # Build filter clause
    filter_clause = ''
    if filter_conditions:
        filter_clause = ' AND ' + ' AND '.join(filter_conditions)
    
    # Build complete query
    query = f"""
        WITH current_balances AS (
            {base_current}{filter_clause}
            GROUP BY cm.client_name, cm.client_id
        ),
        qtd_start_balances AS (
            {base_qtd}{filter_clause}
            GROUP BY cm.client_id
        ),
        ytd_start_balances AS (
            {base_ytd}{filter_clause}
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
    """
    
    # Execute with appropriate parameters
    if filter_conditions:
        # Parameters: filter_params for current + qtd_date + filter_params for qtd + ytd_date + filter_params for ytd
        all_params = filter_params + [qtd_start.strftime('%Y-%m-%d')] + filter_params + [ytd_start.strftime('%Y-%m-%d')] + filter_params
        cursor.execute(query, tuple(all_params))
    else:
        cursor.execute(query, (qtd_start.strftime('%Y-%m-%d'), ytd_start.strftime('%Y-%m-%d')))
    
    client_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get fund aggregated balances with QTD and YTD changes
    # Build dynamic query with filters
    base_current_fund = """
        SELECT 
            ab.fund_name,
            f.fund_ticker,
            SUM(ab.balance) as current_balance,
            COUNT(DISTINCT ab.account_id) as account_count
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
    """
    
    base_qtd_fund = """
        SELECT 
            ab.fund_name,
            SUM(ab.balance) as qtd_start_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (
            SELECT MAX(balance_date) FROM account_balances 
            WHERE balance_date <= ?
        )
    """
    
    base_ytd_fund = """
        SELECT 
            ab.fund_name,
            SUM(ab.balance) as ytd_start_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (
            SELECT MAX(balance_date) FROM account_balances 
            WHERE balance_date <= ?
        )
    """
    
    # Reuse filter conditions from client query
    # filter_conditions and filter_params are already built above
    
    # Build complete fund query
    fund_query = f"""
        WITH current_balances AS (
            {base_current_fund}{filter_clause}
            GROUP BY ab.fund_name, f.fund_ticker
        ),
        qtd_start_balances AS (
            {base_qtd_fund}{filter_clause}
            GROUP BY ab.fund_name
        ),
        ytd_start_balances AS (
            {base_ytd_fund}{filter_clause}
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
    """
    
    # Execute with appropriate parameters
    if filter_conditions:
        # Parameters: filter_params for current + qtd_date + filter_params for qtd + ytd_date + filter_params for ytd
        fund_params = filter_params + [qtd_start.strftime('%Y-%m-%d')] + filter_params + [ytd_start.strftime('%Y-%m-%d')] + filter_params
        cursor.execute(fund_query, tuple(fund_params))
    else:
        cursor.execute(fund_query, (qtd_start.strftime('%Y-%m-%d'), ytd_start.strftime('%Y-%m-%d')))
    
    fund_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get account details with QTD and YTD - aggregated at account level
    # Build dynamic query with filters
    base_current_account = """
        SELECT 
            ab.account_id,
            cm.client_name,
            SUM(ab.balance) as current_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
    """
    
    base_qtd_account = """
        SELECT 
            ab.account_id,
            SUM(ab.balance) as qtd_start_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (
            SELECT MAX(balance_date) FROM account_balances 
            WHERE balance_date <= ?
        )
    """
    
    base_ytd_account = """
        SELECT 
            ab.account_id,
            SUM(ab.balance) as ytd_start_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date = (
            SELECT MAX(balance_date) FROM account_balances 
            WHERE balance_date <= ?
        )
    """
    
    # Build complete account query using same filter conditions
    account_query = f"""
        WITH current_balances AS (
            {base_current_account}{filter_clause}
            GROUP BY ab.account_id, cm.client_name
            HAVING current_balance > 0
        ),
        qtd_start_balances AS (
            {base_qtd_account}{filter_clause}
            GROUP BY ab.account_id
        ),
        ytd_start_balances AS (
            {base_ytd_account}{filter_clause}
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
    """
    
    # Execute with appropriate parameters (same as fund query)
    if filter_conditions:
        # Parameters: filter_params for current + qtd_date + filter_params for qtd + ytd_date + filter_params for ytd
        account_params = filter_params + [qtd_start.strftime('%Y-%m-%d')] + filter_params + [ytd_start.strftime('%Y-%m-%d')] + filter_params
        cursor.execute(account_query, tuple(account_params))
    else:
        cursor.execute(account_query, (qtd_start.strftime('%Y-%m-%d'), ytd_start.strftime('%Y-%m-%d')))
    
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
    
    # Get text filters from query parameters
    filters = get_text_filters()
    fund_ticker_filter = filters.get('fund_ticker_filter', '')
    client_name_filter = filters.get('client_name_filter', '')
    account_number_filter = filters.get('account_number_filter', '')

    # Log active filters
    if fund_ticker_filter or client_name_filter or account_number_filter:
        print(f"Text filters for client {client_id}: fund='{fund_ticker_filter}', client='{client_name_filter}', account='{account_number_filter}'")

    # Build filter clause (excluding client_name since we're already filtering by client_id)
    filter_clause, filter_params = build_filter_clause(
        fund_ticker_filter=fund_ticker_filter,
        client_name_filter='',  # Exclude since client_id already filters
        account_number_filter=account_number_filter,
        prepend_and=True
    )
    
    # Get client balance history for different periods
    end_date = (datetime.now() - timedelta(days=1)).date()  # Yesterday
    
    # 90-day history
    start_date_90 = end_date - timedelta(days=90)
    fund_join = "LEFT JOIN funds f ON ab.fund_name = f.fund_name" if fund_ticker_filter else ""
    query_90 = f'''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        {fund_join}
        WHERE cm.client_id = ? AND ab.balance_date >= ? AND ab.balance_date <= ?
        {filter_clause}
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    params_90 = [client_id, start_date_90.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')] + filter_params
    cursor.execute(query_90, params_90)
    recent_history = [dict(row) for row in cursor.fetchall()]
    
    # 3-year history
    start_date_3y = end_date - timedelta(days=365*3)
    query_3y = f'''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        {fund_join}
        WHERE cm.client_id = ? AND ab.balance_date >= ? AND ab.balance_date <= ?
        {filter_clause}
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    params_3y = [client_id, start_date_3y.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')] + filter_params
    cursor.execute(query_3y, params_3y)
    long_term_history = [dict(row) for row in cursor.fetchall()]
    
    # Calculate QTD and YTD start dates
    today = end_date
    current_quarter = (today.month - 1) // 3
    qtd_start = date(today.year, current_quarter * 3 + 1, 1)
    ytd_start = date(today.year, 1, 1)
    
    # Get client's fund balances with QTD and YTD
    query = f'''
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
            {filter_clause}
            GROUP BY ab.fund_name, f.fund_ticker
        ),
        qtd_start_balances AS (
            SELECT 
                ab.fund_name,
                SUM(ab.balance) as qtd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            {fund_join}
            WHERE cm.client_id = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            {filter_clause}
            GROUP BY ab.fund_name
        ),
        ytd_start_balances AS (
            SELECT 
                ab.fund_name,
                SUM(ab.balance) as ytd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            {fund_join}
            WHERE cm.client_id = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            {filter_clause}
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
    
    fund_params = [client_id] + filter_params + [client_id, qtd_start.strftime('%Y-%m-%d')] + filter_params + [client_id, ytd_start.strftime('%Y-%m-%d')] + filter_params
    cursor.execute(query, fund_params)
    fund_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get client's account details with QTD and YTD - aggregated at account level
    query = f'''
        WITH current_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as current_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            {fund_join}
            WHERE cm.client_id = ? AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            {filter_clause}
            GROUP BY ab.account_id
        ),
        qtd_start_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as qtd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            {fund_join}
            WHERE cm.client_id = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            {filter_clause}
            GROUP BY ab.account_id
        ),
        ytd_start_balances AS (
            SELECT 
                ab.account_id,
                SUM(ab.balance) as ytd_start_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            {fund_join}
            WHERE cm.client_id = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            {filter_clause}
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
    
    account_params = [client_id] + filter_params + [client_id, qtd_start.strftime('%Y-%m-%d')] + filter_params + [client_id, ytd_start.strftime('%Y-%m-%d')] + filter_params
    cursor.execute(query, account_params)
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
    
    # Get text filters from query parameters
    filters = get_text_filters()
    fund_ticker_filter = filters.get('fund_ticker_filter', '')
    client_name_filter = filters.get('client_name_filter', '')
    account_number_filter = filters.get('account_number_filter', '')

    # Log active filters
    if fund_ticker_filter or client_name_filter or account_number_filter:
        print(f"Text filters for fund {fund_name}: fund='{fund_ticker_filter}', client='{client_name_filter}', account='{account_number_filter}'")

    # Build filter clause (excluding fund_ticker since we're already filtering by fund_name)
    filter_clause, filter_params = build_filter_clause(
        fund_ticker_filter='',  # Exclude since fund_name already filters
        client_name_filter=client_name_filter,
        account_number_filter=account_number_filter,
        prepend_and=True
    )
    
    # Get fund balance history for different periods
    end_date = (datetime.now() - timedelta(days=1)).date()  # Yesterday
    
    # 90-day history
    start_date_90 = end_date - timedelta(days=90)
    client_join = "JOIN client_mapping cm ON ab.account_id = cm.account_id" if client_name_filter or account_number_filter else ""
    query_90 = f'''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        {client_join}
        WHERE ab.fund_name = ? AND ab.balance_date >= ? AND ab.balance_date <= ?
        {filter_clause}
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    params_90 = [fund_name, start_date_90.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')] + filter_params
    cursor.execute(query_90, params_90)
    recent_history = [dict(row) for row in cursor.fetchall()]
    
    # 3-year history
    start_date_3y = end_date - timedelta(days=365*3)
    query_3y = f'''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        {client_join}
        WHERE ab.fund_name = ? AND ab.balance_date >= ? AND ab.balance_date <= ?
        {filter_clause}
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    params_3y = [fund_name, start_date_3y.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')] + filter_params
    cursor.execute(query_3y, params_3y)
    long_term_history = [dict(row) for row in cursor.fetchall()]
    
    # Calculate QTD and YTD start dates
    today = end_date
    current_quarter = (today.month - 1) // 3
    qtd_start = date(today.year, current_quarter * 3 + 1, 1)
    ytd_start = date(today.year, 1, 1)
    
    # Get client balances for this fund with QTD and YTD
    query = f'''
        WITH current_balances AS (
            SELECT 
                cm.client_name,
                cm.client_id,
                SUM(ab.balance) as current_balance,
                COUNT(DISTINCT ab.account_id) as account_count
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.fund_name = ? AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            {filter_clause}
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
            {filter_clause}
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
            {filter_clause}
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
    
    client_params = [fund_name] + filter_params + [fund_name, qtd_start.strftime('%Y-%m-%d')] + filter_params + [fund_name, ytd_start.strftime('%Y-%m-%d')] + filter_params
    cursor.execute(query, client_params)
    client_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get account details for this fund with QTD and YTD
    query = f'''
        WITH current_balances AS (
            SELECT 
                ab.account_id,
                cm.client_name,
                ab.balance as current_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE ab.fund_name = ? AND ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            {filter_clause}
        ),
        qtd_start_balances AS (
            SELECT 
                ab.account_id,
                ab.balance as qtd_start_balance
            FROM account_balances ab
            {client_join}
            WHERE ab.fund_name = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            {filter_clause}
        ),
        ytd_start_balances AS (
            SELECT 
                ab.account_id,
                ab.balance as ytd_start_balance
            FROM account_balances ab
            {client_join}
            WHERE ab.fund_name = ? AND ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= ?
            )
            {filter_clause}
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
    
    account_params = [fund_name] + filter_params + [fund_name, qtd_start.strftime('%Y-%m-%d')] + filter_params + [fund_name, ytd_start.strftime('%Y-%m-%d')] + filter_params
    cursor.execute(query, account_params)
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
                           'balance': acc['balance'],
                           'qtd_change': acc.get('qtd_change'),
                           'ytd_change': acc.get('ytd_change')} for acc in account_details]
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
    
    # Get filter parameters from query string
    client_ids = request.args.getlist('client_id')
    fund_names = request.args.getlist('fund_name')
    account_ids = request.args.getlist('account_id')
    
    # Get history data (same as overview for charts context)
    end_date = (datetime.now() - timedelta(days=1)).date()
    
    # Build WHERE clause for filtered history
    history_where_clauses = []
    history_params = []
    
    if client_ids:
        placeholders = ','.join(['?' for _ in client_ids])
        history_where_clauses.append(f'ab.account_id IN (SELECT account_id FROM client_mapping WHERE client_id IN ({placeholders}))')
        history_params.extend(client_ids)
    
    if fund_names:
        placeholders = ','.join(['?' for _ in fund_names])
        history_where_clauses.append(f'ab.fund_name IN ({placeholders})')
        history_params.extend(fund_names)
    
    if account_ids:
        placeholders = ','.join(['?' for _ in account_ids])
        history_where_clauses.append(f'ab.account_id IN ({placeholders})')
        history_params.extend(account_ids)
    
    history_where_clause = ' AND '.join(history_where_clauses) if history_where_clauses else '1=1'
    
    # 90-day history
    start_date_90 = end_date - timedelta(days=90)
    query_90 = f'''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        WHERE ab.balance_date >= ? AND ab.balance_date <= ?
        AND {history_where_clause}
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    params_90 = [start_date_90.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')] + history_params
    cursor.execute(query_90, params_90)
    recent_history = [dict(row) for row in cursor.fetchall()]
    
    # 3-year history
    start_date_3y = end_date - timedelta(days=365*3)
    query_3y = f'''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        WHERE ab.balance_date >= ? AND ab.balance_date <= ?
        AND {history_where_clause}
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    params_3y = [start_date_3y.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')] + history_params
    cursor.execute(query_3y, params_3y)
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

def _build_csv_where_clause(args):
    """Build WHERE clause for CSV download queries"""
    where_clauses = []
    params = []
    
    # Multi-selection filters
    client_ids = args.getlist('client_id')
    fund_names = args.getlist('fund_name')
    account_ids = args.getlist('account_id')
    
    if client_ids:
        placeholders = ','.join(['?' for _ in range(len(client_ids))])
        where_clauses.append(f'cm.client_id IN ({placeholders})')
        params.extend(client_ids)
    
    if fund_names:
        placeholders = ','.join(['?' for _ in range(len(fund_names))])
        where_clauses.append(f'ab.fund_name IN ({placeholders})')
        params.extend(fund_names)
        
    if account_ids:
        placeholders = ','.join(['?' for _ in range(len(account_ids))])
        where_clauses.append(f'ab.account_id IN ({placeholders})')
        params.extend(account_ids)
    
    # Text filters
    filters = get_text_filters()
    if filters['fund_ticker_filter']:
        where_clauses.append('ab.fund_name LIKE ?')
        params.append(f"%{filters['fund_ticker_filter']}%")
    
    if filters['client_name_filter']:
        where_clauses.append('cm.client_name LIKE ?')
        params.append(f"%{filters['client_name_filter']}%")
        
    if filters['account_number_filter']:
        where_clauses.append('ab.account_id LIKE ?')
        params.append(f"%{filters['account_number_filter']}%")
    
    where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
    return where_sql, params

def _get_historical_balances(conn, account_fund_pairs, target_date):
    """Pre-fetch quarter and year start balances for QTD/YTD calculations"""
    if not account_fund_pairs:
        return {}
    
    # Calculate boundaries
    quarter_start = date(target_date.year, ((target_date.month - 1) // 3) * 3 + 1, 1)
    year_start = date(target_date.year, 1, 1)
    
    # Build query for historical balances - SQLite doesn't support VALUES clause well
    # Instead, we'll use a simpler approach
    query = '''
        SELECT 
            ab.account_id,
            ab.fund_name,
            ab.balance_date,
            ab.balance
        FROM account_balances ab
        WHERE ab.balance_date IN (?, ?)
    '''
    
    params = [quarter_start, year_start]
    
    results = {}
    cursor = conn.cursor()
    for row in cursor.execute(query, params):
        key = (row['account_id'], row['fund_name'])
        balance_date = row['balance_date']
        
        if key not in results:
            results[key] = {'qtd_balance': 0, 'ytd_balance': 0}
        
        if balance_date == str(quarter_start):
            results[key]['qtd_balance'] = row['balance'] or 0
        elif balance_date == str(year_start):
            results[key]['ytd_balance'] = row['balance'] or 0
    
    return results

@app.route('/api/data')
def get_filtered_data():
    """Unified endpoint for fetching data with multiple filters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all filter parameters
    client_ids = request.args.getlist('client_id')
    fund_names = request.args.getlist('fund_name')
    account_ids = request.args.getlist('account_id')
    
    # Get text filters
    fund_ticker_filter = request.args.get('fund_ticker', '').strip()
    client_name_filter = request.args.get('client_name', '').strip()
    account_number_filter = request.args.get('account_number', '').strip()
    
    # Validate that at least one filter is provided
    all_filters = (client_ids + fund_names + account_ids +
                   [fund_ticker_filter, client_name_filter, account_number_filter])
    
    if not any(f for f in all_filters if f):
        return jsonify({'error': 'At least one filter must be provided'}), 400
    
    # Build different filter clauses for each table
    # Client table: exclude client_ids filter
    client_where_clause, client_params = build_filter_clause(
        client_ids=client_ids,
        fund_names=fund_names,
        account_ids=account_ids,
        fund_ticker_filter=fund_ticker_filter,
        client_name_filter=client_name_filter,
        account_number_filter=account_number_filter,
        prepend_and=True,
        exclude_filters=['client_ids']
    )
    
    # Fund table: exclude fund_names filter
    fund_where_clause, fund_params = build_filter_clause(
        client_ids=client_ids,
        fund_names=fund_names,
        account_ids=account_ids,
        fund_ticker_filter=fund_ticker_filter,
        client_name_filter=client_name_filter,
        account_number_filter=account_number_filter,
        prepend_and=True,
        exclude_filters=['fund_names']
    )
    
    # Account table and charts: include all filters
    full_where_clause, full_params = build_filter_clause(
        client_ids=client_ids,
        fund_names=fund_names,
        account_ids=account_ids,
        fund_ticker_filter=fund_ticker_filter,
        client_name_filter=client_name_filter,
        account_number_filter=account_number_filter,
        prepend_and=True
    )
    
    # Get date range
    end_date = (datetime.now() - timedelta(days=1)).date()
    start_date_90 = end_date - timedelta(days=90)
    start_date_3y = end_date - timedelta(days=365*3)
    
    # Calculate QTD and YTD start dates
    today = end_date
    current_quarter = (today.month - 1) // 3
    qtd_start = date(today.year, current_quarter * 3 + 1, 1)
    ytd_start = date(today.year, 1, 1)
    
    # Add debug logging for QTD/YTD calculation with full intersection
    if client_ids or fund_names or account_ids:
        app.logger.debug(f"QTD/YTD calculation using full intersection: {full_where_clause}")
    
    # Get recent history (90 days)
    recent_query = f'''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date >= ? AND ab.balance_date <= ?
        {full_where_clause}
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    
    cursor.execute(recent_query, [start_date_90.strftime('%Y-%m-%d'), 
                                  end_date.strftime('%Y-%m-%d')] + full_params)
    recent_history = [dict(row) for row in cursor.fetchall()]
    
    # Get long-term history (3 years)
    long_query = f'''
        SELECT 
            ab.balance_date,
            SUM(ab.balance) as total_balance
        FROM account_balances ab
        JOIN client_mapping cm ON ab.account_id = cm.account_id
        LEFT JOIN funds f ON ab.fund_name = f.fund_name
        WHERE ab.balance_date >= ? AND ab.balance_date <= ?
        {full_where_clause}
        GROUP BY ab.balance_date
        ORDER BY ab.balance_date
    '''
    
    cursor.execute(long_query, [start_date_3y.strftime('%Y-%m-%d'), 
                                end_date.strftime('%Y-%m-%d')] + full_params)
    long_term_history = [dict(row) for row in cursor.fetchall()]
    
    # Get client balances with QTD and YTD using full intersection for metrics
    qtd_ytd_client_sql = generate_qtd_ytd_cte_sql('client', 'cm.client_id', full_where_clause)
    client_query = f'''
        WITH current_balances AS (
            SELECT 
                cm.client_name,
                cm.client_id,
                SUM(ab.balance) as current_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            LEFT JOIN funds f ON ab.fund_name = f.fund_name
            WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            {client_where_clause}
            GROUP BY cm.client_name, cm.client_id
        ),
        {qtd_ytd_client_sql}
        SELECT 
            cb.client_name,
            cb.client_id,
            cb.current_balance as total_balance,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL THEN NULL
                WHEN qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL THEN NULL
                WHEN ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances_client qsb ON cb.client_id = qsb.entity_id
        LEFT JOIN ytd_start_balances_client ysb ON cb.client_id = ysb.entity_id
        ORDER BY cb.current_balance DESC
    '''
    
    client_query_params = client_params + [qtd_start.strftime('%Y-%m-%d')] + full_params + [ytd_start.strftime('%Y-%m-%d')] + full_params
    cursor.execute(client_query, client_query_params)
    client_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get fund balances with QTD and YTD using full intersection for metrics
    qtd_ytd_fund_sql = generate_qtd_ytd_cte_sql('fund', 'ab.fund_name', full_where_clause)
    fund_query = f'''
        WITH current_balances AS (
            SELECT 
                ab.fund_name,
                f.fund_ticker,
                SUM(ab.balance) as current_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            LEFT JOIN funds f ON ab.fund_name = f.fund_name
            WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            {fund_where_clause}
            GROUP BY ab.fund_name, f.fund_ticker
        ),
        {qtd_ytd_fund_sql}
        SELECT 
            cb.fund_name,
            cb.fund_ticker,
            cb.current_balance as total_balance,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL THEN NULL
                WHEN qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL THEN NULL
                WHEN ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances_fund qsb ON cb.fund_name = qsb.entity_id
        LEFT JOIN ytd_start_balances_fund ysb ON cb.fund_name = ysb.entity_id
        ORDER BY cb.current_balance DESC
    '''
    
    fund_query_params = fund_params + [qtd_start.strftime('%Y-%m-%d')] + full_params + [ytd_start.strftime('%Y-%m-%d')] + full_params
    cursor.execute(fund_query, fund_query_params)
    fund_balances = [dict(row) for row in cursor.fetchall()]
    
    # Get account details with QTD and YTD (already uses full intersection, updating for consistency)
    qtd_ytd_account_sql = generate_qtd_ytd_cte_sql('account', 'ab.account_id', full_where_clause)
    account_query = f'''
        WITH current_balances AS (
            SELECT 
                ab.account_id,
                cm.client_name,
                SUM(ab.balance) as current_balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            LEFT JOIN funds f ON ab.fund_name = f.fund_name
            WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            {full_where_clause}
            GROUP BY ab.account_id, cm.client_name
        ),
        {qtd_ytd_account_sql}
        SELECT 
            cb.account_id,
            cb.client_name,
            cb.current_balance as total_balance,
            CASE 
                WHEN qsb.qtd_start_balance IS NULL THEN NULL
                WHEN qsb.qtd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - qsb.qtd_start_balance) / qsb.qtd_start_balance) * 100
            END as qtd_change,
            CASE 
                WHEN ysb.ytd_start_balance IS NULL THEN NULL
                WHEN ysb.ytd_start_balance = 0 THEN 0
                ELSE ((cb.current_balance - ysb.ytd_start_balance) / ysb.ytd_start_balance) * 100
            END as ytd_change
        FROM current_balances cb
        LEFT JOIN qtd_start_balances_account qsb ON cb.account_id = qsb.entity_id
        LEFT JOIN ytd_start_balances_account ysb ON cb.account_id = ysb.entity_id
        ORDER BY cb.current_balance DESC
    '''
    
    account_query_params = full_params + [qtd_start.strftime('%Y-%m-%d')] + full_params + [ytd_start.strftime('%Y-%m-%d')] + full_params
    cursor.execute(account_query, account_query_params)
    account_details = [dict(row) for row in cursor.fetchall()]
    
    # Get KPI metrics (using full filtering)
    kpi_query = '''
        WITH current_totals AS (
            SELECT 
                COALESCE(SUM(ab.balance), 0) as total_aum,
                COUNT(DISTINCT cm.client_id) as active_clients,
                COUNT(DISTINCT ab.fund_name) as active_funds,
                COUNT(DISTINCT ab.account_id) as active_accounts
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            LEFT JOIN funds f ON ab.fund_name = f.fund_name
            WHERE ab.balance_date = (SELECT MAX(balance_date) FROM account_balances)
            {full_where_clause}
        ),
        past_totals AS (
            SELECT 
                COALESCE(SUM(ab.balance), 0) as total_aum_30d_ago
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            LEFT JOIN funds f ON ab.fund_name = f.fund_name
            WHERE ab.balance_date = (
                SELECT MAX(balance_date) FROM account_balances 
                WHERE balance_date <= date((SELECT MAX(balance_date) FROM account_balances), '-30 days')
            )
            {full_where_clause}
        )
        SELECT 
            ct.total_aum,
            ct.active_clients,
            ct.active_funds,
            ct.active_accounts,
            pt.total_aum_30d_ago,
            CASE 
                WHEN pt.total_aum_30d_ago = 0 THEN 0
                ELSE ((ct.total_aum - pt.total_aum_30d_ago) / pt.total_aum_30d_ago) * 100
            END as change_30d_pct
        FROM current_totals ct
        CROSS JOIN past_totals pt
    '''

    cursor.execute(kpi_query.format(full_where_clause=full_where_clause), full_params + full_params)
    kpi_result = cursor.fetchone()

    if kpi_result:
        kpi_metrics = dict(kpi_result)
    else:
        # Provide default values if no data matches the filters
        kpi_metrics = {
            'total_aum': 0,
            'active_clients': 0,
            'active_funds': 0,
            'active_accounts': 0,
            'total_aum_30d_ago': 0,
            'change_30d_pct': 0
        }
    
    conn.close()
    
    # Build response
    response_data = {
        'filters': {
            'client_ids': client_ids,
            'fund_names': fund_names,
            'account_ids': account_ids,
            'fund_ticker': fund_ticker_filter,
            'client_name': client_name_filter,
            'account_number': account_number_filter
        },
        'recent_history': recent_history,
        'long_term_history': long_term_history,
        'client_balances': client_balances,
        'fund_balances': fund_balances,
        'account_details': account_details,
        'kpi_metrics': kpi_metrics
    }
    
    return jsonify(response_data)

@app.route('/api/download_csv/count')
def get_download_count():
    """Get count of rows that would be in CSV"""
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            where_sql, params = _build_csv_where_clause(request.args)
            
            query = f'''
                SELECT COUNT(*) as count
                FROM account_balances ab
                JOIN client_mapping cm ON ab.account_id = cm.account_id
                WHERE {where_sql}
            '''
            
            result = cursor.execute(query, params).fetchone()
            return jsonify({'count': result['count']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download_csv')
def download_csv():
    """Download filtered data as CSV"""
    MAX_ROWS = 1000000  # 1M row limit
    
    try:
        # First check row count
        count_response = get_download_count()
        count_data = count_response.get_json()
        
        if 'error' in count_data:
            return count_response
        
        row_count = count_data['count']
        if row_count > MAX_ROWS:
            return jsonify({
                'error': f'Download exceeds {MAX_ROWS:,} rows ({row_count:,} rows). Please apply more filters.'
            }), 413
        
        # Don't use context manager here - we need connection to stay open for generator
        conn = get_db_connection()
        cursor = conn.cursor()
        where_sql, params = _build_csv_where_clause(request.args)
        
        # Determine as_of_date
        selected_date = request.args.get('date')
        if selected_date:
            as_of_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        else:
            as_of_date = date.today()
        
        # Get unique account/fund pairs for historical data fetch
        pairs_query = f'''
            SELECT DISTINCT ab.account_id, ab.fund_name
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE {where_sql}
        '''
        
        account_fund_pairs = [(row['account_id'], row['fund_name']) 
                              for row in cursor.execute(pairs_query, params)]
        
        # Pre-fetch historical balances
        historical_balances = _get_historical_balances(conn, account_fund_pairs, as_of_date)
        
        # Main query
        query = f'''
            SELECT 
                ab.balance_date,
                cm.client_name,
                cm.client_id,
                ab.account_id,
                ab.fund_name,
                ab.balance
            FROM account_balances ab
            JOIN client_mapping cm ON ab.account_id = cm.account_id
            WHERE {where_sql}
            ORDER BY ab.balance_date DESC, cm.client_name, ab.account_id, ab.fund_name
        '''
        
        def generate_csv():
            try:
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow([
                    'Date', 'Client Name', 'Client ID', 'Account ID', 
                    'Fund Name', 'Balance', 'QTD%', 'YTD%', 
                    'QTD $Change', 'YTD $Change', 'As of Date'
                ])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)
                
                for row in cursor.execute(query, params):
                    key = (row['account_id'], row['fund_name'])
                    hist = historical_balances.get(key, {'qtd_balance': 0, 'ytd_balance': 0})
                    
                    current_balance = row['balance']
                    qtd_balance = hist['qtd_balance']
                    ytd_balance = hist['ytd_balance']
                    
                    # Calculate changes
                    qtd_change = current_balance - qtd_balance
                    ytd_change = current_balance - ytd_balance
                    
                    # Calculate percentages (avoid division by zero)
                    qtd_pct = (qtd_change / qtd_balance * 100) if qtd_balance != 0 else 0
                    ytd_pct = (ytd_change / ytd_balance * 100) if ytd_balance != 0 else 0
                    
                    writer.writerow([
                        row['balance_date'],
                        row['client_name'],
                        row['client_id'],
                        row['account_id'],
                        row['fund_name'],
                        f"${current_balance:,.2f}",
                        f"{qtd_pct:.2f}%",
                        f"{ytd_pct:.2f}%",
                        f"${qtd_change:,.2f}",
                        f"${ytd_change:,.2f}",
                        as_of_date.strftime('%Y-%m-%d')
                    ])
                    
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)
                    
            except Exception as e:
                yield f"Error generating CSV: {str(e)}\n"
            finally:
                # Close connection after generator completes
                conn.close()
        
        # Generate filename
        filter_parts = []
        if request.args.getlist('client_id'):
            filter_parts.append(f"{len(request.args.getlist('client_id'))}clients")
        if request.args.getlist('fund_name'):
            filter_parts.append(f"{len(request.args.getlist('fund_name'))}funds")
        if request.args.getlist('account_id'):
            filter_parts.append(f"{len(request.args.getlist('account_id'))}accounts")
        
        filter_summary = '_'.join(filter_parts) if filter_parts else 'all_data'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"financial_data_{filter_summary}_{timestamp}.csv"
        
        return Response(
            generate_csv(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('FLASK_PORT', 9095))
    app.run(debug=True, host='0.0.0.0', port=port)