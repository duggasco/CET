#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

# Simulate mobile request
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
}

# Get the page
response = requests.get('http://localhost:9095', headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Check if mobile class is applied
body = soup.find('body')
print(f"Mobile class applied: {'mobile' in body.get('class', [])}")

# Analyze table structure
tables = soup.find_all('table')
print(f"\nNumber of tables found: {len(tables)}")

# Simulate iPhone SE viewport (375px wide)
viewport_width = 375

# Calculate approximate character widths at different font sizes
# Assuming roughly 0.6 character width ratio for proportional fonts
char_widths = {
    '3px': 1.8,  # 3px font ≈ 1.8px per character
    '4px': 2.4,  # 4px font ≈ 2.4px per character
    '5px': 3.0,  # 5px font ≈ 3.0px per character
}

# Check each table
for i, table in enumerate(tables):
    table_id = table.get('id', f'table_{i}')
    print(f"\n--- Analyzing {table_id} ---")
    
    # Get headers
    headers = table.find_all('th')
    if headers:
        print("Headers:", [th.text.strip() for th in headers])
    
    # Analyze column widths based on CSS
    # Name column: 40% = 150px
    # Balance column: 25% = 93.75px
    # QTD/YTD columns: 17.5% each = 65.625px each
    
    col_widths = [150, 93.75, 65.625, 65.625]
    col_names = ['Name/ID', 'Balance', 'QTD %', 'YTD %']
    
    # Get sample data from first row
    first_row = table.find('tbody', {'tr': True})
    if first_row:
        cells = first_row.find_all('td')
        if cells:
            print("\nFirst row data:")
            for j, (cell, width, name) in enumerate(zip(cells[:4], col_widths, col_names)):
                text = cell.text.strip()
                font_size = '3px' if 'account' in table_id.lower() and j == 0 else '4px'
                char_width = char_widths.get(font_size, 2.4)
                
                # Account for padding (1px x 2px = 4px total horizontal)
                available_width = width - 4
                max_chars = int(available_width / char_width)
                
                fits = len(text) <= max_chars
                status = "✓ FITS" if fits else "✗ TRUNCATED"
                
                print(f"  {name}: '{text}' ({len(text)} chars)")
                print(f"    Font: {font_size}, Available: {available_width:.1f}px, Max chars: {max_chars}")
                print(f"    Status: {status}")

print("\n--- Summary ---")
print(f"Viewport width: {viewport_width}px")
print("Font sizes: 4px general, 3px for account IDs")
print("With current settings, text may be truncated if:")
print("- Client names > 62 characters")
print("- Fund names > 62 characters") 
print("- Account IDs > 50 characters")
print("- Balance values > 39 characters")
print("- Percentages > 27 characters")