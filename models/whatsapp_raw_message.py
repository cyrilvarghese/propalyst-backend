"""
Pydantic models for WhatsApp raw messages

These models represent individual parsed messages from WhatsApp chat exports.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WhatsAppRawMessageCreate(BaseModel):
    """
    Model for creating a new WhatsApp raw message
    Used when inserting parsed messages into the database
    """
    message_date: datetime = Field(
        ...,
        description="Timestamp when the message was sent (from WhatsApp export)"
    )
    sender_name: str = Field(
        ...,
        min_length=1,
        description="Name or phone number of the message sender"
    )
    message_text: str = Field(
        ...,
        description="Full message body (may include multiple lines)"
    )
    is_deleted: bool = Field(
        default=False,
        description="True if message was deleted"
    )
    is_media: bool = Field(
        default=False,
        description="True if message is media (image/video omitted)"
    )
    source_file: Optional[str] = Field(
        default=None,
        description="Name of the source file this message was parsed from"
    )
    line_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="Line number in source file where message started"
    )


class WhatsAppRawMessage(WhatsAppRawMessageCreate):
    """
    Complete WhatsApp raw message model (includes database fields)
    """
    id: str = Field(
        ...,
        description="Unique identifier (UUID)"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when record was created in database"
    )


class WhatsAppParseResponse(BaseModel):
    """
    Response model for parse operations
    """
    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    messages_parsed: int = Field(
        default=0,
        ge=0,
        description="Number of messages successfully parsed"
    )
    messages_inserted: int = Field(
        default=0,
        ge=0,
        description="Number of messages successfully inserted into database"
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional message with details or error information"
    )
    errors: Optional[list[str]] = Field(
        default=None,
        description="List of any errors encountered during processing"
    )


class WhatsAppMessageFilters(BaseModel):
    """
    Query filters for retrieving WhatsApp messages
    """
    sender_name: Optional[str] = Field(
        default=None,
        description="Filter by sender name (exact match)"
    )
    source_file: Optional[str] = Field(
        default=None,
        description="Filter by source file name"
    )
    date_from: Optional[datetime] = Field(
        default=None,
        description="Filter messages from this date onwards"
    )
    date_to: Optional[datetime] = Field(
        default=None,
        description="Filter messages up to this date"
    )
    is_deleted: Optional[bool] = Field(
        default=None,
        description="Filter by deleted status"
    )
    is_media: Optional[bool] = Field(
        default=None,
        description="Filter by media status"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of messages to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of messages to skip"
    )
