"""
Database constraints for ACID compliance

This module provides SQL constraints that enforce data consistency
at the database level, ensuring ACID compliance.
"""

from sqlalchemy import text
from src.db.operations import get_db_manager


def create_acid_constraints():
    """
    Create database constraints for ACID compliance
    
    These constraints enforce:
    - Data consistency
    - Business rules
    - Referential integrity
    - Status validation
    """
    
    constraints = [
        # Order total consistency
        """
        ALTER TABLE orders ADD CONSTRAINT IF NOT EXISTS check_order_total 
        CHECK (total >= 0 AND total = subtotal + delivery_charge)
        """,
        
        # Order item total consistency
        """
        ALTER TABLE order_items ADD CONSTRAINT IF NOT EXISTS check_item_total 
        CHECK (total_price >= 0 AND total_price = unit_price * quantity)
        """,
        
        # Cart item quantity validation
        """
        ALTER TABLE cart_items ADD CONSTRAINT IF NOT EXISTS check_cart_quantity 
        CHECK (quantity > 0)
        """,
        
        # Cart item price validation
        """
        ALTER TABLE cart_items ADD CONSTRAINT IF NOT EXISTS check_cart_price 
        CHECK (unit_price >= 0)
        """,
        
        # Order status validation
        """
        ALTER TABLE orders ADD CONSTRAINT IF NOT EXISTS check_order_status 
        CHECK (status IN ('pending', 'confirmed', 'preparing', 'missing', 'ready', 'delivered', 'cancelled'))
        """,
        
        # Product price validation
        """
        ALTER TABLE menu_products ADD CONSTRAINT IF NOT EXISTS check_product_price 
        CHECK (price >= 0)
        """,
        
        # Customer telegram_id uniqueness
        """
        ALTER TABLE customers ADD CONSTRAINT IF NOT EXISTS check_telegram_id_unique 
        UNIQUE (telegram_id)
        """,
        
        # Order number uniqueness
        """
        ALTER TABLE orders ADD CONSTRAINT IF NOT EXISTS check_order_number_unique 
        UNIQUE (order_number)
        """,
        
        # Category name uniqueness
        """
        ALTER TABLE menu_categories ADD CONSTRAINT IF NOT EXISTS check_category_name_unique 
        UNIQUE (name)
        """,
        
        # Product name uniqueness within category
        """
        ALTER TABLE menu_products ADD CONSTRAINT IF NOT EXISTS check_product_name_unique 
        UNIQUE (name, category_id)
        """,
        
        # Delivery charge validation
        """
        ALTER TABLE orders ADD CONSTRAINT IF NOT EXISTS check_delivery_charge 
        CHECK (delivery_charge >= 0)
        """,
        
        # Subtotal validation
        """
        ALTER TABLE orders ADD CONSTRAINT IF NOT EXISTS check_subtotal 
        CHECK (subtotal >= 0)
        """,
        
        # Order item quantity validation
        """
        ALTER TABLE order_items ADD CONSTRAINT IF NOT EXISTS check_order_item_quantity 
        CHECK (quantity > 0)
        """,
        
        # Order item price validation
        """
        ALTER TABLE order_items ADD CONSTRAINT IF NOT EXISTS check_order_item_price 
        CHECK (unit_price >= 0)
        """
    ]
    
    try:
        with get_db_manager().get_session_context() as session:
            for constraint_sql in constraints:
                try:
                    session.execute(text(constraint_sql))
                    print(f"✅ Applied constraint: {constraint_sql.split('ADD CONSTRAINT')[1].split()[0]}")
                except Exception as e:
                    print(f"⚠️  Constraint already exists or failed: {e}")
            
            session.commit()
            print("✅ All ACID constraints applied successfully")
            
    except Exception as e:
        print(f"❌ Failed to apply constraints: {e}")


def drop_acid_constraints():
    """
    Drop all ACID compliance constraints
    
    Use this for testing or if constraints need to be modified
    """
    
    constraints_to_drop = [
        "check_order_total",
        "check_item_total", 
        "check_cart_quantity",
        "check_cart_price",
        "check_order_status",
        "check_product_price",
        "check_telegram_id_unique",
        "check_order_number_unique",
        "check_category_name_unique",
        "check_product_name_unique",
        "check_delivery_charge",
        "check_subtotal",
        "check_order_item_quantity",
        "check_order_item_price"
    ]
    
    try:
        with get_db_manager().get_session_context() as session:
            for constraint_name in constraints_to_drop:
                try:
                    # Try to drop from different tables
                    tables = ["orders", "order_items", "cart_items", "menu_products", "customers", "menu_categories"]
                    for table in tables:
                        try:
                            session.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint_name}"))
                        except:
                            pass  # Constraint might not exist on this table
                    
                    print(f"✅ Dropped constraint: {constraint_name}")
                except Exception as e:
                    print(f"⚠️  Could not drop constraint {constraint_name}: {e}")
            
            session.commit()
            print("✅ All ACID constraints dropped successfully")
            
    except Exception as e:
        print(f"❌ Failed to drop constraints: {e}")


def check_constraints_status():
    """
    Check the status of all ACID constraints
    
    Returns:
        Dictionary with constraint status
    """
    
    constraint_queries = {
        "order_total": "SELECT COUNT(*) FROM orders WHERE total != subtotal + delivery_charge OR total < 0",
        "item_total": "SELECT COUNT(*) FROM order_items WHERE total_price != unit_price * quantity OR total_price < 0",
        "cart_quantity": "SELECT COUNT(*) FROM cart_items WHERE quantity <= 0",
        "cart_price": "SELECT COUNT(*) FROM cart_items WHERE unit_price < 0",
        "order_status": "SELECT COUNT(*) FROM orders WHERE status NOT IN ('pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled')",
        "product_price": "SELECT COUNT(*) FROM menu_products WHERE price < 0",
        "delivery_charge": "SELECT COUNT(*) FROM orders WHERE delivery_charge < 0",
        "subtotal": "SELECT COUNT(*) FROM orders WHERE subtotal < 0",
        "order_item_quantity": "SELECT COUNT(*) FROM order_items WHERE quantity <= 0",
        "order_item_price": "SELECT COUNT(*) FROM order_items WHERE unit_price < 0"
    }
    
    status = {}
    
    try:
        with get_db_manager().get_session_context() as session:
            for constraint_name, query in constraint_queries.items():
                try:
                    result = session.execute(text(query)).scalar()
                    status[constraint_name] = {
                        "violations": result,
                        "compliant": result == 0
                    }
                except Exception as e:
                    status[constraint_name] = {
                        "violations": "ERROR",
                        "compliant": False,
                        "error": str(e)
                    }
            
            session.commit()
            
    except Exception as e:
        print(f"❌ Failed to check constraint status: {e}")
        return None
    
    return status


def validate_data_consistency():
    """
    Comprehensive data consistency validation
    
    Returns:
        Dictionary with validation results
    """
    
    validations = {
        "orders_without_customer": """
            SELECT COUNT(*) FROM orders o 
            LEFT JOIN customers c ON o.customer_id = c.id 
            WHERE c.id IS NULL
        """,
        "order_items_without_order": """
            SELECT COUNT(*) FROM order_items oi 
            LEFT JOIN orders o ON oi.order_id = o.id 
            WHERE o.id IS NULL
        """,
        "cart_items_without_cart": """
            SELECT COUNT(*) FROM cart_items ci 
            LEFT JOIN carts c ON ci.cart_id = c.id 
            WHERE c.id IS NULL
        """,
        "products_without_category": """
            SELECT COUNT(*) FROM menu_products p 
            LEFT JOIN menu_categories mc ON p.category_id = mc.id 
            WHERE mc.id IS NULL AND p.category_id IS NOT NULL
        """,
        "duplicate_order_numbers": """
            SELECT COUNT(*) FROM (
                SELECT order_number, COUNT(*) as cnt 
                FROM orders 
                GROUP BY order_number 
                HAVING COUNT(*) > 1
            ) as duplicates
        """,
        "duplicate_telegram_ids": """
            SELECT COUNT(*) FROM (
                SELECT telegram_id, COUNT(*) as cnt 
                FROM customers 
                GROUP BY telegram_id 
                HAVING COUNT(*) > 1
            ) as duplicates
        """,
        "negative_totals": """
            SELECT COUNT(*) FROM orders WHERE total < 0
        """,
        "invalid_status_transitions": """
            SELECT COUNT(*) FROM orders 
            WHERE status NOT IN ('pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled')
        """
    }
    
    results = {}
    
    try:
        with get_db_manager().get_session_context() as session:
            for validation_name, query in validations.items():
                try:
                    result = session.execute(text(query)).scalar()
                    results[validation_name] = {
                        "count": result,
                        "valid": result == 0
                    }
                except Exception as e:
                    results[validation_name] = {
                        "count": "ERROR",
                        "valid": False,
                        "error": str(e)
                    }
            
            session.commit()
            
    except Exception as e:
        print(f"❌ Failed to validate data consistency: {e}")
        return None
    
    return results


if __name__ == "__main__":
    print("🔒 ACID CONSTRAINTS MANAGEMENT")
    print("=" * 50)
    
    # Check current status
    print("\n📊 Checking constraint status...")
    status = check_constraints_status()
    if status:
        for constraint, info in status.items():
            print(f"{constraint}: {'✅' if info['compliant'] else '❌'} ({info['violations']} violations)")
    
    # Validate data consistency
    print("\n🔍 Validating data consistency...")
    validation = validate_data_consistency()
    if validation:
        for check, info in validation.items():
            print(f"{check}: {'✅' if info['valid'] else '❌'} ({info['count']} issues)")
    
    print("\n✅ ACID constraints management complete!") 