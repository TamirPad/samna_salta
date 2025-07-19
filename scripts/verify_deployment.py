#!/usr/bin/env python3
"""
Deployment verification script for Samna Salta Bot
Helps debug deployment issues on Render
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def check_environment():
    """Check environment variables and configuration"""
    print("🔍 Checking environment configuration...")
    
    # Required variables
    required_vars = ['BOT_TOKEN', 'ADMIN_CHAT_ID']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * (len(value) - 4) + value[-4:] if len(value) > 4 else '***'}")
    
    if missing_vars:
        print(f"❌ Missing required variables: {missing_vars}")
        return False
    
    # Optional variables
    optional_vars = [
        'WEBHOOK_MODE', 'PORT', 'RENDER_EXTERNAL_URL', 
        'DATABASE_URL', 'LOG_LEVEL', 'ENVIRONMENT'
    ]
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"ℹ️  {var}: {value}")
        else:
            print(f"⚠️  {var}: Not set (using default)")
    
    return True

def check_dependencies():
    """Check if all required dependencies are available"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'telegram', 'fastapi', 'uvicorn', 'sqlalchemy', 
        'pydantic', 'httpx', 'alembic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: Available")
        except ImportError:
            print(f"❌ {package}: Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {missing_packages}")
        return False
    
    return True

def check_directories():
    """Check if required directories exist"""
    print("\n📁 Checking directories...")
    
    required_dirs = ['data', 'logs']
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✅ {dir_name}: Exists")
        else:
            print(f"⚠️  {dir_name}: Missing (will be created)")
            try:
                dir_path.mkdir(exist_ok=True)
                print(f"✅ {dir_name}: Created")
            except Exception as e:
                print(f"❌ {dir_name}: Failed to create - {e}")
                return False
    
    return True

async def test_bot_connection():
    """Test bot token and connection"""
    print("\n🤖 Testing bot connection...")
    
    try:
        from telegram import Bot
        from telegram.error import InvalidToken, NetworkError
        
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            print("❌ BOT_TOKEN not set")
            return False
        
        bot = Bot(token=bot_token)
        
        # Test getMe
        me = await bot.get_me()
        print(f"✅ Bot connected: @{me.username} ({me.first_name})")
        
        # Test webhook info
        webhook_info = await bot.get_webhook_info()
        print(f"ℹ️  Webhook URL: {webhook_info.url or 'Not set'}")
        print(f"ℹ️  Webhook pending: {webhook_info.pending_update_count}")
        
        return True
        
    except InvalidToken:
        print("❌ Invalid bot token")
        return False
    except NetworkError as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_database():
    """Check database connection"""
    print("\n🗄️  Checking database...")
    
    try:
        from src.db.operations import check_database_connection
        
        if check_database_connection():
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def main():
    """Main verification function"""
    print("🚀 Samna Salta Bot - Deployment Verification")
    print("=" * 50)
    
    # Check environment
    env_ok = check_environment()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check directories
    dirs_ok = check_directories()
    
    # Check database
    db_ok = check_database()
    
    # Test bot connection
    bot_ok = asyncio.run(test_bot_connection())
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Verification Summary:")
    print(f"Environment: {'✅' if env_ok else '❌'}")
    print(f"Dependencies: {'✅' if deps_ok else '❌'}")
    print(f"Directories: {'✅' if dirs_ok else '❌'}")
    print(f"Database: {'✅' if db_ok else '❌'}")
    print(f"Bot Connection: {'✅' if bot_ok else '❌'}")
    
    all_ok = all([env_ok, deps_ok, dirs_ok, db_ok, bot_ok])
    
    if all_ok:
        print("\n🎉 All checks passed! Deployment should work correctly.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 