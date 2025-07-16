#!/usr/bin/env python3
"""
Database connection diagnostic script
Helps troubleshoot database connectivity issues
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config import get_config
from src.db.operations import check_database_connection, get_database_status

def main():
    """Run database diagnostics"""
    print("🔍 Database Connection Diagnostics")
    print("=" * 50)
    
    # Get configuration
    try:
        config = get_config()
        print(f"✅ Configuration loaded successfully")
        print(f"   Environment: {config.environment}")
        print(f"   Database URL: {'Set' if config.database_url else 'Not set'}")
        print(f"   Supabase Connection: {'Set' if config.supabase_connection_string else 'Not set'}")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return
    
    # Check which database is being used
    if config.supabase_connection_string:
        print(f"\n📊 Using Supabase PostgreSQL")
        print(f"   Connection string: {config.supabase_connection_string[:50]}...")
    else:
        print(f"\n📊 Using local database")
        print(f"   Database URL: {config.database_url}")
    
    # Test connection
    print(f"\n🔌 Testing database connection...")
    for attempt in range(3):
        print(f"   Attempt {attempt + 1}/3...")
        
        if check_database_connection():
            print(f"   ✅ Database connection successful!")
            break
        else:
            print(f"   ❌ Database connection failed")
            if attempt < 2:
                print(f"   ⏳ Waiting 2 seconds before retry...")
                time.sleep(2)
    else:
        print(f"   ❌ All connection attempts failed")
    
    # Get detailed status
    print(f"\n📋 Database Status Report")
    print("-" * 30)
    status = get_database_status()
    
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Environment information
    print(f"\n🌍 Environment Information")
    print("-" * 30)
    print(f"   Python version: {sys.version}")
    print(f"   Platform: {sys.platform}")
    print(f"   Working directory: {os.getcwd()}")
    
    # Check environment variables
    print(f"\n🔧 Environment Variables")
    print("-" * 30)
    db_vars = [
        "SUPABASE_CONNECTION_STRING",
        "DATABASE_URL", 
        "SUPABASE_URL",
        "SUPABASE_KEY"
    ]
    
    for var in db_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "key" in var.lower() or "password" in var.lower():
                masked_value = value[:10] + "..." if len(value) > 10 else "***"
                print(f"   {var}: {masked_value}")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: Not set")
    
    print(f"\n💡 Troubleshooting Tips")
    print("-" * 30)
    if not status["connected"]:
        print("   • Check if Supabase database is running")
        print("   • Verify connection string is correct")
        print("   • Check network connectivity")
        print("   • Ensure database credentials are valid")
        print("   • Check if database is accessible from deployment environment")
    else:
        print("   • Database connection is working correctly")
        print("   • If you're still having issues, check application logs")

if __name__ == "__main__":
    main() 