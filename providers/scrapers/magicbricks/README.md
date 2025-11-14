# MagicBricks Scraper

Provider-specific scraper for extracting property listings from MagicBricks.

## Structure

```
magicbricks/
├── magicbricks_scraper.py      # Main scraper implementation
├── schemas/
│   └── schema.json              # XPath extraction schema (auto-generated)
├── prompts/
│   ├── schema_generation_prompt.txt          # LLM prompt for schema generation
│   ├── relevance_scoring_prompt.txt          # Simple scoring prompt
│   └── relevance_scoring_prompt_structured.txt # Detailed scoring prompt
└── sample_html/
    └── magicbricks_residential_sale_sample.html # Sample HTML for schema generation
```

## Usage

```python
from providers.scrapers.magicbricks.magicbricks_scraper import MagicBricksScraper

scraper = MagicBricksScraper()
properties = await scraper.scrape(url)
```

## Key Features

- **XPath-based extraction**: Uses XPath queries with data-summary attributes
- **Label-based selectors**: Matches fields by label text rather than DOM position
- **Schema generation**: Auto-generates extraction schema from sample HTML
- **Field mapping**: Extracts available fields from MagicBricks listings

## Extracted Fields

- `title` - Property title/heading
- `price` - Sale/rental price
- `super_area` - Carpet area (built-up area)
- `facing` - Property facing direction
- `parking` - Parking availability
- `furnishing` - Furnishing status
- `bathroom` - Number of bathrooms
- `floor` - Floor number
- `balcony` - Number of balconies
- `description` - Property description

## Important Notes

### Limited Field Availability

MagicBricks schema **does not extract**:
- Bedrooms/BHK count (not in current schema)
- Location/area name (not in current schema)
- Property type (not in current schema)
- Image URLs (not in current schema)

### Scoring Implications

When scoring MagicBricks properties:
- `bedrooms` is set to "Not specified"
- `location` is set to "N/A"
- `property_type` is set to "Not specified"
- Relevance scoring only evaluates available fields

Use `RelevanceScoringService.score_properties_batch_magicbricks()` for MagicBricks-specific scoring that properly handles limited field availability.

## Schema Generation

- Uses OpenAI GPT-4O for schema generation
- Generates XPath selectors with data-summary attributes
- Label-based selectors ensure field matching by text content
- Schema is cached and only generated once
