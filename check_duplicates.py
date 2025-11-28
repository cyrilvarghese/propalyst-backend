"""
Check for Duplicate Messages

Analyzes messages in whatsapp_raw_messages and shows duplicate pairs
based on message_text hash (text only).

Run with: python check_duplicates.py
"""

import hashlib
from collections import defaultdict
from services.supabase_service import SupabaseService


def calculate_text_hash(message_text: str) -> str:
    """Calculate MD5 hash of message text only"""
    return hashlib.md5(message_text.encode('utf-8')).hexdigest()


def main():
    print("="*80)
    print("Duplicate Message Checker")
    print("="*80)

    # Get Supabase client
    client = SupabaseService._get_client()
    print("✓ Connected to Supabase\n")

    # Read all messages (fetch in batches to avoid default 1000 limit)
    print("Reading all messages from whatsapp_raw_messages...")
    all_messages = []
    batch_size = 1000
    offset = 0

    while True:
        response = client.table("whatsapp_raw_messages")\
            .select("id, message_text, sender_name, message_date, created_at")\
            .range(offset, offset + batch_size - 1)\
            .execute()

        batch = response.data or []
        if not batch:
            break

        all_messages.extend(batch)
        offset += batch_size
        print(f"  Fetched {len(all_messages)} messages so far...")

        if len(batch) < batch_size:
            break  # Last batch

    print(f"✓ Found {len(all_messages)} total messages\n")

    if len(all_messages) == 0:
        print("No messages found")
        return

    # Group by text hash
    print("Grouping by message text hash...")
    hash_groups = defaultdict(list)

    for msg in all_messages:
        message_text = msg.get('message_text', '')
        text_hash = calculate_text_hash(message_text)

        hash_groups[text_hash].append(msg)

    # Find duplicate groups
    duplicate_groups = {h: msgs for h, msgs in hash_groups.items() if len(msgs) > 1}

    print(f"✓ Found {len(duplicate_groups)} groups with duplicates\n")

    if len(duplicate_groups) == 0:
        print("✅ No duplicates found!")
        return

    # Show first 5 duplicate groups
    print("="*80)
    print(f"Showing First 5 Duplicate Groups (out of {len(duplicate_groups)} total)")
    print("="*80)

    for idx, (hash_val, messages) in enumerate(list(duplicate_groups.items())[:5], 1):
        print(f"\n{'='*80}")
        print(f"DUPLICATE GROUP #{idx} (Hash: {hash_val[:16]}...)")
        print(f"{'='*80}")
        print(f"Found {len(messages)} messages with identical text:\n")

        for msg_idx, msg in enumerate(messages, 1):
            print(f"  Message {msg_idx}/{len(messages)}:")
            print(f"    ID:          {msg.get('id')}")
            print(f"    Sender:      {msg.get('sender_name')}")
            print(f"    Date:        {msg.get('message_date')}")
            print(f"    Created At:  {msg.get('created_at')}")
            print(f"    Text Preview: {msg.get('message_text', '')[:150]}...")
            print()

        # Show if texts are truly identical
        texts = [msg.get('message_text', '') for msg in messages]
        if len(set(texts)) == 1:
            print(f"  ✓ Confirmed: All {len(messages)} messages have IDENTICAL text")
        else:
            print(f"  ⚠️  Warning: Messages have DIFFERENT text (hash collision?)")

        print(f"\n  Full text of first message:")
        print(f"  {'-'*76}")
        print(f"  {messages[0].get('message_text', '')[:500]}")
        print(f"  {'-'*76}")

    # Summary
    print(f"\n{'='*80}")
    print("Summary")
    print("="*80)
    print(f"Total messages:        {len(all_messages)}")
    print(f"Unique messages:       {len(hash_groups)}")
    print(f"Duplicate groups:      {len(duplicate_groups)}")

    # Count total duplicates to delete
    total_duplicates = sum(len(msgs) - 1 for msgs in duplicate_groups.values())
    print(f"Duplicates to delete:  {total_duplicates}")
    print(f"Messages after cleanup: {len(all_messages) - total_duplicates}")
    print("="*80)

    print("\nTo see all duplicate groups, check the database or modify this script.")


if __name__ == "__main__":
    main()
