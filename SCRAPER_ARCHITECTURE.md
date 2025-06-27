# Price Tracker - Scraper Architecture

## Current Structure

### 1. **`scraper.py` - Base Scraper Class**
- **Purpose**: Foundation class for all price scraping
- **Handles**: Generic e-commerce sites (Amazon.com, eBay, Walmart, etc.)
- **Key Features**:
  - Base `PriceScraper` class with HTTP session management
  - Anti-bot measures (headers, delays, retries)
  - Generic price extraction methods
  - Site detection logic

### 2. **`uk_scraper.py` - UK Catering Specialist**
- **Purpose**: Specialized scraper for UK catering supply websites
- **Handles**: JJ Food Service, A to Z Catering, Amazon UK
- **Key Features**:
  - Inherits from `PriceScraper` base class
  - UK currency handling (£ symbol)
  - Delivery vs Collection price prioritization
  - Special pricing detection (offers, strikethrough, was/now pricing)
  - Site-specific CSS selectors (e.g., `.my-price.price-offer` for A to Z)

### 3. **`scraper_manager.py` - Orchestration Layer**
- **Purpose**: Routes scraping tasks to appropriate scrapers
- **Logic**: 
  - Detects UK catering sites → uses `UKCateringScraper`
  - Detects other sites → uses base `PriceScraper`
  - Manages concurrent requests and error handling

## Site Mapping

### UK Catering Sites (UKCateringScraper):
- `jjfoodservice` → JJ Food Service
- `atoz_catering` → A to Z Catering 
- `amazon_uk` → Amazon UK

### International Sites (PriceScraper):
- `amazon` → Amazon.com
- `ebay` → eBay
- `walmart` → Walmart
- *(Future sites can be added here)*

## Key Benefits of Current Structure

✅ **Separation of Concerns**: UK-specific logic is isolated
✅ **Extensibility**: Easy to add new UK sites or international sites
✅ **Maintainability**: Changes to UK logic don't affect international scraping
✅ **Specialization**: UK scraper handles currency, delivery pricing, special offers

## Recommendations

### ✅ **KEEP CURRENT STRUCTURE** - It's well-designed!

The separation between `scraper.py` and `uk_scraper.py` is actually **good architecture** because:

1. **UK catering sites have unique requirements** (delivery vs collection, £ pricing, special offers)
2. **International sites have different patterns** (USD pricing, different site structures)
3. **Easy to maintain and extend** each scraper independently

### Minor Improvements Made:

1. **Enhanced site detection** in base scraper
2. **Added helper methods** to determine scraper routing
3. **Improved scraper manager** logic for clarity
4. **Fixed A to Z pricing** with `.my-price.price-offer` selector

## Final File Structure

```
src/
├── scraper.py           # Base scraper (international sites)
├── uk_scraper.py        # UK catering specialist 
├── scraper_manager.py   # Orchestration layer
├── config.py           # Configuration management
├── database.py         # Data persistence
└── web_ui.py           # Flask web interface
```

This structure supports both current UK catering needs and future expansion to international e-commerce sites.
