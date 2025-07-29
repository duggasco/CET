# Mobile View Documentation

## Overview
The Client Exploration Tool now includes automatic mobile detection and a responsive mobile-friendly view that activates when accessing from mobile devices.

## Mobile Detection
The application automatically detects mobile devices using three criteria:
1. **User Agent Detection**: Matches common mobile device patterns (iPhone, iPad, Android, etc.)
2. **Touch Support**: Checks for touch capabilities
3. **Screen Width**: Activates for screens ≤ 768px wide

When detected as mobile, the `<body>` element receives a `mobile` class that triggers mobile-specific styling.

## Mobile Features

### Layout Changes
- **KPI Cards**: Switch from 4-column grid to single column stack
- **Charts and Tables**: Change from side-by-side to stacked vertical layout
- **Scrolling**: Natural page scrolling enabled (removes desktop's fixed-height restriction)

### Table Optimizations
- Horizontal scrolling with smooth momentum
- Sticky table headers remain visible while scrolling
- Touch-optimized row heights (44px minimum)
- Improved touch targets for better interaction

### Chart Adjustments
- Smaller font sizes (8px vs 9px)
- Reduced tick marks for cleaner display
- Maximum height constraints (180px) to fit mobile screens
- Maintained interactivity for drill-down functionality

### Typography & Spacing
- Slightly larger fonts for better readability
- Increased padding on interactive elements
- Optimized whitespace for mobile viewing

## Testing Mobile View

### On Desktop Browser
1. Open Chrome DevTools (F12)
2. Click the device toggle toolbar icon
3. Select a mobile device preset (e.g., iPhone 14 Pro)
4. Refresh the page

### On Actual Mobile Device
Simply navigate to the application URL - mobile detection is automatic.

### Test Files
- `test_mobile.html` - Visual device frame testing
- `mobile_demo.html` - Side-by-side desktop/mobile comparison
- `test_mobile_view.py` - Automated user agent testing

## Technical Implementation

### JavaScript (app.js)
```javascript
function detectMobile() {
    const userAgent = navigator.userAgent || navigator.vendor || window.opera;
    const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
    const touchSupport = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    const screenWidth = window.innerWidth <= 768;
    
    return mobileRegex.test(userAgent) || (touchSupport && screenWidth);
}
```

### CSS (style.css)
Mobile styles are applied when `body.mobile` class is present:
```css
body.mobile .kpi-section {
    grid-template-columns: 1fr;
}

body.mobile .split-content {
    flex-direction: column;
}
```

## Cache Busting
To ensure users always get the latest mobile updates:
- CSS and JS files include timestamp-based query strings: `?v=1234567890`
- HTML pages have no-cache headers
- Static assets can be cached long-term due to versioning

## Browser Support
- iOS Safari 12+
- Chrome for Android 80+
- Samsung Internet 10+
- All modern mobile browsers

## Performance Considerations
- Animations disabled on mobile for better performance
- Optimized chart rendering with fewer data points displayed
- Efficient touch event handling
- Hardware-accelerated scrolling with `-webkit-overflow-scrolling: touch`