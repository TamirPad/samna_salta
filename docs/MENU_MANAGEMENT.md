# 🍽️ Admin Menu Management System

## Overview

The Admin Menu Management System allows restaurant administrators to fully control their product menu through the Telegram bot interface. This comprehensive system provides CRUD (Create, Read, Update, Delete) operations for products with a user-friendly interface.

## Features

### 📋 Product Management
- **View All Products**: See all products (active and inactive) with status indicators
- **Add New Products**: Create new products with name, description, category, and price
- **Edit Existing Products**: Update product details including name, description, category, price, and status
- **Delete Products**: Soft delete products (deactivate) while preserving order history
- **Toggle Product Status**: Quickly activate/deactivate products

### 📂 Category Management
- **View Categories**: See all product categories with product counts
- **Filter by Category**: View products organized by category
- **Category-based Navigation**: Easy navigation through category-specific product lists

### 🔍 Search Functionality
- **Product Search**: Search products by name or description
- **Real-time Results**: Instant search results with product details
- **Minimum Search Length**: 2-character minimum for meaningful results

### 📊 Dashboard Overview
- **Product Statistics**: Total, active, and inactive product counts
- **Category Count**: Number of unique product categories
- **Quick Actions**: Easy access to all management functions

## How to Use

### Accessing Menu Management

1. **Start the bot** and use the `/admin` command
2. **Click "🍽️ Menu Management"** from the admin dashboard
3. **Navigate** through the menu management interface

### Adding a New Product

1. **Click "➕ Add New Product"** from the menu management dashboard
2. **Enter product details** in the following format:
   ```
   Name: Product Name
   Description: Product description
   Category: Product category
   Price: 25.00
   ```
3. **Submit** the product details
4. **Confirm** the product creation

### Editing a Product

1. **View all products** and click on the product you want to edit
2. **Click "✏️ Edit"** from the product details view
3. **Enter updated details** in the same format as adding:
   ```
   Name: New Product Name
   Description: New description
   Category: New category
   Price: 30.00
   Status: active
   ```
4. **Submit** the changes
5. **Review** the updated product details

### Deleting a Product

1. **View product details** for the product you want to delete
2. **Click "🗑️ Delete"** from the product actions
3. **Confirm deletion** in the confirmation dialog
4. **Product is deactivated** (soft delete) and hidden from customers

### Searching Products

1. **Click "🔍 Search Products"** from the menu management dashboard
2. **Enter search term** (minimum 2 characters)
3. **View results** with product details and actions
4. **Click on products** to view full details

### Managing Categories

1. **Click "📂 Product Categories"** from the menu management dashboard
2. **View all categories** with product counts
3. **Click on categories** to see products in that category
4. **Navigate back** to manage other categories

## Technical Implementation

### Database Operations

The system uses the following database operations:

```python
# Product CRUD operations
get_all_products_admin()           # Get all products for admin
create_product(name, desc, cat, price)  # Create new product
update_product(product_id, **kwargs)     # Update product fields
delete_product(product_id)         # Soft delete product
get_product_categories()           # Get unique categories
get_products_by_category(category) # Get products by category
search_products(search_term)       # Search products
```

### Service Layer

The `AdminService` class provides high-level menu management methods:

```python
# Menu management methods
async def get_all_products_for_admin(self) -> List[Dict]
async def create_new_product(self, name, desc, cat, price) -> Dict
async def update_existing_product(self, product_id, **kwargs) -> Dict
async def delete_existing_product(self, product_id) -> Dict
async def get_product_categories_list(self) -> List[str]
async def search_products_admin(self, search_term) -> List[Dict]
async def get_products_by_category_admin(self, category) -> List[Dict]
```

### Handler Layer

The `AdminHandler` class manages the Telegram interface:

```python
# Menu management handlers
async def _show_menu_management_dashboard(self, query: CallbackQuery)
async def _show_all_products(self, query: CallbackQuery)
async def _start_add_product(self, query: CallbackQuery)
async def _handle_add_product_input(self, update, context)
async def _show_product_details(self, query: CallbackQuery, product_id: int)
async def _start_edit_product(self, query: CallbackQuery, product_id: int)
async def _show_delete_product_confirmation(self, query: CallbackQuery, product_id: int)
async def _toggle_product_status(self, query: CallbackQuery, product_id: int)
```

### Conversation States

The system uses conversation handlers for user input:

```python
AWAITING_PRODUCT_DETAILS = 2      # Waiting for new product details
AWAITING_PRODUCT_UPDATE = 3       # Waiting for product update details
AWAITING_SEARCH_TERM = 5          # Waiting for search term
```

## Data Validation

### Product Creation Validation
- **Name**: Minimum 2 characters, unique across all products
- **Description**: Optional, but recommended
- **Category**: Minimum 2 characters
- **Price**: Must be greater than 0, numeric value

### Product Update Validation
- **Name**: Minimum 2 characters if provided
- **Price**: Must be greater than 0 if provided
- **Category**: Minimum 2 characters if provided
- **Status**: Must be 'active' or 'inactive' if provided

### Search Validation
- **Search Term**: Minimum 2 characters
- **Case Insensitive**: Searches both name and description fields

## User Interface

### Keyboard Layouts

#### Menu Management Dashboard
```
🍽️ Menu Management Summary

📋 Total Products: 7
✅ Active Products: 6
❌ Inactive Products: 1
📂 Categories: 4

🛠️ Available Actions:

[📋 View Products] [➕ Add Product]
[📂 Manage Categories] [🔍 Search Products]
[⬅️ Back to Admin Dashboard]
```

#### Product List
```
🍽️ Product Management

Total: 7 product(s)

📝 Kubaneh
📂 bread | 💰 ₪25.00 | ✅ Active

📝 Samneh
📂 spread | 💰 ₪15.00 | ✅ Active

[⬅️ Back to Menu Management]
```

#### Product Details
```
📋 Product Details

📝 Name: Kubaneh
📄 Description: Traditional Yemenite bread
📂 Category: bread
💰 Price: ₪25.00
🔄 Status: ✅ Active
📅 Created: 2024-01-15 10:30

[✏️ Edit] [🗑️ Delete]
[🔄 Toggle Status]
[⬅️ Back to Product List]
```

## Error Handling

### Common Error Scenarios

1. **Product Name Already Exists**
   - Error: "Product with this name already exists"
   - Solution: Use a different name or edit existing product

2. **Invalid Price Format**
   - Error: "Price must be a valid number greater than 0"
   - Solution: Enter a numeric price (e.g., 25.00)

3. **Product Not Found**
   - Error: "Product not found"
   - Solution: Refresh the product list and try again

4. **Invalid Input Format**
   - Error: "Invalid input format. Please follow the instructions"
   - Solution: Use the exact format shown in instructions

### Error Recovery

- **Cancel Operations**: Use the "Cancel" button or `/cancel` command
- **Navigation**: Use back buttons to return to previous screens
- **Retry**: Most operations can be retried after fixing input errors

## Security Considerations

### Admin Access Control
- **Admin Verification**: Only verified admin users can access menu management
- **Telegram ID Check**: Admin status verified through Telegram user ID
- **Session Management**: Proper conversation state management

### Data Integrity
- **Soft Deletes**: Products are deactivated rather than permanently deleted
- **Order History Preservation**: Deleted products don't affect existing orders
- **Validation**: Comprehensive input validation prevents data corruption

### Audit Trail
- **Logging**: All menu management actions are logged
- **Timestamps**: Product creation and update times are tracked
- **User Tracking**: Admin actions are associated with user IDs

## Testing

### Manual Testing
1. **Run the test script**: `python test_menu_management.py`
2. **Test all CRUD operations** through the Telegram interface
3. **Verify data persistence** in the database
4. **Test error scenarios** with invalid inputs

### Automated Testing
```bash
# Run the menu management test
python test_menu_management.py
```

## Future Enhancements

### Planned Features

- **Image Support**: Add product images to the menu
- **Pricing History**: Track price changes over time
- **Inventory Management**: Add stock tracking
- **Menu Templates**: Predefined menu structures
- **Export/Import**: CSV/JSON menu data export/import

### Technical Improvements
- **Caching**: Cache frequently accessed product data
- **Pagination**: Handle large product lists efficiently
- **Real-time Updates**: Live menu updates across all users
- **Backup/Restore**: Automated menu backup functionality

## Support

### Troubleshooting
1. **Check logs** for detailed error information
2. **Verify database connection** and permissions
3. **Test with minimal data** to isolate issues
4. **Review conversation state** for stuck operations

### Common Issues
- **Conversation stuck**: Use `/cancel` to reset
- **Product not appearing**: Check if product is active
- **Search not working**: Ensure minimum 2 characters
- **Permission denied**: Verify admin status

## Conclusion

The Admin Menu Management System provides a comprehensive, user-friendly interface for managing restaurant products through Telegram. With robust validation, error handling, and security measures, it ensures reliable menu management while preserving data integrity and order history. 