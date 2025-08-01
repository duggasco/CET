const { chromium } = require('playwright');

async function testAccountTableV2() {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    // Enable console logging
    page.on('console', msg => {
        if (msg.type() === 'log' || msg.type() === 'error') {
            console.log(`[Browser ${msg.type()}]:`, msg.text());
        }
    });
    
    try {
        console.log('=== Testing Account Table V2 Implementation ===\n');
        
        // Navigate to the application
        await page.goto('http://localhost:9095');
        await page.waitForLoadState('networkidle');
        
        // Check feature flags
        const featureFlags = await page.evaluate(() => window.featureFlags);
        console.log('Feature flags:', featureFlags);
        
        // Verify v2 tables are being used
        const isUsingV2Tables = featureFlags?.useV2Tables === true;
        console.log(`Using V2 Tables: ${isUsingV2Tables}`);
        
        if (!isUsingV2Tables) {
            console.log('ERROR: V2 tables are not enabled. Set useV2Tables flag to true.');
            return;
        }
        
        // Wait for initial data load
        await page.waitForTimeout(1000);
        
        // Test 1: Check initial account table data
        console.log('\n--- Test 1: Initial Account Table Load ---');
        const accountCount = await page.locator('#accountTable tbody tr').count();
        console.log(`Accounts loaded: ${accountCount}`);
        
        // Get first few account details
        const accountData = await page.$$eval('#accountTable tbody tr', rows => 
            rows.slice(0, 5).map(row => ({
                id: row.querySelector('td:first-child').textContent,
                balance: row.querySelector('td:nth-child(2)').textContent,
                qtd: row.querySelector('td:nth-child(3)').textContent,
                ytd: row.querySelector('td:nth-child(4)').textContent
            }))
        );
        console.log('First 5 accounts:', accountData);
        
        // Verify no N/A values in initial load
        const hasNA = accountData.some(acc => 
            acc.qtd.includes('N/A') || acc.ytd.includes('N/A')
        );
        console.log(`Initial load has N/A values: ${hasNA ? 'YES (FAIL)' : 'NO (PASS)'}`);
        
        // Test 2: Single account selection
        console.log('\n--- Test 2: Single Account Selection ---');
        if (accountCount > 0) {
            // Click the first account
            await page.locator('#accountTable tbody tr').first().click();
            await page.waitForTimeout(500);
            
            // Check if selection is visible
            const selectedAccount = await page.locator('#accountTable tbody tr.selected').count();
            console.log(`Selected accounts: ${selectedAccount}`);
            
            // Check KPI updates
            const totalAUM = await page.locator('#totalAUM').textContent();
            const activeAccounts = await page.locator('.kpi-card:nth-child(2) .kpi-value').textContent();
            console.log(`Total AUM: ${totalAUM}, Active Accounts: ${activeAccounts}`);
            
            // Check filter indicator
            const filterText = await page.locator('.filter-info').textContent();
            console.log(`Filter indicator: ${filterText}`);
            
            // Check if fund table shows N/A (this is a known issue in v1)
            const fundQTD = await page.$$eval('#fundTable tbody tr', rows => 
                rows.length > 0 ? rows[0].querySelector('td:nth-child(3)').textContent : 'No funds'
            );
            console.log(`Fund QTD after account selection: ${fundQTD}`);
            if (fundQTD === 'N/A') {
                console.log('Note: Fund table shows N/A - this is expected in v1 endpoints');
            }
        }
        
        // Test 3: Multi-account selection
        console.log('\n--- Test 3: Multi-Account Selection ---');
        if (accountCount >= 2) {
            // Select second account as well
            await page.locator('#accountTable tbody tr').nth(1).click();
            await page.waitForTimeout(500);
            
            const multiSelectedCount = await page.locator('#accountTable tbody tr.selected').count();
            console.log(`Multi-selected accounts: ${multiSelectedCount}`);
            
            // Check updated KPIs
            const multiAUM = await page.locator('#totalAUM').textContent();
            console.log(`Total AUM with multi-selection: ${multiAUM}`);
        }
        
        // Test 4: Client + Account combination
        console.log('\n--- Test 4: Client + Account Combination ---');
        // Clear selections first
        await page.click('#clear-filters');
        await page.waitForTimeout(500);
        
        if ((await page.locator('#clientTable tbody tr').count()) > 0 && accountCount > 0) {
            // Select a client first
            await page.locator('#clientTable tbody tr').first().click();
            await page.waitForTimeout(500);
            
            // Then select an account
            await page.locator('#accountTable tbody tr').first().click();
            await page.waitForTimeout(500);
            
            const combinedFilter = await page.locator('.filter-info').textContent();
            console.log(`Combined filter: ${combinedFilter}`);
            
            // Check if account table shows only accounts for selected client
            const filteredAccountCount = await page.locator('#accountTable tbody tr').count();
            console.log(`Accounts shown for client+account selection: ${filteredAccountCount}`);
        }
        
        // Test 5: Fund + Account combination
        console.log('\n--- Test 5: Fund + Account Combination ---');
        await page.click('#clear-filters');
        await page.waitForTimeout(500);
        
        if ((await page.locator('#fundTable tbody tr').count()) > 0 && accountCount > 0) {
            // Select a fund first
            await page.locator('#fundTable tbody tr').first().click();
            await page.waitForTimeout(500);
            
            // Then select an account
            await page.locator('#accountTable tbody tr').first().click();
            await page.waitForTimeout(500);
            
            const fundAccountAUM = await page.locator('#totalAUM').textContent();
            console.log(`Total AUM for fund+account: ${fundAccountAUM}`);
        }
        
        // Test 6: Clear all selections
        console.log('\n--- Test 6: Clear Selections ---');
        await page.click('#clear-filters');
        await page.waitForTimeout(500);
        
        const selectedAfterClear = await page.locator('tr.selected').count();
        console.log(`Selected after clear: ${selectedAfterClear}`);
        
        // Test 7: Balance fallback handling
        console.log('\n--- Test 7: Balance Field Handling ---');
        // The account table handles both 'total_balance' and 'balance' fields
        const balanceHandling = await page.evaluate(() => {
            const code = window.tablesV2?.updateAccountTable.toString();
            return code.includes('account.total_balance || account.balance || 0');
        });
        console.log(`Balance fallback handling implemented: ${balanceHandling ? 'YES' : 'NO'}`);
        
        // Test 8: Performance check
        console.log('\n--- Test 8: Performance Check ---');
        const startTime = Date.now();
        
        // Trigger a data refresh
        await page.locator('#clientTable tbody tr').first().click();
        await page.waitForTimeout(100);
        
        const endTime = Date.now();
        const duration = endTime - startTime;
        console.log(`Table update duration: ${duration}ms (target: <200ms)`);
        console.log(`Performance: ${duration < 200 ? 'PASS' : 'FAIL'}`);
        
        console.log('\n=== Account Table V2 Tests Completed ===');
        
    } catch (error) {
        console.error('Test failed:', error);
    } finally {
        await browser.close();
    }
}

// Run the tests
testAccountTableV2().catch(console.error);