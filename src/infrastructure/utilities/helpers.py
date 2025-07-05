"""
Utility functions for the Samna Salta bot
"""

from datetime import datetime, time

from ..configuration.config import get_config


def format_price(price: float, currency: str = "ILS") -> str:
    """Format price with currency"""
    return f"{price:.2f} {currency}"


def is_hilbeh_available() -> bool:
    """Check if Hilbeh is available today"""
    config = get_config()
    today = datetime.now().strftime("%A").lower()

    return today in config.hilbeh_available_days


def parse_time_range(time_range: str) -> tuple[time, time]:
    """Parse time range string (e.g., '09:00-18:00')"""
    start_str, end_str = time_range.split("-")
    start_time = datetime.strptime(start_str, "%H:%M").time()
    end_time = datetime.strptime(end_str, "%H:%M").time()
    return start_time, end_time


def is_within_business_hours() -> bool:
    """Check if current time is within business hours"""
    config = get_config()
    start_time, end_time = parse_time_range(config.hilbeh_available_hours)
    current_time = datetime.now().time()

    return start_time <= current_time <= end_time


def sanitize_phone_number(phone: str) -> str:
    """Sanitize phone number to standard format"""
    # Remove all non-digit characters
    digits_only = "".join(filter(str.isdigit, phone))

    # Handle Israeli phone numbers
    if digits_only.startswith("972"):
        return f"+{digits_only}"
    if digits_only.startswith("0"):
        return f"+972{digits_only[1:]}"
    if len(digits_only) == 9:
        return f"+972{digits_only}"
    return f"+{digits_only}"


def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    sanitized = sanitize_phone_number(phone)

    # Check basic Israeli format
    if not sanitized.startswith("+972") or len(sanitized) != 13:
        return False

    # Check for valid Israeli mobile prefixes
    # After sanitization, 050 becomes 50, 052 becomes 52, etc.
    # Valid Israeli mobile prefixes after removing leading zero: 50, 52, 53, 54, 55, 57, 58
    mobile_part = sanitized[
        4:6
    ]  # Extract the 2-digit prefix after +972 (first two digits)
    valid_prefixes = ["50", "52", "53", "54", "55", "57", "58"]

    return mobile_part in valid_prefixes


def translate_product_name(product_name: str, options: dict = None) -> str:
    """
    Translate a product name from database format to localized display name
    
    Args:
        product_name: The product name as stored in the database
        options: Product options (type, size, etc.)
    
    Returns:
        Localized product display name
    """
    from src.infrastructure.utilities.i18n import tr
    
    # Map database product names to translation keys
    product_name_lower = product_name.lower()
    
    if "kubaneh" in product_name_lower:
        if options and "type" in options:
            kubaneh_type = options["type"]
            type_key = f"KUBANEH_{kubaneh_type.upper()}"
            type_display = tr(type_key)
            return tr("KUBANEH_DISPLAY_NAME").format(type=type_display)
        return tr("PRODUCT_KUBANEH_CLASSIC")
    
    elif "samneh" in product_name_lower:
        if options and "smoking" in options:
            smoking_type = options["smoking"].replace(" ", "_")
            type_key = f"SAMNEH_{smoking_type.upper()}"
            type_display = tr(type_key)
            return tr("SAMNEH_DISPLAY_NAME").format(type=type_display)
        return tr("PRODUCT_SAMNEH_SMOKED")
    
    elif "red bisbas" in product_name_lower or "bisbas" in product_name_lower:
        if options and "size" in options:
            size = options["size"]
            size_key = f"SIZE_{size.upper()}"
            size_display = tr(size_key)
            return tr("RED_BISBAS_DISPLAY_NAME").format(size=size_display)
        return tr("PRODUCT_RED_BISBAS")
    
    elif "hilbeh" in product_name_lower:
        return tr("PRODUCT_HILBEH")
    
    elif "hawaij" in product_name_lower and "soup" in product_name_lower:
        return tr("PRODUCT_HAWAIJ_SOUP")
    
    elif "hawaij" in product_name_lower and "coffee" in product_name_lower:
        return tr("PRODUCT_HAWAIJ_COFFEE")
    
    elif "white coffee" in product_name_lower:
        return tr("PRODUCT_WHITE_COFFEE")
    
    # Fallback to original name if no translation found
    return product_name
