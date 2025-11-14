# Label-Based CSS Selector Patterns

## Problem with Position-Based Selectors

Position-based selectors like `nth-child()`, `nth-of-type()` are fragile:

```html
<!-- Property 1: Parking is 4th item -->
<div class="items">
  <div class="item">Carpet Area</div>
  <div class="item">Furnishing Status</div>
  <div class="item">Column Items</div>
  <div class="item">Parking</div>      ← :nth-of-type(4)
</div>

<!-- Property 2: Parking is 3rd item (columns moved) -->
<div class="items">
  <div class="item">Carpet Area</div>
  <div class="item">Furnishing Status</div>
  <div class="item">Parking</div>      ← :nth-of-type(3) (selector breaks!)
</div>
```

## Solution: Label-Based Selectors

Find the label text first, then extract the value.

### Pattern 1: Direct Label Matching with :has() and :contains()

```css
/* Find the item containing "Parking" label, then get the value */
.mb-srp__card__summary-commercial__list--item:has(.mb-srp__card__summary--label:contains('Parking')) .mb-srp__card__summary--value

/* Find the item containing "Washroom" label, then get the value */
.mb-srp__card__summary-commercial__list--item:has(.mb-srp__card__summary--label:contains('Washroom')) .mb-srp__card__summary--value
```

**Advantage**: Works regardless of item order

### Pattern 2: Sibling Selector Pattern

```css
/* Label element followed by adjacent sibling value */
.mb-srp__card__summary--label:contains('Parking') + .mb-srp__card__summary--value

/* Or with different structure */
.mb-srp__card__summary--label:contains('Cabins') ~ .mb-srp__card__summary-commercial--value
```

**Advantage**: Direct relationship between label and value

### Pattern 3: Data Attribute Pattern

```css
/* Use data attributes if available */
.summary-item[data-label='parking'] .value

/* Or attribute contains */
.summary-item[data-field*='park'] .value
```

**Advantage**: Very explicit and unlikely to change

### Pattern 4: Combined Pattern (Most Robust)

```css
/* Find parent with label, then navigate to value */
.mb-srp__card__summary-commercial__list:has(.mb-srp__card__summary--label:contains('Parking')) .mb-srp__card__summary--value

/* Or with class matching */
.mb-srp__card__summary-commercial:has(.label-parking) .mb-srp__card__summary--value
```

**Advantage**: Scoped to specific property card

## Real-World Example: MagicBricks

### HTML Structure
```html
<div class="mb-srp__card">
  <div class="mb-srp__card__summary-commercial">
    <div class="mb-srp__card__summary-commercial__list">

      <!-- Parking Item -->
      <div class="mb-srp__card__summary-commercial__list--item">
        <div class="mb-srp__card__summary--label">Parking</div>
        <div class="mb-srp__card__summary--value">2 Covered</div>
      </div>

      <!-- Washroom Item -->
      <div class="mb-srp__card__summary-commercial__list--item">
        <div class="mb-srp__card__summary--label">Washroom</div>
        <div class="mb-srp__card__summary--value">2</div>
      </div>

    </div>
  </div>
</div>
```

### Selectors

```json
{
  "fields": [
    {
      "name": "parking",
      "selector": ".mb-srp__card__summary-commercial__list--item:has(.mb-srp__card__summary--label:contains('Parking')) .mb-srp__card__summary--value",
      "type": "text"
    },
    {
      "name": "washrooms",
      "selector": ".mb-srp__card__summary-commercial__list--item:has(.mb-srp__card__summary--label:contains('Washroom')) .mb-srp__card__summary--value",
      "type": "text"
    }
  ]
}
```

## SquareYards: Icon-Based Pattern

### HTML Structure
```html
<div class="sy-property-card">
  <div class="sy-property-specs">
    <div class="spec-item">
      <span class="icon icon-beds"></span>
      <span class="spec-value">4 BHK</span>
    </div>
    <div class="spec-item">
      <span class="icon icon-bath"></span>
      <span class="spec-value">3 Baths</span>
    </div>
  </div>
</div>
```

### Selectors

```json
{
  "fields": [
    {
      "name": "bedrooms",
      "selector": ".icon-beds ~ .spec-value",
      "type": "text"
    },
    {
      "name": "bathrooms",
      "selector": ".icon-bath ~ .spec-value",
      "type": "text"
    }
  ]
}
```

**Advantage**: Icons are stable identifiers

## Comparison Table

| Approach | Robustness | Example | Works When... |
|----------|-----------|---------|--------------|
| nth-child | ❌ Low | `:nth-of-type(4)` | Order is fixed |
| Label text | ✅ High | `:has(.label:contains('Parking'))` | Label text exists |
| Icon-based | ✅ High | `.icon-beds ~ .value` | Icons are consistent |
| Data attrs | ✅ High | `[data-field='parking']` | Attrs are added to HTML |
| Sibling | ✅ Medium | `.label + .value` | HTML structure is consistent |

## Browser/Tool Support

These patterns work in:
- ✅ Modern browsers (Chrome 105+, Firefox 78+, Safari 15.4+)
- ✅ Crawl4AI (uses browser engine)
- ✅ Cheerio (with limitations)
- ✅ Puppeteer / Playwright

## LLM Guidance in Prompts

The updated prompts instruct Gemini to:

1. **Analyze HTML structure** to identify label-value pairs
2. **Prefer content-based selectors** over position-based
3. **Use icons as anchors** when available
4. **Create resilient selectors** that work across variations
5. **Avoid nth-child/nth-of-type** as primary selectors

This way, the LLM generates the schema intelligently, without requiring post-processing.
