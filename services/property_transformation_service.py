"""
Property Transformation Service
================================

Transforms property listings from different sources (WhatsApp, properties table)
into a unified schema for consistent frontend rendering.

Purpose:
    - Normalize field names across sources (bedroom_count → bedrooms)
    - Handle missing/NULL fields gracefully
    - Add source identifier for tracking
    - Ensure consistent data types

Transformations:
    1. WhatsApp Listings → Unified Schema
       - Maps whatsapp_listing_data fields to unified format
       - Sets source = 'whatsapp'
       - Preserves message_type, raw_message

    2. Properties (with agent) → Unified Schema
       - Maps properties_with_agent view fields to unified format
       - Sets source = 'properties'
       - Includes agent details from JOIN
       - Preserves static_flyer_url, verified_by
"""

from typing import Dict, Any, Optional, List
from datetime import datetime


class PropertyTransformationService:
    """Service for transforming property data from different sources to unified schema"""

    @staticmethod
    def whatsapp_to_unified(whatsapp_listing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform WhatsApp listing to unified schema

        Field Mappings:
            - bedroom_count → bedrooms
            - area_sqft → sqft
            - agent_name → agent_name (direct)
            - agent_contact → agent_contact (direct)
            - location → location
            - project_name → title + project_name
            - raw_message → description (truncated) + raw_message

        Args:
            whatsapp_listing: Raw WhatsApp listing from whatsapp_listing_data table

        Returns:
            Dictionary matching UnifiedPropertyListing schema
        """
        # Extract core fields with safe defaults
        listing_id = whatsapp_listing.get("id")
        message_date = whatsapp_listing.get("message_date")
        created_at = whatsapp_listing.get("created_at", message_date)
        sender_name = whatsapp_listing.get("sender_name")

        # Parse message_date datetime if string
        if isinstance(message_date, str):
            try:
                message_date = datetime.fromisoformat(message_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                message_date = None

        # Parse created_at datetime if string
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = datetime.now()

        # Property details
        property_type = whatsapp_listing.get("property_type")
        bedroom_count = whatsapp_listing.get("bedroom_count")
        area_sqft = whatsapp_listing.get("area_sqft")
        price = whatsapp_listing.get("price")
        price_text = whatsapp_listing.get("price_text")
        location = whatsapp_listing.get("location")
        project_name = whatsapp_listing.get("project_name")
        furnishing_status = whatsapp_listing.get("furnishing_status")
        parking_count = whatsapp_listing.get("parking_count")
        facing_direction = whatsapp_listing.get("facing_direction")
        special_features = whatsapp_listing.get("special_features", [])

        # Agent information
        agent_name = whatsapp_listing.get("agent_name")
        agent_contact = whatsapp_listing.get("agent_contact")
        company_name = whatsapp_listing.get("company_name")

        # WhatsApp-specific fields
        message_type = whatsapp_listing.get("message_type")
        raw_message = whatsapp_listing.get("raw_message", "")

        # Generate title from project_name or property details
        title = project_name or f"{bedroom_count}BHK {property_type or 'Property'} in {location or 'Unknown'}" if bedroom_count else (property_type or "Property Listing")

        # Generate description from raw message (truncate if too long)
        description = raw_message[:500] + "..." if len(raw_message) > 500 else raw_message

        return {
            # Core identification
            "id": listing_id,
            "source": "whatsapp",
            "sender_name": sender_name,

            # Basic property info
            "title": title,
            "description": description,
            "property_type": property_type,

            # Property specifications
            "bedrooms": bedroom_count,
            "bathrooms": None,  # Not available in WhatsApp listings
            "sqft": float(area_sqft) if area_sqft else None,
            "price": float(price) if price else None,
            "price_text": price_text,

            # Location
            "location": location,
            "project_name": project_name,

            # Property features
            "furnishing_status": furnishing_status,
            "facing_direction": facing_direction,
            "parking_count": parking_count,
            "special_features": special_features or [],

            # Media
            "images": [],  # WhatsApp listings don't have images stored

            # Agent/Contact information
            "agent_name": agent_name,
            "agent_contact": agent_contact,
            "agent_email": None,  # Not available
            "company_name": company_name,
            "agent_avatar": None,
            "agent_vanity_url": None,

            # Owner information
            "owner_name": None,
            "owner_number": None,

            # Status and metadata
            "status": "available",  # Inferred for WhatsApp listings
            "created_at": created_at,
            "updated_at": None,

            # WhatsApp-specific fields
            "message_type": message_type,
            "message_date": message_date,
            "raw_message": raw_message,

            # Properties-specific fields (NULL for WhatsApp)
            "static_flyer_url": None,
            "static_html_url": None,
            "verified_by": None,
            "view_count": None,
            "currency": None,

            # Additional metadata
            "source_key": f"whatsapp:{listing_id}"
        }

    @staticmethod
    def properties_to_unified(property_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform properties table record (with agent details from view) to unified schema

        Field Mappings:
            - bedrooms → bedrooms (direct)
            - sqft → sqft (direct)
            - baths → bathrooms
            - facing_dir → facing_direction
            - agent_name (from view JOIN) → agent_name
            - agent_contact (from view JOIN) → agent_contact
            - city + area → location

        Args:
            property_record: Raw property from properties_with_agent view

        Returns:
            Dictionary matching UnifiedPropertyListing schema
        """
        # Extract core fields
        property_id = property_record.get("id")
        created_at = property_record.get("created_at")
        updated_at = property_record.get("updated_at")

        # Parse datetime if string
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = datetime.now()

        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = None

        # Property details
        title = property_record.get("title")
        description = property_record.get("description")
        property_type = property_record.get("property_type") or property_record.get("asset_type")
        bedrooms = property_record.get("bedrooms")
        bathrooms = property_record.get("baths")
        sqft = property_record.get("sqft")
        price = property_record.get("price")
        currency = property_record.get("currency", "INR")

        # Location (combine city + area)
        city = property_record.get("city")
        area = property_record.get("area")
        location = f"{city}, {area}" if city and area else (city or area or "Unknown")

        # Property features
        facing_dir = property_record.get("facing_dir")
        images = property_record.get("images", [])
        status = property_record.get("status")

        # Agent information (from view JOIN with profiles)
        agent_name = property_record.get("agent_name")
        agent_contact = property_record.get("agent_contact")
        agent_email = property_record.get("agent_email")
        agent_company = property_record.get("agent_company")
        agent_avatar = property_record.get("agent_avatar")
        agent_vanity_url = property_record.get("agent_vanity_url")

        # Owner information (if different from agent)
        owner_name = property_record.get("owner_name")
        owner_number = property_record.get("owner_number")

        # Properties-specific fields
        static_flyer_url = property_record.get("static_flyer_url")
        static_html_url = property_record.get("static_html_url")
        verified_by = property_record.get("verified_by")
        view_count = property_record.get("view_count")
        source_key = property_record.get("source_key")

        return {
            # Core identification
            "id": property_id,
            "source": "properties",

            # Basic property info
            "title": title,
            "description": description,
            "property_type": property_type,

            # Property specifications
            "bedrooms": int(bedrooms) if bedrooms is not None else None,
            "bathrooms": int(bathrooms) if bathrooms is not None else None,
            "sqft": float(sqft) if sqft else None,
            "price": float(price) if price else None,
            "price_text": None,  # Not available in properties table

            # Location
            "location": location,
            "project_name": title,  # Use title as project_name for consistency

            # Property features
            "furnishing_status": None,  # Not available in properties table
            "facing_direction": facing_dir,
            "parking_count": None,  # Not available in properties table
            "special_features": [],  # Not available in properties table

            # Media
            "images": images or [],

            # Agent/Contact information (from view JOIN)
            "agent_name": agent_name,
            "agent_contact": agent_contact,
            "agent_email": agent_email,
            "company_name": agent_company,
            "agent_avatar": agent_avatar,
            "agent_vanity_url": agent_vanity_url,

            # Owner information
            "owner_name": owner_name,
            "owner_number": str(owner_number) if owner_number else None,

            # Status and metadata
            "status": status,
            "created_at": created_at,
            "updated_at": updated_at,

            # WhatsApp-specific fields (NULL for properties)
            "message_type": None,
            "message_date": None,
            "raw_message": None,

            # Properties-specific fields
            "static_flyer_url": static_flyer_url,
            "static_html_url": static_html_url,
            "verified_by": verified_by,
            "view_count": view_count,
            "currency": currency,

            # Additional metadata
            "source_key": source_key or f"properties:{property_id}"
        }

    @staticmethod
    def transform_batch(
        source: str,
        records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Transform a batch of records from a specific source

        Args:
            source: Data source ('whatsapp' or 'properties')
            records: List of raw records from the source

        Returns:
            List of transformed records with unified schema

        Raises:
            ValueError: If source is not recognized
        """
        if source == "whatsapp":
            return [PropertyTransformationService.whatsapp_to_unified(record) for record in records]
        elif source == "properties":
            return [PropertyTransformationService.properties_to_unified(record) for record in records]
        else:
            raise ValueError(f"Unknown source: {source}. Expected 'whatsapp' or 'properties'")
