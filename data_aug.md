Here is the **full and final spec**, combining everything into a single clean document you can hand directly to your developer.

It contains:

* What needs to be built
* The new table schema
* The LLM extraction spec
* Each field’s meaning
* The processing workflow
* Exactly how to run backfill and incremental updates

No changes are made to the original `crea_wapp` table.

---

# **SPEC: WhatsApp Listing Data Extraction Pipeline (v1)**

## **0. Goal**

Build a pipeline that:

1. Reads each raw WhatsApp message from the existing `public.crea_wapp` table
2. Sends the `raw_message` text to an LLM
3. Receives a structured JSON response
4. Inserts a normalized row into a **new** table `public.whatsapp_listing_data`

This creates a clean, queryable dataset separate from the raw table.

**Important:**

* `crea_wapp` stays **unchanged** (read only).
* All new writes go to the new table.
* Each message is processed once using `source_message_id` as the unique reference.

---

# **1. New Table: `public.whatsapp_listing_data`**

Create this table:

```sql
create table public.whatsapp_listing_data (
  id uuid primary key default gen_random_uuid(),

  -- reference to the original raw message
  source_message_id uuid not null
    references public.crea_wapp(id) on delete cascade
    unique,

  -- copied metadata from source row
  message_date timestamptz,
  agent_contact text not null,
  agent_name text,
  company_name text,

  -- original raw message text
  raw_message text not null,

  -- LLM classification
  message_type text not null,

  -- extracted structured fields
  property_type text null,
  area_sqft numeric null,

  price numeric null,
  price_text text null,

  location text null,
  project_name text null,

  furnishing_status text null,
  parking_count integer null,
  parking_text text null,

  facing_direction text null,
  special_features text[] null,

  -- full JSON returned from the LLM
  llm_json jsonb null,

  created_at timestamptz not null default now()
);
```

Optional constraint to keep classification clean:

```sql
alter table public.whatsapp_listing_data
add constraint whatsapp_listing_message_type_chk
check (
  message_type in (
    'greeting', 'garbage', 'generic_info',
    'supply_sale', 'supply_rent',
    'demand_buy', 'demand_rent'
  )
);
```

---

# **2. LLM Extraction Contract**

The backend must send **one raw message** to the LLM and expect a JSON response with specific fields.

## **2.1 LLM Input**

For each unprocessed row from `crea_wapp`, pass:

```json
{
  "raw_message": "<full WhatsApp message text>"
}
```

No other fields are required, but you can include them for context if needed.

---

# **2.2 Expected LLM Output JSON**

The LLM must return exactly this structure:

```json
{
  "message_type": "...",

  "property_type": "...",
  "area_sqft": null,

  "price": null,
  "price_text": null,

  "location": null,
  "project_name": null,

  "furnishing_status": null,
  "parking_count": null,
  "parking_text": null,

  "facing_direction": null,
  "special_features": [],

  "llm_notes": null
}
```

---

# **2.3 Field Definitions (For Prompt Construction)**

Use the below definitions inside the LLM system prompt.

### **message_type**

High level classification of the message.
Allowed values:

* `greeting`
* `garbage`
* `generic_info`
* `supply_sale`
* `supply_rent`
* `demand_buy`
* `demand_rent`

Exactly one must be chosen.

---

### **property_type**

Normalized property category.

Allowed values:

* `apartment`
* `villa`
* `independent_house`
* `plot`
* `land`
* `office`
* `retail`
* `warehouse`
* `industrial`
* `other`
* `null`

---

### **area_sqft**

A number (main area in square feet), or null.

Extract from patterns like:

* `"2500 sft"`, `"1650 sqft"`, `"2400-2600 sq ft"`

Pick a single representative value.

---

### **price**

Numeric price in rupees, or null.

Conversions:

* 2.4 Cr → 24000000
* 75L → 7500000
* 80k → 80000
* 1.8L → 180000

Sale = total value
Rent = monthly rent

---

### **price_text**

Human readable phrase, like:

* `"2.3 Cr slightly negotiable"`
* `"Rent 80k"`
* `"Price on request"`

---

### **location**

Main locality or micro market:

* `"Whitefield"`
* `"Indiranagar"`
* `"HSR Layout"`
* `"Near Manyata Tech Park"`

---

### **project_name**

Name of building or project if mentioned:

* `"Sobha Lake Terrace"`
* `"Prestige Shantiniketan"`

---

### **furnishing_status**

One of:

* `unfurnished`
* `semi_furnished`
* `fully_furnished`
* `bare_shell`
* `warm_shell`
* `unknown`
* `null`

---

### **parking_count**

Integer number of car parks if explicitly stated.

### **parking_text**

Raw text describing parking.

---

### **facing_direction**

Normalized direction:

* `north`, `south`, `east`, `west`
* `north_east`, `north_west`, `south_east`, `south_west`
* `road_facing`, `park_facing`, `lake_facing`
* `unknown`
* `null`

---

### **special_features**

List of feature tags.

Examples:

* `"corner_plot"`
* `"lake_view"`
* `"gated_community"`
* `"ready_to_move"`
* `"duplex"`

Array can be empty (`[]`).

---

### **llm_notes**

Free text notes from LLM, or null.
This is stored inside `llm_json` only.

---

# **3. Processing Workflow**

Your dev must build the following workflow.

## **3.1 Step 1: Read unprocessed messages**

Query:

```sql
select
  w.id,
  w.message_date,
  w.agent_contact,
  w.agent_name,
  w.company_name,
  w.raw_message
from public.crea_wapp w
left join public.whatsapp_listing_data d
  on d.source_message_id = w.id
where d.source_message_id is null;
```

This returns only raw messages that do **not** yet exist in `whatsapp_listing_data`.

---

## **3.2 Step 2: Send raw message to LLM**

For each row returned by Step 1:

* Call LLM with the prompt and input
* Parse the returned JSON
* Validate required fields (`message_type`, `special_features`)

---

## **3.3 Step 3: Insert new row**

Insert into the new table:

```sql
insert into public.whatsapp_listing_data (
  source_message_id,
  message_date,
  agent_contact,
  agent_name,
  company_name,
  raw_message,
  message_type,
  property_type,
  area_sqft,
  price,
  price_text,
  location,
  project_name,
  furnishing_status,
  parking_count,
  parking_text,
  facing_direction,
  special_features,
  llm_json
)
values (
  $id,
  $message_date,
  $agent_contact,
  $agent_name,
  $company_name,
  $raw_message,
  $message_type,
  $property_type,
  $area_sqft,
  $price,
  $price_text,
  $location,
  $project_name,
  $furnishing_status,
  $parking_count,
  $parking_text,
  $facing_direction,
  $special_features::text[],
  $llm_json::jsonb
);
```

`source_message_id` is unique so the message is never processed twice.

---

# **4. Incremental Processing**

Schedule a worker or cron job to:

1. Run the same "unprocessed rows" query
2. Process any new rows with LLM
3. Insert into `whatsapp_listing_data`

This keeps everything in sync automatically as new messages arrive.

---

# **5. Summary (1 page version for dev)**

* Do **not modify** `crea_wapp`.
* Create `whatsapp_listing_data` as defined.
* For each `crea_wapp` row not already in the new table:

  1. Read metadata + raw_message
  2. Send `raw_message` to LLM
  3. Receive structured JSON
  4. Insert a row into `whatsapp_listing_data`

This is the complete and final spec.
