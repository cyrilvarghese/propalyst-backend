# Schema Generation Strategy - Label-Based & Robust Selectors

## Overview
Instead of hardcoding selectors or using post-processing logic, we now instruct the LLM (Gemini) to generate intelligent CSS selectors that are resistant to DOM structure changes.

## Key Changes

### 1. Updated Prompts
Both SquareYards and MagicBricks schema generation prompts now include **CRITICAL INSTRUCTIONS** that guide the LLM to:

#### MagicBricks (`magicbricks_schema_generation_prompt.txt`)
- **Generate label-based selectors** instead of nth-child selectors
- Use patterns like: `.parent-class:has(.label:contains('Label Text')) .value-class`
- Create selectors that find the label first, then extract the adjacent value
- Examples:
  - Find "Parking" label, then get its value
  - Find "Washroom" label, then get its value
  - Work regardless of label order

#### SquareYards (`schema_generation_prompt.txt`)
- Prefer class names and data attributes
- Use icon-based patterns: find `.icon-beds`, then extract adjacent text
- Use parent-child relationships and sibling selectors
- Avoid position-based selectors

### 2. Simplified Scraper
The MagicBricksScraper is now back to its simple form:
- No post-processing logic
- No label-to-field mapping
- LLM handles selector generation → JsonCssExtractionStrategy handles extraction

## How It Works

### Before (Fragile Approach)
```
HTML (varies) → Fixed position-based selectors → Breaks ❌
```

### Now (Robust Approach)
```
HTML (any structure) → LLM generates smart selectors → Works ✓
                       (label-based, content-aware)
```

### Execution Flow
1. First time: Scraper loads sample HTML
2. LLM analyzes HTML with new prompt
3. LLM generates intelligent selectors (label-based, not position-based)
4. Schema is saved
5. JsonCssExtractionStrategy uses the smart selectors
6. Result: Extracted fields match labels correctly regardless of order

## Key Prompt Instructions

### MagicBricks
```
DO NOT use nth-child or nth-of-type selectors - these are fragile
INSTEAD: Create selectors that find the element containing specific label text
Example: ".parent-class:has(.label:contains('Label Text')) .value-class"
```

### SquareYards
```
Prefer using specific class names and data attributes over nth-child selectors
For icon-based fields: find the icon (like .icon-beds) then get adjacent text
Use parent-child relationships and sibling selectors
```

## Benefits

✓ **No Manual Post-Processing**: Schema handles everything
✓ **Resilient to DOM Changes**: Selectors based on content, not position
✓ **LLM Intelligence**: Gemini understands HTML semantics
✓ **Auto-Generation**: Schema regenerates if deleted
✓ **Maintainable**: Prompts guide selector generation logic

## When Schema is Generated

1. **First run**: No schema file exists
   - Scraper loads sample HTML
   - LLM generates schema using new prompt
   - Schema saved to file
   - JsonCssExtractionStrategy uses it

2. **Subsequent runs**: Schema exists
   - Scraper uses saved schema
   - JsonCssExtractionStrategy extracts data

3. **To regenerate**: Delete schema file
   - `rm providers/scrapers/schemas/magicbricks_schema.json`
   - Next run will regenerate with updated logic

## Technical Details

### CSS Selector Patterns LLM May Generate

For label-value pairs:
- `.container:has(.label:contains('Parking')) .value` - Find container with label, get value
- `.item:has(.label-class) + .value-class` - Sibling pattern
- `[data-label='Parking'] ~ .value` - Data attribute pattern

For icon-based fields:
- `.icon-beds ~ .count` - Icon followed by count
- `.property-meta:has(.icon-bath) .number` - Container with icon

### Browser Support
Modern CSS selectors used by Crawl4AI support:
- `:has()` pseudo-class (structural pseudo-class)
- `:contains()` pseudo-class (text matching)
- `~` (general sibling combinator)
- `+` (adjacent sibling combinator)

## Testing

To verify the approach works:
1. Delete the schema file
2. Run a scrape operation
3. Check that it auto-generates
4. Verify extracted fields have correct labels mapped to values

Example test:
```python
# Should now correctly extract:
parking: "2 Covered"
washrooms: "2"
pantry: "Wet Pantry/Cafeteria"
# Regardless of order in HTML
```

## Future Improvements

- Monitor if LLM generates ideal selectors
- Refine prompt based on LLM outputs
- Add more examples to prompt if needed
- Consider using XPath as fallback if CSS proves insufficient
