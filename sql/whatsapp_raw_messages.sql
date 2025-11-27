-- Table for storing raw parsed WhatsApp messages
-- This table stores individual messages parsed from WhatsApp chat export files

create table if not exists public.whatsapp_raw_messages (
  -- Primary key
  id uuid primary key default gen_random_uuid(),

  -- Parsed message fields
  message_date timestamptz not null,
  sender_name text not null,
  message_text text not null,

  -- Message type flags
  is_deleted boolean default false,
  is_media boolean default false,

  -- Source tracking (optional, for debugging)
  source_file text,
  line_number integer,

  -- Metadata
  created_at timestamptz not null default now()
);

-- Indexes for efficient querying
create index if not exists idx_whatsapp_raw_message_date
  on public.whatsapp_raw_messages(message_date desc);

create index if not exists idx_whatsapp_raw_sender_name
  on public.whatsapp_raw_messages(sender_name);

create index if not exists idx_whatsapp_raw_source_file
  on public.whatsapp_raw_messages(source_file);

create index if not exists idx_whatsapp_raw_created_at
  on public.whatsapp_raw_messages(created_at desc);

-- Comment on table
comment on table public.whatsapp_raw_messages is
  'Raw parsed WhatsApp messages from chat export files. Each row represents a single message extracted from the export.';

-- Comments on columns
comment on column public.whatsapp_raw_messages.message_date is
  'Timestamp from the WhatsApp export (when the message was sent)';
comment on column public.whatsapp_raw_messages.sender_name is
  'Name or phone number of the message sender as it appears in the export';
comment on column public.whatsapp_raw_messages.message_text is
  'Full message body, may include multiple lines';
comment on column public.whatsapp_raw_messages.is_deleted is
  'True if the message was deleted (contains "This message was deleted")';
comment on column public.whatsapp_raw_messages.is_media is
  'True if the message is media (contains "image omitted", "video omitted", etc.)';
comment on column public.whatsapp_raw_messages.source_file is
  'Optional: name of the source file this message was parsed from';
comment on column public.whatsapp_raw_messages.line_number is
  'Optional: line number in the source file where this message started';
