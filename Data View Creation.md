Here is a clean spec you can paste into a doc / Notion for your dev.

---

# 0\. Goal

Build an **Agent Profiling pipeline** that:

* Uses WhatsApp group messages stored in `crea_wapp`  
    
* Identifies **top active agents** in the last 3 months  
    
* For each top agent:  
    
  * Collects a small sample of recent raw messages  
      
  * Sends them to an LLM to infer a **clean, standardized profile**  
      
  * Stores one **normalized profile row per agent** with:  
      
    * Numeric filters: price bands, BHK range, supply vs demand counts  
    * Non numeric info: primary locations, property types, summary


* Can be rerun periodically so profiles stay in sync with new data

The LLM is responsible for interpreting messy text. Numeric aggregations use the standardized values returned by the LLM.

---

# 1\. High level steps

1. **Raw data storage** WhatsApp messages live in `public.crea_wapp`.  
     
2. **Top agent selection (3 month window)** Use a view to find agents with enough activity in the last 3 months.  
     
3. **Recent messages per top agent** View that picks up to 20 most recent messages per top agent.  
     
4. **Grouped per agent view (Step 2.4)** View that returns one row per agent with an array of recent messages. This is the **only SQL input** to the LLM layer.  
     
5. **LLM per agent** Backend reads the grouped view, builds payload per agent, calls LLM, gets clean normalized data back.  
     
6. **Agent profiles table** Store one row per agent with:  
     
   * Numeric bands and counts (sale and rent bands, BHK range, supply vs demand counts)  
   * Locations and property types  
   * Human summary  
   * Full LLM JSON

   

7. **Refresh strategy** Run the pipeline periodically (for example daily). Each run overwrites the agent profile with a fresh LLM result based on the last 3 months of messages.

---

# 2\. Data model and SQL views

## 2.1 Raw messages table (existing)

create table public.crea\_wapp (

  id uuid not null default gen\_random\_uuid (),

  created\_at timestamptz not null default now(),

  message\_date timestamptz null,

  agent\_name text not null,

  agent\_contact text null,

  company\_name text null,

  listing\_type text null,       \-- 'sale' or 'rent' (what kind of listing)

  transaction\_type text null,   \-- 'sell' or 'rent' (client intent, if used)

  property\_type text null,

  configuration text null,

  size\_sqft numeric null,

  price numeric null,

  price\_text text null,

  location text null,

  project\_name text null,

  facing text null,

  floor text null,

  furnishing text null,

  parking integer null,

  status text null,

  amenities text null,

  raw\_message text not null,

  constraint real\_estate\_listings\_pkey primary key (id)

);

All LLM interpretation is based on `raw_message` and the agent identity fields.

---

## 2.2 Top agents in last 3 months

Criteria:

* `message_date` in last 3 months  
* More than 20 posts  
* Has a non null `agent_contact`

create or replace view public.crea\_top\_agents\_3m as

select

  agent\_contact,

  agent\_name,

  company\_name,

  count(\*)          as total\_posts,

  max(message\_date) as last\_seen

from public.crea\_wapp

where message\_date \>= now() \- interval '3 months'

  and agent\_contact is not null

group by

  agent\_contact,

  agent\_name,

  company\_name

having

  count(\*) \> 20

  and max(message\_date) \>= now() \- interval '3 months';

Result: one row per top agent.

---

## 2.3 Recent messages per top agent

Pick up to 20 most recent messages for each top agent within last 3 months.

create or replace view public.crea\_top\_agents\_3m\_msgs as

with ranked\_messages as (

  select

    w.id,

    w.message\_date,

    w.agent\_contact,

    w.agent\_name,

    w.company\_name,

    w.raw\_message,

    row\_number() over (

      partition by w.agent\_contact

      order by w.message\_date desc

    ) as rn

  from public.crea\_wapp w

  join public.crea\_top\_agents\_3m ta

    on w.agent\_contact \= ta.agent\_contact

   and w.message\_date \>= now() \- interval '3 months'

)

select

  id,

  agent\_contact,

  agent\_name,

  company\_name,

  message\_date,

  raw\_message,

  rn

from ranked\_messages

where rn \<= 20;

Result: one row per message, max 20 rows per agent.

---

## 2.4 Grouped per agent view – input to LLM

This is the key view the backend uses to call the LLM.

create or replace view public.crea\_top\_agents\_3m\_msgs\_grouped as

select

  m.agent\_contact,

  min(m.agent\_name)   as agent\_name,

  min(m.company\_name) as company\_name,

  ta.total\_posts,

  ta.last\_seen,

  json\_agg(

    json\_build\_object(

      'message\_date', m.message\_date,

      'raw\_message',  m.raw\_message

    )

    order by m.message\_date desc

  ) as messages

from public.crea\_top\_agents\_3m\_msgs m

join public.crea\_top\_agents\_3m ta

  on m.agent\_contact \= ta.agent\_contact

group by

  m.agent\_contact,

  ta.total\_posts,

  ta.last\_seen;

Each row:

{

  "agent\_contact": "+91...",

  "agent\_name": "Some Agent",

  "company\_name": "Some Realty",

  "total\_posts": 47,

  "last\_seen": "2025-11-20T10:10:00Z",

  "messages": \[

    { "message\_date": "...", "raw\_message": "..." },

    ...

  \]

}

---

# 3\. Agent profile storage

We store one clean profile row per agent, derived from the LLM output.

create table if not exists public.agent\_profiles\_clean (

  agent\_contact text primary key,

  agent\_name text,

  company\_name text,

  \-- numeric bands inferred by LLM for this agent

  sale\_price\_min numeric null,    \-- rupees

  sale\_price\_max numeric null,    \-- rupees

  rent\_price\_min numeric null,    \-- rupees per month

  rent\_price\_max numeric null,    \-- rupees per month

  bhk\_min integer null,

  bhk\_max integer null,

  \-- supply vs demand orientation across sampled messages

  supply\_sale\_count integer not null default 0,   \-- supply sale

  supply\_rent\_count integer not null default 0,   \-- supply rent

  demand\_buy\_count integer not null default 0,    \-- demand buy

  demand\_rent\_count integer not null default 0,   \-- demand rent

  \-- non numeric profile features

  primary\_locations text\[\] null,        \-- list of main areas

  primary\_property\_types text\[\] null,   \-- standard labels

  \-- full LLM response and summary

  profile\_json jsonb not null,

  summary\_text text not null,

  \-- meta

  total\_posts integer not null,

  lookback\_months integer not null default 3,

  messages\_sampled integer not null default 20,

  generated\_at timestamptz not null default now()

);

---

# 4\. LLM contract

## 4.1 LLM input per agent

From `crea_top_agents_3m_msgs_grouped` row, backend builds:

{

  "agent\_contact": "+91XXXXXXX",

  "agent\_name": "Some Agent",

  "company\_name": "Some Realty",

  "total\_posts\_last\_3\_months": 47,

  "sample\_messages": \[

    "raw message text 1...",

    "raw message text 2...",

    "raw message text 3..."

  \]

}

Where `sample_messages` comes from `messages[*].raw_message`.

---

## 4.2 LLM output per agent

Ask the LLM to return exactly this JSON shape:

{

  "agent\_contact": "+91XXXXXXX",

  "primary\_locations": \["Whitefield", "Sarjapur Road"\],

  "primary\_property\_types": \["residential\_apartment", "residential\_villa"\],

  "sale\_price\_min": 20000000,

  "sale\_price\_max": 60000000,

  "rent\_price\_min": 60000,

  "rent\_price\_max": 180000,

  "bhk\_min": 2,

  "bhk\_max": 4,

  "supply\_sale\_count": 15,

  "supply\_rent\_count": 6,

  "demand\_buy\_count": 2,

  "demand\_rent\_count": 1,

  "summary\_text": "Focuses on mid to high ticket 2 to 4 BHK apartments and villas in Whitefield and Sarjapur Road, mostly handling sale inventory with some premium rentals."

}

### Prompt rules for the model (summary)

* Use `sample_messages` to infer this agent’s typical specialization.  
    
* `primary_property_types` must use a small fixed vocabulary like:  
    
  * `residential_apartment`, `residential_villa`, `plot_land`, `commercial_office`, `commercial_retail`, `industrial_warehouse`, `agri_land`


* `primary_locations` are 3 to 5 key areas or micro markets mentioned across messages.  
    
* Prices:  
    
  * Use rupee values only.  
  * Convert Cr, Lakh, and k to rupees.  
  * Ignore obviously junk prices like 50 rupees unless clearly a central signal.  
  * Ignore “Price on request” and similar.  
  * If no reliable sale prices, set `sale_price_min` and `sale_price_max` to null.  
  * If no reliable rent prices, set `rent_price_min` and `rent_price_max` to null.


* BHK:  
    
  * Infer from patterns like “2 BHK”, “3.5 BHK”, “4 bed”.  
  * Use `bhk_min` and `bhk_max` to cover the typical range in the sample.  
  * If no BHK info, set both to null.


* Supply vs demand:  
    
  * Supply listing:  
      
    * Offer inventory, phrases like “for sale”, “for rent”, “available”, “keys with me”, “inventory”.

    

  * Demand requirement:  
      
    * Phrases like “requirement”, “looking for”, “need a”, “client wants”, “seeking”.

    

  * Set `supply_sale_count`, `supply_rent_count`, `demand_buy_count`, `demand_rent_count` as counts of messages in each bucket across the sample.


* If unsure for any field, prefer `null` or 0 (for counts) rather than inventing.  
    
* Respond with JSON only, no extra text.

---

# 5\. Backend job flow

## 5.1 Fetch agents to profile

Query:

select

  agent\_contact,

  agent\_name,

  company\_name,

  total\_posts,

  last\_seen,

  messages

from public.crea\_top\_agents\_3m\_msgs\_grouped;

Backend iterates over rows.

Optionally, skip agents whose existing profile is very fresh, for example:

* If `agent_profiles_clean.generated_at > now() - interval '1 day'` then skip.

## 5.2 Build and send LLM payload

For each row:

* Extract `sample_messages` array from `messages[*].raw_message`.  
* Build input JSON according to section 4.1.  
* Call LLM with the fixed prompt.  
* Parse output JSON and validate keys.

## 5.3 Upsert into `agent_profiles_clean`

SQL upsert:

insert into public.agent\_profiles\_clean (

  agent\_contact,

  agent\_name,

  company\_name,

  sale\_price\_min,

  sale\_price\_max,

  rent\_price\_min,

  rent\_price\_max,

  bhk\_min,

  bhk\_max,

  supply\_sale\_count,

  supply\_rent\_count,

  demand\_buy\_count,

  demand\_rent\_count,

  primary\_locations,

  primary\_property\_types,

  profile\_json,

  summary\_text,

  total\_posts,

  lookback\_months,

  messages\_sampled

)

values (

  $agent\_contact,

  $agent\_name,

  $company\_name,

  $sale\_price\_min,

  $sale\_price\_max,

  $rent\_price\_min,

  $rent\_price\_max,

  $bhk\_min,

  $bhk\_max,

  $supply\_sale\_count,

  $supply\_rent\_count,

  $demand\_buy\_count,

  $demand\_rent\_count,

  $primary\_locations::text\[\],

  $primary\_property\_types::text\[\],

  $profile\_json::jsonb,

  $summary\_text,

  $total\_posts,   \-- from the view

  3,              \-- 3 month lookback

  $messages\_sampled

)

on conflict (agent\_contact) do update set

  agent\_name \= excluded.agent\_name,

  company\_name \= excluded.company\_name,

  sale\_price\_min \= excluded.sale\_price\_min,

  sale\_price\_max \= excluded.sale\_price\_max,

  rent\_price\_min \= excluded.rent\_price\_min,

  rent\_price\_max \= excluded.rent\_price\_max,

  bhk\_min \= excluded.bhk\_min,

  bhk\_max \= excluded.bhk\_max,

  supply\_sale\_count \= excluded.supply\_sale\_count,

  supply\_rent\_count \= excluded.supply\_rent\_count,

  demand\_buy\_count \= excluded.demand\_buy\_count,

  demand\_rent\_count \= excluded.demand\_rent\_count,

  primary\_locations \= excluded.primary\_locations,

  primary\_property\_types \= excluded.primary\_property\_types,

  profile\_json \= excluded.profile\_json,

  summary\_text \= excluded.summary\_text,

  total\_posts \= excluded.total\_posts,

  lookback\_months \= excluded.lookback\_months,

  messages\_sampled \= excluded.messages\_sampled,

  generated\_at \= now();

---

# 6\. Refresh and usage

* **Refresh cadence**  
    
  * Run this profiling job once a day or a few times a day.  
      
  * Each run:  
      
    * Uses the latest 3 month window and latest 20 messages per agent.  
    * Overwrites that agent’s row in `agent_profiles_clean`.


* **Usage in product**  
    
  * For lead routing:  
      
    * Filter agents on numeric fields like `sale_price_min`, `sale_price_max`, `bhk_min`, `bhk_max`.  
    * Filter on `primary_locations` and `primary_property_types`.  
    * Optionally rank by `supply_sale_count` vs `demand_buy_count` depending on lead type.

    

  * For internal UI:  
      
    * Show `summary_text`.  
    * Show `total_posts` and `last_seen` from `crea_top_agents_3m`.

This spec should be enough for a dev to wire the SQL, LLM calls, and upserts without needing more context.  
