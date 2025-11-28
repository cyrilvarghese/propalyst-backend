-- Migration: Remove source_message_id column from whatsapp_listing_data
-- Date: 2025-11-27
-- Reason: No longer using crea_wapp table as source, uploading files directly

-- Step 1: Drop the index
DROP INDEX IF EXISTS idx_whatsapp_listing_source_message_id;

-- Step 2: Drop the unique constraint (if it exists separately)
-- Note: It's part of the column definition, so it will be removed with the column

-- Step 3: Drop the column (this also removes the foreign key constraint)
ALTER TABLE public.whatsapp_listing_data
DROP COLUMN IF EXISTS source_message_id;

-- Step 4: Update table comment
COMMENT ON TABLE public.whatsapp_listing_data IS 'Structured WhatsApp listing data extracted from file uploads using LLM';

-- Verify the change
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'whatsapp_listing_data'
ORDER BY ordinal_position;
