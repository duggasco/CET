# Database Migration Guide

## Adding Fund Tickers (Latest Update)

If you have an existing deployment that was created before the fund ticker feature was added, you need to run the migration script to add the `funds` table to your database.

### Steps to migrate:

1. **Backup your database first:**
   ```bash
   cp client_exploration.db client_exploration.db.backup
   ```

2. **Run the migration script:**
   ```bash
   python3 migrate_add_funds_table.py
   ```

   This script will:
   - Create the `funds` table if it doesn't exist
   - Populate it with fund ticker mappings
   - Skip if the table already exists

3. **Verify the migration:**
   ```bash
   sqlite3 client_exploration.db "SELECT * FROM funds;"
   ```

   You should see:
   ```
   Government Money Market|GMMF
   Prime Money Market|PMMF
   Treasury Fund|TRSF
   Municipal Money Market|MUNF
   Corporate Bond Fund|CBND
   Institutional Fund|INST
   ```

### Note:
The application will still work without the funds table (fund_ticker will be null), but running the migration is recommended to get the full functionality.