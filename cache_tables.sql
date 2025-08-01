-- Cache tables for pre-computed dashboard data
-- These tables are refreshed nightly after data updates

-- Cached overview data (no filters)
CREATE TABLE IF NOT EXISTS cached_overview (
    cache_key TEXT PRIMARY KEY,
    as_of_date DATE NOT NULL,
    total_clients INTEGER NOT NULL,
    total_funds INTEGER NOT NULL,
    total_accounts INTEGER NOT NULL,
    total_aum DECIMAL(15,2) NOT NULL,
    aum_30d_ago DECIMAL(15,2),
    aum_30d_change DECIMAL(5,2),
    avg_ytd_growth DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cached client balances with QTD/YTD
CREATE TABLE IF NOT EXISTS cached_client_balances (
    client_id TEXT NOT NULL,
    as_of_date DATE NOT NULL,
    client_name TEXT NOT NULL,
    total_balance DECIMAL(15,2) NOT NULL,
    qtd_change DECIMAL(5,2),
    ytd_change DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (client_id, as_of_date)
);

-- Cached fund balances with QTD/YTD
CREATE TABLE IF NOT EXISTS cached_fund_balances (
    fund_name TEXT NOT NULL,
    as_of_date DATE NOT NULL,
    fund_ticker TEXT NOT NULL,
    total_balance DECIMAL(15,2) NOT NULL,
    qtd_change DECIMAL(5,2),
    ytd_change DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (fund_name, as_of_date)
);

-- Cached account details with QTD/YTD
CREATE TABLE IF NOT EXISTS cached_account_details (
    account_id TEXT NOT NULL,
    as_of_date DATE NOT NULL,
    client_id TEXT NOT NULL,
    client_name TEXT NOT NULL,
    balance DECIMAL(15,2) NOT NULL,
    qtd_change DECIMAL(5,2),
    ytd_change DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, as_of_date)
);

-- Cached chart data (90-day and 3-year)
CREATE TABLE IF NOT EXISTS cached_chart_data (
    cache_key TEXT NOT NULL,
    as_of_date DATE NOT NULL,
    data_date DATE NOT NULL,
    balance DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cache_key, as_of_date, data_date)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_cached_overview_date ON cached_overview(as_of_date);
CREATE INDEX IF NOT EXISTS idx_cached_client_date ON cached_client_balances(as_of_date);
CREATE INDEX IF NOT EXISTS idx_cached_fund_date ON cached_fund_balances(as_of_date);
CREATE INDEX IF NOT EXISTS idx_cached_account_date ON cached_account_details(as_of_date);
CREATE INDEX IF NOT EXISTS idx_cached_chart_key_date ON cached_chart_data(cache_key, as_of_date);