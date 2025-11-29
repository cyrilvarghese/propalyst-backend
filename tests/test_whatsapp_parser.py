"""
Test suite for WhatsApp parser with multi-format support

Tests both iOS and Android WhatsApp export formats
"""

import pytest
from datetime import datetime
from services.whatsapp_parser_service import WhatsAppParserService, WhatsAppFormatType


class TestFormatDetection:
    """Tests for WhatsApp format auto-detection"""

    def test_detect_ios_format(self):
        """Test detection of iOS format"""
        ios_content = "[06/07/16, 8:04:11 PM] ~ Vino: Sir i am accepting it is my mistake"
        format_type = WhatsAppParserService.detect_format(ios_content)
        assert format_type == WhatsAppFormatType.IOS

    def test_detect_android_format(self):
        """Test detection of Android format"""
        android_content = "28/11/2025, 14:30 - John Doe: Hello everyone"
        format_type = WhatsAppParserService.detect_format(android_content)
        assert format_type == WhatsAppFormatType.ANDROID

    def test_detect_unknown_format(self):
        """Test detection of unknown format"""
        unknown_content = "This is not a valid WhatsApp export"
        format_type = WhatsAppParserService.detect_format(unknown_content)
        assert format_type == WhatsAppFormatType.UNKNOWN

    def test_detect_mixed_format_prefers_ios(self):
        """Test detection with mixed formats (more iOS)"""
        mixed_content = """[06/07/16, 8:04:11 PM] ~ Vino: Sir i am accepting
[10/07/16, 1:45:43 PM] Srinivas: Available for sale
[12/07/16, 9:20:41 AM] Fransis: I have a request
28/11/2025, 14:30 - John Doe: Hello"""
        format_type = WhatsAppParserService.detect_format(mixed_content)
        assert format_type == WhatsAppFormatType.IOS

    def test_detect_mixed_format_prefers_android(self):
        """Test detection with mixed formats (more Android)"""
        mixed_content = """[06/07/16, 8:04:11 PM] ~ Vino: Sir i am accepting
28/11/2025, 14:30 - John Doe: Hello
28/11/2025, 15:45 - Jane Smith: Property available
29/11/2025, 09:15 - Mike Jones: Interested"""
        format_type = WhatsAppParserService.detect_format(mixed_content)
        assert format_type == WhatsAppFormatType.ANDROID


class TestIOSParsing:
    """Tests for iOS format parsing (backward compatibility)"""

    def test_parse_ios_single_message(self):
        """Test parsing a single iOS message"""
        ios_content = "[06/07/16, 8:04:11 PM] Vino: Sir i am accepting it is my mistake"
        messages = WhatsAppParserService.parse_file_content(ios_content)

        assert len(messages) == 1
        assert messages[0]["sender_name"] == "Vino"
        assert messages[0]["message_text"] == "Sir i am accepting it is my mistake"
        assert messages[0]["message_date"].year == 2016
        assert messages[0]["message_date"].month == 7
        assert messages[0]["message_date"].day == 6
        assert messages[0]["is_deleted"] is False
        assert messages[0]["is_media"] is False

    def test_parse_ios_multiple_messages(self):
        """Test parsing multiple iOS messages"""
        ios_content = """[06/07/16, 8:04:11 PM] Vino: First message
[10/07/16, 1:45:43 PM] Srinivas: Second message
[12/07/16, 9:20:41 AM] Fransis: Third message"""
        messages = WhatsAppParserService.parse_file_content(ios_content)

        assert len(messages) == 3
        assert messages[0]["sender_name"] == "Vino"
        assert messages[1]["sender_name"] == "Srinivas"
        assert messages[2]["sender_name"] == "Fransis"

    def test_parse_ios_multiline_message(self):
        """Test parsing iOS multiline message"""
        ios_content = """[06/07/16, 8:04:11 PM] Vino: First line
Second line
Third line
[10/07/16, 1:45:43 PM] Srinivas: Next message"""
        messages = WhatsAppParserService.parse_file_content(ios_content)

        assert len(messages) == 2
        assert "First line\nSecond line\nThird line" in messages[0]["message_text"]
        assert messages[1]["message_text"] == "Next message"

    def test_parse_ios_deleted_message(self):
        """Test detection of deleted iOS message"""
        ios_content = "[06/07/16, 8:04:11 PM] Vino: This message was deleted"
        messages = WhatsAppParserService.parse_file_content(ios_content)

        assert len(messages) == 1
        assert messages[0]["is_deleted"] is True

    def test_parse_ios_media_message(self):
        """Test detection of iOS media message"""
        ios_content = "[06/07/16, 8:04:11 PM] Vino: <image omitted>"
        messages = WhatsAppParserService.parse_file_content(ios_content)

        assert len(messages) == 1
        assert messages[0]["is_media"] is True

    def test_parse_ios_with_unicode(self):
        """Test parsing iOS message with unicode characters"""
        ios_content = "[06/07/16, 8:04:11 PM] ‪+91 98861 35757‬: Rental Inventory"
        messages = WhatsAppParserService.parse_file_content(ios_content)

        assert len(messages) == 1
        assert "+91" in messages[0]["sender_name"]

    def test_parse_ios_am_pm_handling(self):
        """Test correct AM/PM handling in iOS format"""
        ios_content = """[06/07/16, 8:04:11 AM] Vino: Morning message
[06/07/16, 8:04:11 PM] Srinivas: Evening message"""
        messages = WhatsAppParserService.parse_file_content(ios_content)

        assert len(messages) == 2
        # Morning message should be 08:04 AM
        assert messages[0]["message_date"].hour == 8
        # Evening message should be 20:04 (8 PM in 24-hour format)
        assert messages[1]["message_date"].hour == 20


class TestAndroidParsing:
    """Tests for Android format parsing (new functionality)"""

    def test_parse_android_single_message(self):
        """Test parsing a single Android message"""
        android_content = "28/11/2025, 14:30 - John Doe: Hello everyone"
        messages = WhatsAppParserService.parse_file_content(android_content)

        assert len(messages) == 1
        assert messages[0]["sender_name"] == "John Doe"
        assert messages[0]["message_text"] == "Hello everyone"
        assert messages[0]["message_date"].year == 2025
        assert messages[0]["message_date"].month == 11
        assert messages[0]["message_date"].day == 28
        assert messages[0]["message_date"].hour == 14
        assert messages[0]["message_date"].minute == 30
        assert messages[0]["is_deleted"] is False
        assert messages[0]["is_media"] is False

    def test_parse_android_multiple_messages(self):
        """Test parsing multiple Android messages"""
        android_content = """28/11/2025, 14:30 - John Doe: First message
28/11/2025, 15:45 - Jane Smith: Second message
29/11/2025, 09:15 - Mike Jones: Third message"""
        messages = WhatsAppParserService.parse_file_content(android_content)

        assert len(messages) == 3
        assert messages[0]["sender_name"] == "John Doe"
        assert messages[1]["sender_name"] == "Jane Smith"
        assert messages[2]["sender_name"] == "Mike Jones"

    def test_parse_android_multiline_message(self):
        """Test parsing Android multiline message"""
        android_content = """28/11/2025, 14:30 - John Doe: First line
Second line
Third line
28/11/2025, 15:45 - Jane Smith: Next message"""
        messages = WhatsAppParserService.parse_file_content(android_content)

        assert len(messages) == 2
        assert "First line\nSecond line\nThird line" in messages[0]["message_text"]
        assert messages[1]["message_text"] == "Next message"

    def test_parse_android_24hour_format(self):
        """Test correct 24-hour format handling in Android"""
        android_content = """28/11/2025, 8:30 - John: Morning
28/11/2025, 14:30 - Jane: Afternoon
28/11/2025, 23:59 - Mike: Late night"""
        messages = WhatsAppParserService.parse_file_content(android_content)

        assert len(messages) == 3
        assert messages[0]["message_date"].hour == 8
        assert messages[1]["message_date"].hour == 14
        assert messages[2]["message_date"].hour == 23

    def test_parse_android_single_digit_date(self):
        """Test Android format with single digit day/month"""
        android_content = "3/4/2025, 9:15 - John: Test message"
        messages = WhatsAppParserService.parse_file_content(
            android_content,
            format=WhatsAppFormatType.ANDROID
        )

        assert len(messages) == 1
        assert messages[0]["message_date"].day == 3
        assert messages[0]["message_date"].month == 4

    def test_parse_android_single_digit_time(self):
        """Test Android format with single digit hour"""
        android_content = "28/11/2025, 9:15 - John: Test message"
        messages = WhatsAppParserService.parse_file_content(android_content)

        assert len(messages) == 1
        assert messages[0]["message_date"].hour == 9

    def test_parse_android_property_listing(self):
        """Test parsing Android message with property listing format"""
        android_content = """4/28/25, 8:31 AM - Vinay Gowda: *Purchasing Requirement for Villa*
	•	Property Type: Individual Villa
	•	Location: North Bangalore
	•	Budget: ₹1.1 Crore
	•	Plot Size: 30x40 (1200 sq.ft)
	•	Facing: East Facing
	•	Approval: Any Khata"""
        messages = WhatsAppParserService.parse_file_content(android_content)

        assert len(messages) == 1
        assert "*Purchasing Requirement for Villa*" in messages[0]["message_text"]
        assert "Budget: ₹1.1 Crore" in messages[0]["message_text"]


class TestFormatParameter:
    """Tests for explicit format parameter"""

    def test_parse_with_explicit_ios_format(self):
        """Test parsing with explicit iOS format specification"""
        ios_content = "[06/07/16, 8:04:11 PM] Vino: Test message"
        messages = WhatsAppParserService.parse_file_content(
            ios_content,
            format=WhatsAppFormatType.IOS
        )

        assert len(messages) == 1
        assert messages[0]["sender_name"] == "Vino"

    def test_parse_with_explicit_android_format(self):
        """Test parsing with explicit Android format specification"""
        android_content = "28/11/2025, 14:30 - John Doe: Test message"
        messages = WhatsAppParserService.parse_file_content(
            android_content,
            format=WhatsAppFormatType.ANDROID
        )

        assert len(messages) == 1
        assert messages[0]["sender_name"] == "John Doe"

    def test_parse_with_unknown_format_raises_error(self):
        """Test that unknown format raises ValueError"""
        unknown_content = "This is not a valid WhatsApp export format"
        with pytest.raises(ValueError, match="Unable to detect WhatsApp export format"):
            WhatsAppParserService.parse_file_content(unknown_content)


class TestHashCalculation:
    """Tests for message deduplication hash"""

    def test_hash_consistency_same_message(self):
        """Test that same message text produces same hash"""
        message_text = "Available for sale in Bangalore"
        hash1 = WhatsAppParserService.calculate_message_hash(
            {"message_text": message_text}
        )
        hash2 = WhatsAppParserService.calculate_message_hash(
            {"message_text": message_text}
        )

        assert hash1 == hash2

    def test_hash_different_for_different_messages(self):
        """Test that different messages produce different hashes"""
        hash1 = WhatsAppParserService.calculate_message_hash(
            {"message_text": "Message 1"}
        )
        hash2 = WhatsAppParserService.calculate_message_hash(
            {"message_text": "Message 2"}
        )

        assert hash1 != hash2

    def test_hash_ignores_sender_and_date(self):
        """Test that hash is based on message text only"""
        message_text = "Property available for sale"
        hash1 = WhatsAppParserService.calculate_message_hash({
            "message_text": message_text,
            "sender_name": "Agent1",
            "message_date": "2025-11-28"
        })
        hash2 = WhatsAppParserService.calculate_message_hash({
            "message_text": message_text,
            "sender_name": "Agent2",
            "message_date": "2025-11-29"
        })

        assert hash1 == hash2

    def test_hash_same_across_formats(self):
        """Test that same property in different formats produces same hash"""
        message_text = "3 BHK apartment available for rent"
        hash1 = WhatsAppParserService.calculate_message_hash({
            "message_text": message_text
        })
        hash2 = WhatsAppParserService.calculate_message_hash({
            "message_text": message_text
        })

        assert hash1 == hash2


class TestErrorHandling:
    """Tests for error handling"""

    def test_invalid_ios_datetime_skipped(self):
        """Test that invalid iOS datetime is handled gracefully"""
        ios_content = """[06/07/16, 8:04:11 PM] Vino: Valid message
[99/99/99, 99:99:99 ZZ] Invalid: Invalid datetime
[10/07/16, 1:45:43 PM] Srinivas: Another valid message"""
        messages = WhatsAppParserService.parse_file_content(ios_content)

        # Should parse valid messages, skip invalid
        assert len(messages) >= 2

    def test_empty_content(self):
        """Test parsing empty content"""
        messages = WhatsAppParserService.parse_file_content("")
        assert len(messages) == 0

    def test_content_with_only_newlines(self):
        """Test parsing content with only newlines"""
        messages = WhatsAppParserService.parse_file_content("\n\n\n")
        assert len(messages) == 0


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility"""

    def test_parse_file_content_without_format_parameter(self):
        """Test that parse_file_content works without format parameter (auto-detect)"""
        ios_content = "[06/07/16, 8:04:11 PM] Vino: Auto-detect test"
        messages = WhatsAppParserService.parse_file_content(ios_content)

        assert len(messages) == 1
        assert messages[0]["sender_name"] == "Vino"

    def test_boundary_pattern_alias_exists(self):
        """Test that BOUNDARY_PATTERN alias exists for backward compatibility"""
        assert hasattr(WhatsAppParserService, "BOUNDARY_PATTERN")
        assert WhatsAppParserService.BOUNDARY_PATTERN == WhatsAppParserService.IOS_BOUNDARY_PATTERN

    def test_parse_file_with_source_file_parameter(self):
        """Test that source_file parameter still works"""
        ios_content = "[06/07/16, 8:04:11 PM] Vino: Test"
        messages = WhatsAppParserService.parse_file_content(
            ios_content,
            source_file="test_file.txt"
        )

        assert len(messages) == 1
        assert messages[0]["source_file"] == "test_file.txt"


class TestComplexScenarios:
    """Tests for complex real-world scenarios"""

    def test_ios_rental_inventory_message(self):
        """Test parsing iOS rental inventory message with multiple listings"""
        ios_content = """[11/3/25, 12:54:10 PM] ‪+91 98861 35757‬: Rental Inventory

1.  Brigade Lavelle,
Lavelle road cross , Grade A building , cul de sac, quiet location
Ground floor, apprx 2500sft (including 1 very large Sit-out balcony and 1 small balcony), 3bhk , 2 car parks, fully furnished
2 balconies.
Rent 1.7 lacs including maintenance

2.  Near Ulsoor lake
Quiet Residential location
Duplex Penthouse with pvt terrace
2700sft + 1000sft terrace
4bhk, 1 car park , furnished
Rent 2.25 lacs + M"""
        messages = WhatsAppParserService.parse_file_content(ios_content)

        assert len(messages) == 1
        assert "Brigade Lavelle" in messages[0]["message_text"]
        assert "Ulsoor lake" in messages[0]["message_text"]
        assert messages[0]["sender_name"] == "+91 98861 35757"

    def test_android_property_sale_message(self):
        """Test parsing Android property sale message"""
        android_content = """4/28/25, 8:31 AM - Vinay Gowda: *Available flat for sale in Regency La Majada*

3 bhk with servants accommodation
2574 sft
Lower floor
2 car parks
Semi furnished

Price - 3.35 Cr (Negotiable)"""
        messages = WhatsAppParserService.parse_file_content(android_content)

        assert len(messages) == 1
        assert "Regency La Majada" in messages[0]["message_text"]
        assert "3.35 Cr" in messages[0]["message_text"]

    def test_message_with_special_characters(self):
        """Test parsing messages with special characters and emojis"""
        ios_content = "[06/07/16, 8:04:11 PM] Vino: ✓ Available 🏠 Beautiful apartment! Price: ₹50,00,000"
        messages = WhatsAppParserService.parse_file_content(ios_content)

        assert len(messages) == 1
        assert "₹50,00,000" in messages[0]["message_text"]
