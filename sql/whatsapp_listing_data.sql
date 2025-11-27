-- WhatsApp Listing Data Table
-- Stores ALL classified messages to prevent duplicate LLM calls
-- - Supply/Demand messages: Full extracted data
-- - Greeting/Garbage/Generic: Minimal data (just classification)
-- Source: public.crea_wapp table (read-only reference)

create table public.whatsapp_listing_data (
  id uuid primary key default gen_random_uuid(),

  -- reference to the original raw message
  source_message_id uuid not null
    references public.crea_wapp(id) on delete cascade
    unique,

  -- copied metadata from source row (message_date, company_name)
  -- agent info extracted by LLM (can be null if not in message)
  message_date timestamptz,
  agent_contact text null,
  agent_name text null,
  company_name text null,

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

-- Constraint to enforce valid message types (all types stored for tracking)
-- Supply/demand have full data, greeting/garbage/generic have minimal data
alter table public.whatsapp_listing_data
add constraint whatsapp_listing_message_type_chk
check (
  message_type in (
    'greeting', 'garbage', 'generic_info',
    'supply_sale', 'supply_rent',
    'demand_buy', 'demand_rent'
  )
);

-- Indexes for performance
create index if not exists idx_whatsapp_listing_source_message_id on public.whatsapp_listing_data(source_message_id);
create index if not exists idx_whatsapp_listing_message_date on public.whatsapp_listing_data(message_date);
create index if not exists idx_whatsapp_listing_agent_contact on public.whatsapp_listing_data(agent_contact);
create index if not exists idx_whatsapp_listing_message_type on public.whatsapp_listing_data(message_type);
create index if not exists idx_whatsapp_listing_property_type on public.whatsapp_listing_data(property_type);
create index if not exists idx_whatsapp_listing_location on public.whatsapp_listing_data(location);
create index if not exists idx_whatsapp_listing_special_features on public.whatsapp_listing_data using gin(special_features);

-- Comments for documentation
comment on table public.whatsapp_listing_data is 'Structured WhatsApp listing data extracted from raw messages using LLM';
comment on column public.whatsapp_listing_data.source_message_id is 'Reference to original message in crea_wapp table (unique)';
comment on column public.whatsapp_listing_data.message_type is 'Classification: supply_sale, supply_rent, demand_buy, demand_rent, greeting, garbage, generic_info. Only supply/demand have full data extracted.';
comment on column public.whatsapp_listing_data.property_type is 'Normalized property category: apartment, villa, plot, etc.';
comment on column public.whatsapp_listing_data.area_sqft is 'Property area in square feet';
comment on column public.whatsapp_listing_data.price is 'Numeric price in rupees (sale=total, rent=monthly)';
comment on column public.whatsapp_listing_data.furnishing_status is 'unfurnished, semi_furnished, fully_furnished, bare_shell, warm_shell';
comment on column public.whatsapp_listing_data.facing_direction is 'Normalized direction: north, south, east, west, or special facing like lake_facing';
comment on column public.whatsapp_listing_data.special_features is 'Array of feature tags like corner_plot, gated_community, ready_to_move';
comment on column public.whatsapp_listing_data.llm_json is 'Full LLM response JSON for debugging/reference';

-- Helpful view: Only relevant listings (supply/demand) with full data
create or replace view public.whatsapp_listings_relevant as
select *
from public.whatsapp_listing_data
where message_type in ('supply_sale', 'supply_rent', 'demand_buy', 'demand_rent')
order by message_date desc;

comment on view public.whatsapp_listings_relevant is 'View containing only supply/demand listings with full extracted data (excludes greeting/garbage/generic_info)';
