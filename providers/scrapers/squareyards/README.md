# SquareYards Scraper

Provider-specific scraper for extracting property listings from SquareYards.

## Structure

```
squareyards/
├── squareyards_scraper.py      # Main scraper implementation
├── schemas/
│   └── schema.json              # CSS extraction schema (auto-generated)
├── prompts/
│   ├── schema_generation_prompt.txt          # LLM prompt for schema generation
│   ├── relevance_scoring_prompt.txt          # Simple scoring prompt
│   └── relevance_scoring_prompt_structured.txt # Detailed scoring prompt
└── sample_html/
    └── squareyards_sample.html  # Sample HTML for schema generation
```

## Usage

```python
from providers.scrapers.squareyards.squareyards_scraper import SquareYardsScraper

scraper = SquareYardsScraper()
properties = await scraper.scrape(url)
```

## Key Features

- **CSS-based extraction**: Uses CSS selectors to extract property data
- **Schema generation**: Auto-generates extraction schema from sample HTML
- **Field mapping**: Extracts standard fields: title, location, price, bedrooms, bathrooms, area, facing, parking, flooring, furnishing, description

## Extracted Fields

- `title` - Property title/heading
- `location` - Area/locality name
- `price` - Sale/rental price
- `bedrooms` - Number of BHK/rooms
- `bathrooms` - Number of bathrooms
- `area` - Carpet or built-up area
- `facing` - Property facing direction
- `parking` - Parking availability
- `flooring` - Flooring type
- `furnishing` - Furnishing status
- `description` - Property description

## Notes

- SquareYards provides comprehensive field extraction
- Schema is cached and only generated once
- Uses Gemini 2.5 Flash for schema generation
