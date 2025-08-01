const { chromium } = require('playwright');

async function testFundTableV2() {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    // Enable console logging
    page.on('console', msg => {
        if (msg.type() === 'log' || msg.type() === 'error') {
            console.log(`[Browser ${msg.type()}]:`, msg.text());
        }
    });
    
    try {
        console.log('=== Testing Fund Table V2 Implementation ===\n');
        
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
        
        // Test 1: Check initial fund table data
        console.log('\n--- Test 1: Initial Fund Table Load ---');
        const fundCount = await page.locator('#fundTable tbody tr').count();
        console.log(`Funds loaded: ${fundCount}`);
        
        // Get all fund names
        const fundNames = await page.$$eval('#fundTable tbody tr', rows => 
            rows.map(row => row.querySelector('td:first-child').textContent)
        );
        console.log('Available funds:', fundNames);
        
        // Test 2: Single fund selection
        console.log('\n--- Test 2: Single Fund Selection ---');
        if (fundCount > 0) {
            // Click the first fund
            await page.locator('#fundTable tbody tr').first().click();
            await page.waitForTimeout(500);
            
            // Check if selection is visible
            const selectedFund = await page.locator('#fundTable tbody tr.selected').count();
            console.log(`Selected funds: ${selectedFund}`);
            
            // Verify selection state
            const selectedFundData = await page.$$eval('#fundTable tbody tr.selected', rows => 
                rows.map(row => ({
                    name: row.querySelector('td:first-child').textContent,
                    balance: row.querySelector('td:nth-child(2)').textContent,
                    qtd: row.querySelector('td:nth-child(3)').textContent,
                    ytd: row.querySelector('td:nth-child(4)').textContent
                }))
            );
            console.log('Selected fund data:', selectedFundData);
            
            // Check KPI updates
            const totalAUM = await page.locator('#totalAUM').textContent();
            console.log(`Total AUM after selection: ${totalAUM}`);
            
            // Check filter indicator
            const filterText = await page.locator('.filter-info').textContent();
            console.log(`Filter indicator: ${filterText}`);
        }
        
        // Test 3: Multi-fund selection
        console.log('\n--- Test 3: Multi-Fund Selection ---');
        if (fundCount >= 2) {
            // Select second fund as well
            await page.locator('#fundTable tbody tr').nth(1).click();
            await page.waitForTimeout(500);
            
            const multiSelectedCount = await page.locator('#fundTable tbody tr.selected').count();
            console.log(`Multi-selected funds: ${multiSelectedCount}`);
            
            // Check updated KPIs
            const multiAUM = await page.locator('#totalAUM').textContent();
            console.log(`Total AUM with multi-selection: ${multiAUM}`);
            
            // Verify tables show intersection data
            const clientCount = await page.locator('#clientTable tbody tr').count();
            const accountCount = await page.locator('#accountTable tbody tr').count();
            console.log(`Filtered clients: ${clientCount}, Filtered accounts: ${accountCount}`);
        }
        
        // Test 4: Fund + Client combination
        console.log('\n--- Test 4: Fund + Client Combination ---');
        if ((await page.locator('#clientTable tbody tr').count()) > 0) {
            // Select a client
            await page.locator('#clientTable tbody tr').first().click();
            await page.waitForTimeout(500);
            
            const combinedFilter = await page.locator('.filter-info').textContent();
            console.log(`Combined filter: ${combinedFilter}`);
            
            // Check if data represents intersection
            const intersectionAUM = await page.locator('#totalAUM').textContent();
            console.log(`Intersection AUM: ${intersectionAUM}`);
        }
        
        // Test 5: Clear all selections
        console.log('\n--- Test 5: Clear Selections ---');
        await page.click('#clear-filters');
        await page.waitForTimeout(500);
        
        const selectedAfterClear = await page.locator('tr.selected').count();
        console.log(`Selected after clear: ${selectedAfterClear}`);
        
        // Test 6: QTD/YTD values
        console.log('\n--- Test 6: QTD/YTD Values ---');
        const qtdYtdData = await page.$$eval('#fundTable tbody tr', rows => 
            rows.slice(0, 3).map(row => ({
                fund: row.querySelector('td:first-child').textContent,
                qtd: row.querySelector('td:nth-child(3)').textContent,
                ytd: row.querySelector('td:nth-child(4)').textContent
            }))
        );
        console.log('QTD/YTD values for first 3 funds:');
        qtdYtdData.forEach(data => {
            console.log(`  ${data.fund}: QTD=${data.qtd}, YTD=${data.ytd}`);
        });
        
        // Verify no "N/A" values
        const hasNA = qtdYtdData.some(data => 
            data.qtd.includes('N/A') || data.ytd.includes('N/A')
        );
        console.log(`Contains N/A values: ${hasNA ? 'YES (FAIL)' : 'NO (PASS)'}`);
        
        // Test 7: Text filter with fund selection
        console.log('\n--- Test 7: Text Filter + Fund Selection ---');
        await page.fill('#fundTickerFilter', 'PRIME');
        await page.click('#applyFilters');
        await page.waitForTimeout(1000);
        
        const filteredFundCount = await page.locator('#fundTable tbody tr').count();
        console.log(`Funds after text filter: ${filteredFundCount}`);
        
        if (filteredFundCount > 0) {
            await page.locator('#fundTable tbody tr').first().click();
            await page.waitForTimeout(500);
            
            const textPlusFundAUM = await page.locator('#totalAUM').textContent();
            console.log(`AUM with text filter + fund selection: ${textPlusFundAUM}`);
        }
        
        console.log('\n=== Fund Table V2 Tests Completed ===');
        
    } catch (error) {
        console.error('Test failed:', error);
    } finally {
        await browser.close();
    }
}

// Run the tests
testFundTableV2().catch(console.error);