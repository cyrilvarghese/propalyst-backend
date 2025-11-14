# MagicBricks Schema Generation - Text Content Based Selectors

## Goal
Update the MagicBricks schema generation prompt so that the LLM (Gemini) generates CSS selectors that match labels by their TEXT CONTENT rather than by DOM position (nth-child/nth-of-type).

## Problem with Position-Based Selectors
Original approach used fragile selectors:
```css
:nth-of-type(4) /* Parking */
:nth-of-type(5) /* Washroom */
```

Issues:
- Breaks when label order changes
- Breaks when DOM structure varies
- Not resilient across different properties

## Solution: Text Content-Based Selectors

### Updated Prompt Strategy
The new `magicbricks_schema_generation_prompt.txt` now explicitly instructs Gemini to:

1. **Find labels by their TEXT CONTENT**, not position
2. **Navigate to adjacent value element** using sibling selectors
3. **Use semantic selectors** that check for label text like "Parking", "Washroom", etc.

### Example Selectors (What Gemini Should Generate)

For "Parking" field:
```css
.mb-srp__card__summary-commercial__list--item:has(.mb-srp__card__summary--label:contains('Parking')) .mb-srp__card__summary--value
```

For "Washroom" field:
```css
.mb-srp__card__summary-commercial__list--item:has(.mb-srp__card__summary--label:contains('Washroom')) .mb-srp__card__summary--value
```

For "Cabins" (nested in column):
```css
.mb-srp__card__summary-commercial--column:has(.mb-srp__card__summary-commercial--label:contains('Cabins')) .mb-srp__card__summary-commercial--value
```

## HTML Structure Reference
```html
<div class="mb-srp__card__summary-commercial__list">
  <!-- Parking item -->
  <div class="mb-srp__card__summary-commercial__list--item">
    <div class="mb-srp__card__summary--label">Parking</div>
    <div class="mb-srp__card__summary--value">2 Covered</div>
  </div>

  <!-- Washroom item -->
  <div class="mb-srp__card__summary-commercial__list--item">
    <div class="mb-srp__card__summary--label">Washroom</div>
    <div class="mb-srp__card__summary--value">2</div>
  </div>

  <!-- Cabins/Seats (nested columns) -->
  <div class="mb-srp__card__summary-commercial__list--item column-2">
    <div class="mb-srp__card__summary-commercial--column">
      <div class="mb-srp__card__summary-commercial--label">Cabins</div>
      <div class="mb-srp__card__summary-commercial--value">2</div>
    </div>
    <div class="mb-srp__card__summary-commercial--column">
      <div class="mb-srp__card__summary-commercial--label">Seats</div>
      <div class="mb-srp__card__summary-commercial--value">40</div>
    </div>
  </div>
</div>
```

## Prompt Key Changes

### Before
```
- DO NOT use nth-child or nth-of-type selectors
- INSTEAD, create selectors that find the element containing the specific label text
```

### After (More Specific)
```
- Generate selectors that find the LABEL element by its TEXT CONTENT
- Then extract the adjacent VALUE sibling
- For "Parking": Generate a selector that finds label text "Parking" and gets its sibling value
- For "Washroom": Generate a selector that finds label text "Washroom" and gets its sibling value
- For nested items, include parent container in selector logic
```

## Next Steps

1. **Delete the old schema** (if it exists):
   ```bash
   rm providers/scrapers/schemas/magicbricks_schema.json
   ```

2. **First scrape will trigger generation** with new prompt
   - Gemini will analyze the HTML
   - Generate text-based selectors
   - Save schema to file

3. **Verify the generated schema** contains:
   - `:contains()` or similar text matching for labels
   - Adjacent sibling navigation to values
   - No nth-child/nth-of-type selectors

4. **Test extraction** works correctly with new selectors

## How It Works in Execution

```
1. MagicBricksScraper.scrape() called
2. Schema file doesn't exist
3. Loads sample HTML: magicbricks_sample.html
4. Loads prompt: magicbricks_schema_generation_prompt.txt
5. Calls Gemini with prompt + sample HTML
6. Gemini analyzes HTML + instructions
7. Gemini generates JSON schema with TEXT-BASED selectors
8. Schema saved to: providers/scrapers/schemas/magicbricks_schema.json
9. JsonCssExtractionStrategy uses schema to extract data
10. Returns properties with correctly mapped fields
```

## Expected Schema Structure

The generated schema should look similar to:

```json
{
  "baseSelector": ".mb-srp__card",
  "fields": [
    {
      "name": "title",
      "selector": "h2.mb-srp__card--title",
      "type": "text"
    },
    {
      "name": "parking",
      "selector": ".mb-srp__card__summary-commercial__list--item:has(.mb-srp__card__summary--label:contains('Parking')) .mb-srp__card__summary--value",
      "type": "text"
    },
    {
      "name": "washrooms",
      "selector": ".mb-srp__card__summary-commercial__list--item:has(.mb-srp__card__summary--label:contains('Washroom')) .mb-srp__card__summary--value",
      "type": "text"
    },
    ...
  ]
}
```

## Testing the Iteration

To test if Gemini generates the correct selectors:
1. Ensure schema file is deleted
2. Run a scrape operation
3. Check the generated schema file
4. Verify selectors use `:contains()` or text matching
5. Verify no nth-child/nth-of-type selectors exist
6. Verify extraction works with varying label orders

## Debugging

If extraction fails, check:
- Does the schema contain text-based selectors?
- Are `:contains()` or `:has()` selectors properly formatted?
- Are label names exactly matching HTML (case-sensitive)?
- Are sibling relationships correct?
