"""Backward-compatible imports for the requests module."""

from modules.requests.service import (
    ACCOMMODATION_TYPES,
    CATEGORY_KEYWORDS,
    NON_OPERATIONAL_SIGNALS,
    REQUEST_SIGNALS,
    classify_service_request,
    confirm_service_request,
    create_service_request,
    get_service_request,
    is_accommodation_entity,
    sheet_command,
)
