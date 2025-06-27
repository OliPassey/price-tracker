# Special Pricing Features - Price Tracker

## Overview

The UK Price Tracker now includes enhanced special pricing detection capabilities to identify and prioritize discounted, sale, and special offer prices across supported UK catering sites.

## Features

### 🎯 Special Pricing Detection
- **Strikethrough Pricing**: Detects crossed-out prices with sale prices
- **Was/Now Patterns**: Identifies "Was £X Now £Y" pricing patterns  
- **Offer Labels**: Recognizes sale/discount/special offer badges and containers
- **Percentage Discounts**: Detects "X% OFF" promotional pricing
- **Member/Trade Pricing**: Special pricing for registered customers (JJ Food Service)

### 🚚 Delivery Price Priority
- Automatically prioritizes delivery prices over collection prices
- Identifies delivery-specific special offers
- Handles mixed pricing scenarios (delivery vs collection vs general)

### 🏪 Site-Specific Enhancements

#### JJ Food Service
- Member pricing detection
- Trade pricing identification  
- Bulk discount recognition
- Quantity-based pricing

#### A to Z Catering
- Header-based delivery pricing (H3/H4 elements)
- Inline strikethrough detection
- Special delivery offer containers
- Style-based strikethrough recognition

#### Amazon UK
- Deal price detection
- Strike-through pricing
- Sale badge recognition
- RRP vs Sale price comparison

## Configuration

Special pricing is configured in `config.json`:

```json
{
  "scraping": {
    "special_pricing": {
      "enabled": true,
      "prefer_delivery_prices": true,
      "detect_strikethrough": true,
      "detect_was_now_patterns": true,
      "detect_percentage_discounts": true,
      "min_discount_threshold": 0.05,
      "max_price_difference_ratio": 0.5
    }
  },
  "sites": {
    "jjfoodservice": {
      "selectors": {
        "special_offer": [
          ".special-offer",
          ".member-price",
          "del:contains('£')",
          ".was-price"
        ]
      }
    }
  }
}
```

## Testing

### Test Suite
Run the comprehensive test suite:
```bash
python test_special_pricing.py
```

This tests:
- Price parsing with various formats
- Special pricing context detection
- Site-specific extraction methods
- Mock HTML scenarios

### Debug Tool
Debug real URLs:
```bash
python debug_special_pricing.py <URL> [--verbose]
```

Examples:
```bash
# Debug a JJ Food Service product
python debug_special_pricing.py "https://www.jjfoodservice.com/product/example" --verbose

# Debug an A to Z Catering product  
python debug_special_pricing.py "https://www.atoz-catering.co.uk/product/example"

# Debug an Amazon UK product
python debug_special_pricing.py "https://www.amazon.co.uk/product/example"
```

## How It Works

### 1. Context Detection
The scraper analyzes HTML elements and their parent containers to detect special pricing context:
- Strikethrough elements (`<del>`, `<s>`, `<strike>`)
- CSS styling (`text-decoration: line-through`)
- Keyword patterns (`was`, `now`, `sale`, `offer`, `discount`)
- Percentage discount patterns (`20% off`, etc.)

### 2. Price Extraction
When multiple prices are found:
- **With special context**: Returns the lowest price (offer price)
- **Delivery preference**: Prioritizes delivery over collection prices
- **Multiple prices**: Takes the last/lowest price found

### 3. Site-Specific Logic
Each site has tailored extraction methods:
- **JJ Food Service**: Focuses on member/trade pricing
- **A to Z Catering**: Enhanced header and delivery price detection
- **Amazon UK**: Deal and promotional price recognition

## Examples

### Strikethrough Pricing
```html
<div class="product-price">
    <del>£15.99</del>
    <span class="sale-price">£12.99</span>
</div>
```
**Result**: £12.99 (special offer detected)

### Was/Now Pricing  
```html
<div class="price-container">
    <span>Was £20.50, now £17.25</span>
</div>
```
**Result**: £17.25 (was/now pattern detected)

### Delivery Special Offers
```html
<h3>Delivery: <del>£25.00</del> £19.99</h3>
```
**Result**: £19.99 (delivery + special offer)

## Troubleshooting

### No Special Prices Detected
1. Check if the site uses non-standard markup
2. Add custom selectors to `config.json`
3. Use debug tool to see what selectors are matching
4. Verify special pricing is enabled in config

### Wrong Price Selected
1. Check if delivery preference is correctly configured
2. Verify the HTML structure matches expected patterns
3. Use verbose debugging to see all detected prices
4. Consider adding site-specific selectors

### Performance Issues
1. Reduce the number of special offer selectors
2. Increase delays between requests
3. Use more specific CSS selectors
4. Enable only necessary special pricing features

## Future Enhancements

- **Machine Learning**: Auto-detect pricing patterns
- **More Sites**: Extend to additional UK catering suppliers
- **Price History**: Track special offer frequency and patterns
- **Alerts**: Notify when special offers are detected
- **Comparison**: Cross-site special offer comparison
