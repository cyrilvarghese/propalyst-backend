 

# Decision: Two raw tables per source for MVP

## Context

You are scraping multiple property portals (MagicBricks, SquareYards, and more in future) to build an intelligent property search and advisory layer.

Key constraints:

* Each portal has its own schema and naming.
* You are currently in MVP mode and want to move quickly.
* Stack is FastAPI and Supabase, but the main concern right now is data shape and product behavior, not infra.

You want:

* A simple way to ingest and inspect portal data.
* A single user facing view of listings that does not expose source complexity.
* Room to evolve into a more robust canonical schema later, without rewriting everything.

---

## Problem

The current idea of storing everything in a single big JSON has these issues:

1. **No clear internal model of a listing**

   * Different sources use different keys for the same concept.
   * Any code that consumes listings has to know source specific details.

2. **Hard to debug portal specific issues**

   * When one portal changes its markup, it is hard to see only that portal's impact.
   * It is not easy to compare scrapes over time per source.

3. **Too early to lock into a heavy canonical schema**

   * You do not yet know which attributes matter most to users and to your LLM layer.
   * Over designing the schema now would slow down experiments.

You need something that is:

* Simple enough to ship quickly.
* Structured enough that you can grow into a canonical model later.
* Friendly for debugging and experimentation.

---

## Decision

For the MVP, use:

* **Two separate raw tables**, one per portal, that store the scraped payload as is.
* **Two internal debug views**, one per portal, for you to inspect raw data.
* **One unified listing shape for the product UI**, created by small mapping functions from each raw table.

You will not introduce a full canonical listings table yet. That comes later.

---

## Short term approach (MVP)

### Data storage

* Maintain one raw table per portal.
* Each row represents a listing from that portal at a given scrape time.
* Store:

  * A portal specific listing identifier.
  * The original source URL.
  * A timestamp for when it was scraped.
  * The full raw payload as JSON.

The goal here is to preserve everything the scraper found, with minimal interpretation.

### Internal views

* Provide one internal view per portal that shows recent rows from that portal's raw table.
* Use these views for:

  * Checking scraper quality.
  * Identifying weird or broken fields.
  * Comparing how different portals represent similar properties.

These views are for you, not for end users.

### Unified listing model for the product

* Define a simple internal model for a listing card that the UI can rely on, for example including:

  * A global id such as `site_name:site_listing_id`.
  * The source name (MagicBricks, SquareYards).
  * A title to display.
  * A human readable location label.
  * Human readable BHK, price, and area labels.
  * The original source URL.

* Implement a small adapter per portal that:

  * Reads one raw row.
  * Picks out the fields needed for the listing card.
  * Fills in this unified shape as best as possible, even if some values are approximate.

* The user facing API and UI:

  * Ask for a list of listing cards.
  * Receive a single list that merges listings from all portals.
  * Do not need to care about the underlying per portal schemas.

At this stage, the focus is on alignment of keys and labels, not precise numeric parsing or data validation.

---

## Long term approach

Once you have real user feedback and a better sense of what matters, evolve the design in stages.

### 1. Introduce a canonical listings table

* Define one canonical table or collection for listings across all sources.
* Keep a stable set of fields for:

  * Location.
  * Property characteristics (type, BHK, bathrooms, areas).
  * Pricing.
  * Metadata (title, description, posting time).
* Store the canonical representation as JSON, plus a few key fields as structured columns for querying.
* Reference back to the raw portal rows so you never lose the original data.

### 2. Build a transformation step from raw tables to canonical

* Run a periodic or incremental process that:

  * Reads raw rows from each portal table.
  * Applies mapping and cleaning logic.
  * Produces canonical listings and updates the canonical table.

* Use this step to:

  * Normalize field names.
  * Apply basic parsing of BHK, area, and price.
  * Start handling duplicates across portals.

### 3. Switch user facing queries to canonical listings

* Once canonical data is stable enough:

  * Have the main listing API read from the canonical table instead of from raw tables.
  * Keep the listing card mapping functions, but now they operate on a clean, uniform model.

* Raw tables remain as:

  * The ground truth of what was scraped.
  * A fallback if the transformation logic needs to be changed and re run.

### 4. Add richer semantics when needed

In later iterations you can:

* Add confidence and validation information for each field.
* Store multiple signals per field (title, description, structured field value) and derive a best guess.
* Introduce anomaly flags for suspicious prices or sizes.
* Use this extra information in:

  * Ranking and filtering.
  * LLM prompts.
  * Quality dashboards.

---

## Trade offs

**Benefits**

* Fast to implement with low risk.
* Each portal is clearly isolated on the ingestion side, which simplifies debugging.
* The product UI gets a consistent listing card from day one.
* You preserve raw data in a form that is easy to reprocess later into a better schema.

**Costs**

* Some duplication in the per portal adapter functions.
* No single canonical view of a property in the first version.
* Limited ability to run complex numeric queries until the canonical layer is added.

---

## Why this is acceptable for now

* The immediate goal is to validate the product idea and interaction model, not to perfect the data model.
* The two table raw approach lets you:

  * Move fast with scraping and UI experiments.
  * Expose a single unified experience to users.
  * Keep your options open for a more robust canonical design without throwing away work.

This decision can be revisited when you are ready to design the canonical listings schema and the transformation pipeline from raw portal data into that schema.
