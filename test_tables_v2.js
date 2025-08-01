const { chromium } = require('playwright');

async function testTablesV2() {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    
    // Enable console logging
    page.on('console', msg => {
        if (msg.type() === 'log' || msg.type() === 'error') {
            console.log(`[Browser ${msg.type()}]:`, msg.text());
        }
    });
    
    try {
        console.log('=== Testing Tables V2 Implementation ===\n');
        
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
            console.log('WARNING: V2 tables are not enabled. Set useV2Tables flag to true.');
        }
        
        // Wait for initial data load
        await page.waitForTimeout(1000);
        
        // Test 1: Check initial table data
        console.log('\n--- Test 1: Initial Table Load ---');
        const clientCount = await page.locator('#clientTable tbody tr').count();
        const fundCount = await page.locator('#fundTable tbody tr').count();
        const accountCount = await page.locator('#accountTable tbody tr').count();
        
        console.log(`Clients loaded: ${clientCount}`);
        console.log(`Funds loaded: ${fundCount}`);
        console.log(`Accounts loaded: ${accountCount}`);
        
        // Test 2: Select a client and verify table updates
        console.log('\n--- Test 2: Client Selection ---');
        if (clientCount > 0) {
            // Click the first client
            await page.locator('#clientTable tbody tr').first().click();
            await page.waitForTimeout(500);
            
            // Check if selection is visible
            const selectedClient = await page.locator('#clientTable tbody tr.selected').count();
            console.log(`Selected clients: ${selectedClient}`);
            
            // Check console for v2 table messages
            await page.waitForTimeout(500);
        }
        
        // Test 3: Apply text filter
        console.log('\n--- Test 3: Text Filter ---');
        await page.fill('#clientNameFilter', 'Acme');
        await page.click('#applyFilters');
        await page.waitForTimeout(1000);
        
        const filteredClientCount = await page.locator('#clientTable tbody tr').count();
        console.log(`Filtered clients: ${filteredClientCount}`);
        
        // Test 4: Multi-selection
        console.log('\n--- Test 4: Multi-Selection ---');
        // Clear filters first
        await page.click('#clear-filters');
        await page.waitForTimeout(500);
        
        // Select multiple items
        const clientRows = page.locator('#clientTable tbody tr');
        if (await clientRows.count() >= 2) {
            await clientRows.nth(0).click();
            await clientRows.nth(1).click();
            await page.waitForTimeout(500);
            
            const selectedCount = await page.locator('#clientTable tbody tr.selected').count();
            console.log(`Multi-selected clients: ${selectedCount}`);
        }
        
        // Test 5: Check KPI updates
        console.log('\n--- Test 5: KPI Updates ---');
        const totalAUM = await page.locator('#totalAUM').textContent();
        console.log(`Total AUM: ${totalAUM}`);
        
        // Test 6: Clear all selections
        console.log('\n--- Test 6: Clear Selections ---');
        await page.click('#clear-filters');
        await page.waitForTimeout(500);
        
        const selectedAfterClear = await page.locator('tr.selected').count();
        console.log(`Selected after clear: ${selectedAfterClear}`);
        
        console.log('\n=== All Tests Completed ===');
        
    } catch (error) {
        console.error('Test failed:', error);
    } finally {
        await browser.close();
    }
}

// Run the tests
testTablesV2().catch(console.error);