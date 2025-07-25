"""
Text formatting utilities for the Telegram bot
"""

from typing import Optional


def center_text(text: str, prefix: str = "", suffix: str = "") -> str:
    """
    Center text using Unicode characters and spacing
    
    Args:
        text: The text to center
        prefix: Optional prefix to add before the centered text
        suffix: Optional suffix to add after the centered text
        
    Returns:
        Centered text using Unicode characters
    """
    if not text:
        return text
    
    # Split text into lines and center each line
    lines = text.split('\n')
    centered_lines = []
    
    for line in lines:
        if line.strip():  # Only center non-empty lines
            # Use Unicode center dot or other characters for visual centering
            centered_lines.append(f"• {line} •")
        else:
            centered_lines.append(line)  # Keep empty lines as-is
    
    result = '\n'.join(centered_lines)
    
    # Add prefix and suffix if provided
    if prefix:
        result = f"{prefix}\n{result}"
    if suffix:
        result = f"{result}\n{suffix}"
    
    return result


def format_title(title: str) -> str:
    """
    Format a title with proper centering and styling
    
    Args:
        title: The title text
        
    Returns:
        Formatted title
    """
    # Use Unicode characters to create visual centering effect
    # The horizontal lines create a frame that makes the text appear centered
    return f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{title}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def format_section_header(header: str) -> str:
    """
    Format a section header with centering
    
    Args:
        header: The header text
        
    Returns:
        Formatted header
    """
    return f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📋 {header}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def format_product_info(name: str, description: str, price: float, category: str = "") -> str:
    """
    Format product information with centering
    
    Args:
        name: Product name
        description: Product description
        price: Product price
        category: Product category (optional)
        
    Returns:
        Formatted product information
    """
    lines = []
    
    # Product name
    lines.append(format_title(name))
    lines.append("")
    
    # Description
    if description:
        lines.append(f"📄 {description}")
        lines.append("")
    
    # Price
    lines.append(f"💰 <b>₪{price:.2f}</b>")
    
    # Category (if provided)
    if category:
        lines.append("")
        lines.append(f"📂 {category}")
    
    return '\n'.join(lines)


def format_cart_item(index: int, name: str, quantity: int, price: float, total: float) -> str:
    """
    Format a cart item with centering
    
    Args:
        index: Item index
        name: Product name
        quantity: Quantity
        price: Unit price
        total: Total price for this item
        
    Returns:
        Formatted cart item
    """
    return f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n<b>{index}.</b> 📦 <b>{name}</b>\n🔢 כמות: {quantity}\n💰 מחיר: ₪{price:.2f}\n💵 סה״כ: ₪{total:.2f}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def format_order_summary(items: list, total: float, delivery_method: str = "", delivery_address: str = "") -> str:
    """
    Format order summary with centering
    
    Args:
        items: List of order items
        total: Total order amount
        delivery_method: Delivery method (optional)
        delivery_address: Delivery address (optional)
        
    Returns:
        Formatted order summary
    """
    lines = []
    
    # Title
    lines.append(format_title("סיכום הזמנה"))
    lines.append("")
    
    # Items
    for i, item in enumerate(items, 1):
        lines.append(format_cart_item(
            i, 
            item.get('name', 'Unknown'), 
            item.get('quantity', 1), 
            item.get('price', 0), 
            item.get('total', 0)
        ))
        lines.append("")
    
    # Total
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💸 <b>סה״כ: ₪{total:.2f}</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Delivery info
    if delivery_method:
        lines.append("")
        lines.append(f"🚚 שיטת משלוח: {delivery_method}")
    
    if delivery_address:
        lines.append("")
        lines.append(f"📍 כתובת: {delivery_address}")
    
    return '\n'.join(lines)


def format_welcome_message(business_name: str, user_name: str = "") -> str:
    """
    Format welcome message with centering
    
    Args:
        business_name: Business name
        user_name: User name (optional)
        
    Returns:
        Formatted welcome message
    """
    lines = []
    
    # Welcome header
    if user_name:
        lines.append(format_title(f"ברוכים הבאים, {user_name}!"))
    else:
        lines.append(format_title("ברוכים הבאים!"))
    
    lines.append("")
    
    # Business name
    lines.append(f"🏪 <b>{business_name}</b>")
    lines.append("")
    
    # Welcome message
    lines.append("אנחנו שמחים להגיש לכם את המעדנים התימניים האותנטיים שלנו.")
    lines.append("")
    lines.append("מה תרצו להזמין היום?")
    
    return '\n'.join(lines)


def format_error_message(error_text: str) -> str:
    """
    Format error message with centering
    
    Args:
        error_text: Error message
        
    Returns:
        Formatted error message
    """
    return f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n❌ {error_text}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def format_success_message(success_text: str) -> str:
    """
    Format success message with centering
    
    Args:
        success_text: Success message
        
    Returns:
        Formatted success message
    """
    return f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ {success_text}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def format_info_message(info_text: str) -> str:
    """
    Format info message with centering
    
    Args:
        info_text: Info message
        
    Returns:
        Formatted info message
    """
    return f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nℹ️ {info_text}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" 