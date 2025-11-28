-- Migration: Recalculate message_hash to use text only (instead of date+sender+text)
-- Handles duplicates by keeping the latest message

-- Step 1: Create a temp table with new hashes and duplicate resolution
CREATE TEMP TABLE temp_hash_updates AS
WITH new_hashes AS (
  SELECT
    id,
    message_text,
    message_hash as old_hash,
    MD5(message_text) as new_hash,
    created_at,
    ROW_NUMBER() OVER (
      PARTITION BY MD5(message_text)
      ORDER BY created_at DESC  -- Keep latest
    ) as row_num
  FROM whatsapp_raw_messages
)
SELECT
  id,
  old_hash,
  new_hash,
  row_num,
  (row_num = 1) as keep  -- True for messages to keep, False for duplicates
FROM new_hashes;

-- Step 2: Show what will be deleted
SELECT
  COUNT(*) as total_messages,
  SUM(CASE WHEN keep THEN 1 ELSE 0 END) as messages_to_keep,
  SUM(CASE WHEN NOT keep THEN 1 ELSE 0 END) as duplicates_to_delete
FROM temp_hash_updates;

-- Step 3: Delete duplicate messages (keep latest only)
DELETE FROM whatsapp_raw_messages
WHERE id IN (
  SELECT id FROM temp_hash_updates WHERE keep = false
);

-- Step 4: Drop the UNIQUE constraint temporarily
ALTER TABLE whatsapp_raw_messages
DROP CONSTRAINT IF EXISTS whatsapp_raw_messages_message_hash_key;

-- Step 5: Update hashes for kept messages
UPDATE whatsapp_raw_messages wrm
SET message_hash = thu.new_hash
FROM temp_hash_updates thu
WHERE wrm.id = thu.id
  AND thu.keep = true;

-- Step 6: Re-add the UNIQUE constraint
ALTER TABLE whatsapp_raw_messages
ADD CONSTRAINT whatsapp_raw_messages_message_hash_key UNIQUE (message_hash);

-- Step 7: Verify results
SELECT
  COUNT(*) as total_messages,
  COUNT(DISTINCT message_hash) as unique_hashes
FROM whatsapp_raw_messages;

-- Cleanup
DROP TABLE temp_hash_updates;

-- Done!
SELECT 'Migration complete! Hash recalculated to use message_text only.' as status;
