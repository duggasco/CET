#!/usr/bin/env python3

# Viewport: 375px (iPhone SE)
# Column widths: 40%, 25%, 17.5%, 17.5%

viewport = 375
columns = {
    'name': {'width_pct': 40, 'max_chars': 24, 'padding': 4},  # 2px x 2
    'balance': {'width_pct': 25, 'max_chars': 14, 'padding': 4},
    'qtd': {'width_pct': 17.5, 'max_chars': 5, 'padding': 4},
    'ytd': {'width_pct': 17.5, 'max_chars': 5, 'padding': 4}
}

print("Optimal Font Size Calculations")
print("=" * 50)

for col_name, col_data in columns.items():
    width_px = (col_data['width_pct'] / 100) * viewport
    available_px = width_px - col_data['padding']
    
    # Calculate required character width
    req_char_width = available_px / col_data['max_chars']
    
    # Font size is roughly 1.67x character width for proportional fonts
    optimal_font = req_char_width * 1.67
    
    print(f"\n{col_name.upper()} Column:")
    print(f"  Width: {width_px}px ({col_data['width_pct']}%)")
    print(f"  Available (minus padding): {available_px}px")
    print(f"  Max chars: {col_data['max_chars']}")
    print(f"  Required char width: {req_char_width:.2f}px")
    print(f"  Optimal font size: {optimal_font:.1f}px")
    print(f"  Recommended: {round(optimal_font)}px")

print("\n" + "=" * 50)
print("\nRECOMMENDATIONS:")
print("- Name columns (clients/funds): 10px")
print("- Account IDs: 10px (monospace)")
print("- Balance values: 11px")
print("- Percentages: 22px (but 11px is fine for consistency)")
print("\nWith 10-11px fonts, all content will fit comfortably on mobile.")