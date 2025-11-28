-- WhatsApp Raw Messages Table
-- Stores ALL parsed messages from WhatsApp exports (after regex split, before LLM processing)
-- This is Stage 1: Raw data storage with deduplication

DROP TABLE IF EXISTS public.whatsapp_raw_messages CASCADE;

CREATE TABLE public.whatsapp_raw_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Deduplication: Hash of message content
  message_hash text NOT NULL UNIQUE,

  -- Parsed message fields (from regex)
  message_date timestamptz NOT NULL,
  sender_name text NOT NULL,
  message_text text NOT NULL,

  -- Message type flags (detected by regex)
  is_deleted boolean DEFAULT false,
  is_media boolean DEFAULT false,

  -- Source tracking
  source_file text,
  line_number integer,

  -- Processing status
  processed boolean DEFAULT false,  -- True if sent to LLM and extracted
  processed_at timestamptz NULL,     -- When it was processed

  -- Metadata
  created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_whatsapp_raw_message_hash ON public.whatsapp_raw_messages(message_hash);
CREATE INDEX IF NOT EXISTS idx_whatsapp_raw_message_date ON public.whatsapp_raw_messages(message_date DESC);
CREATE INDEX IF NOT EXISTS idx_whatsapp_raw_sender_name ON public.whatsapp_raw_messages(sender_name);
CREATE INDEX IF NOT EXISTS idx_whatsapp_raw_source_file ON public.whatsapp_raw_messages(source_file);
CREATE INDEX IF NOT EXISTS idx_whatsapp_raw_processed ON public.whatsapp_raw_messages(processed) WHERE processed = false;

-- Comments
COMMENT ON TABLE public.whatsapp_raw_messages IS 'Raw parsed WhatsApp messages (Stage 1). Stores all messages after regex parsing, before LLM processing.';
COMMENT ON COLUMN public.whatsapp_raw_messages.message_hash IS 'MD5 hash of message_text + sender_name + message_date for deduplication';
COMMENT ON COLUMN public.whatsapp_raw_messages.processed IS 'True if message has been sent to LLM and extracted to whatsapp_listing_data';
COMMENT ON COLUMN public.whatsapp_raw_messages.message_text IS 'Full message body from WhatsApp export (may contain multiple lines)';

-- View: Unprocessed messages (ready for LLM)
CREATE OR REPLACE VIEW public.whatsapp_raw_messages_unprocessed AS
SELECT *
FROM public.whatsapp_raw_messages
WHERE processed = false
  AND is_deleted = false
  AND is_media = false
ORDER BY message_date ASC;

COMMENT ON VIEW public.whatsapp_raw_messages_unprocessed IS 'Unprocessed raw messages ready for LLM extraction (excludes deleted/media)';
