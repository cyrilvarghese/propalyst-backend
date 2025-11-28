"""
Migration Script: Recalculate Message Hashes

Changes hash calculation from (date + sender + text) to (text only)
This allows better deduplication - same message from different senders = duplicate

Run with: python migrate_hash.py
"""

import asyncio
import hashlib
from services.supabase_service import SupabaseService


def calculate_new_hash(message_text: str) -> str:
    """Calculate MD5 hash of message text only"""
    return hashlib.md5(message_text.encode('utf-8')).hexdigest()


async def main():
    print("="*60)
    print("Migration: Recalculate Message Hashes")
    print("="*60)

    # Get Supabase client
    client = SupabaseService._get_client()
    print("✓ Connected to Supabase")

    # Read all messages (include created_at for duplicate resolution)
    # Fetch in batches to avoid Supabase default 1000 row limit
    print("\nStep 1: Reading all messages from whatsapp_raw_messages...")
    all_messages = []
    batch_size = 1000
    offset = 0

    while True:
        response = client.table("whatsapp_raw_messages")\
            .select("id, message_text, message_hash, created_at")\
            .range(offset, offset + batch_size - 1)\
            .execute()

        batch = response.data or []
        if not batch:
            break

        all_messages.extend(batch)
        offset += batch_size
        print(f"  Fetched {len(all_messages)} messages...")

        if len(batch) < batch_size:
            break  # Last batch

    print(f"✓ Found {len(all_messages)} total messages")

    if len(all_messages) == 0:
        print("✓ No messages to migrate")
        return

    # Group messages by new hash to detect duplicates
    print("\nStep 2: Grouping messages by new hash (text only)...")
    from collections import defaultdict
    hash_groups = defaultdict(list)

    for msg in all_messages:
        message_text = msg.get('message_text', '')
        new_hash = calculate_new_hash(message_text)

        hash_groups[new_hash].append({
            'id': msg['id'],
            'old_hash': msg.get('message_hash'),
            'new_hash': new_hash,
            'created_at': msg.get('created_at'),
            'text_preview': message_text[:100]
        })

    # Find duplicates
    duplicates_to_delete = []
    messages_to_update = []

    for new_hash, messages in hash_groups.items():
        if len(messages) > 1:
            # Sort by created_at to keep latest (reverse order)
            messages.sort(key=lambda x: x['created_at'], reverse=True)

            # Keep first (latest), mark rest for deletion
            messages_to_update.append(messages[0])
            duplicates_to_delete.extend(messages[1:])

            print(f"  Found {len(messages)} duplicates with hash {new_hash[:8]}... - keeping latest")
        else:
            # Single message, just update hash
            messages_to_update.append(messages[0])

    print(f"\n✓ Analysis complete:")
    print(f"  Total messages:      {len(all_messages)}")
    print(f"  Unique messages:     {len(messages_to_update)}")
    print(f"  Duplicates to delete: {len(duplicates_to_delete)}")

    # Delete duplicates first
    if len(duplicates_to_delete) > 0:
        print(f"\nStep 3: Deleting {len(duplicates_to_delete)} duplicate messages...")
        delete_count = 0

        for dup in duplicates_to_delete:
            try:
                client.table("whatsapp_raw_messages")\
                    .delete()\
                    .eq('id', dup['id'])\
                    .execute()

                delete_count += 1

                if delete_count % 50 == 0:
                    print(f"  Deleted: {delete_count}/{len(duplicates_to_delete)}...")

            except Exception as e:
                print(f"  ❌ Error deleting message {dup['id']}: {e}")

        print(f"✓ Deleted {delete_count} duplicate messages")

    # Update hashes for kept messages
    print(f"\nStep 4: Updating hashes for {len(messages_to_update)} messages...")
    success_count = 0
    error_count = 0

    for idx, msg in enumerate(messages_to_update, 1):
        try:
            client.table("whatsapp_raw_messages")\
                .update({'message_hash': msg['new_hash']})\
                .eq('id', msg['id'])\
                .execute()

            success_count += 1

            # Print progress every 100 messages
            if idx % 100 == 0:
                print(f"  Progress: {idx}/{len(messages_to_update)} updated...")

        except Exception as e:
            error_count += 1
            print(f"  ❌ Error updating message {msg['id']}: {e}")

    # Summary
    print("\n" + "="*60)
    print("Migration Complete!")
    print("="*60)
    print(f"Original messages:   {len(all_messages)}")
    print(f"Duplicates deleted:  {len(duplicates_to_delete)}")
    print(f"Unique messages:     {len(messages_to_update)}")
    print(f"Hashes updated:      {success_count}")
    print(f"Errors:              {error_count}")
    print("="*60)

    if error_count > 0:
        print(f"\n⚠️  Warning: {error_count} messages failed to update")
    else:
        print("\n✅ All hashes successfully recalculated!")
        print(f"✅ Removed {len(duplicates_to_delete)} duplicate messages")

    print("\nNext steps:")
    print("1. Verify hash changes in database")
    print("2. Check /api/whatsapp-raw/raw-stats to see new counts")
    print("3. Future uploads will use new hash calculation (text only)")


if __name__ == "__main__":
    asyncio.run(main())
