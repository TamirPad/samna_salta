#!/usr/bin/env python3
"""
Script to set up webhook for Telegram bot
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from src.config import get_config
from telegram.ext import Application

# Load environment variables from .env file
load_dotenv()

async def setup_webhook():
    """Set up webhook for the bot"""
    try:
        # Load config
        config = get_config()
        
        # Get webhook URL from environment
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            print("❌ WEBHOOK_URL environment variable not set")
            print("Please set WEBHOOK_URL to your Render app URL (e.g., https://your-app.onrender.com)")
            return False
        
        # Create application
        application = Application.builder().token(config.bot_token).build()
        
        # Set webhook
        webhook_path = f"{webhook_url}/webhook"
        print(f"Setting webhook to: {webhook_path}")
        
        success = await application.bot.set_webhook(url=webhook_path)
        
        if success:
            print("✅ Webhook set successfully!")
            
            # Get webhook info
            webhook_info = await application.bot.get_webhook_info()
            print(f"Webhook URL: {webhook_info.url}")
            print(f"Pending updates: {webhook_info.pending_update_count}")
            
            return True
        else:
            print("❌ Failed to set webhook")
            return False
            
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return False

async def remove_webhook():
    """Remove webhook and switch to polling"""
    try:
        # Load config
        config = get_config()
        
        # Create application
        application = Application.builder().token(config.bot_token).build()
        
        # Remove webhook
        success = await application.bot.delete_webhook()
        
        if success:
            print("✅ Webhook removed successfully!")
            return True
        else:
            print("❌ Failed to remove webhook")
            return False
            
    except Exception as e:
        print(f"❌ Error removing webhook: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/setup_webhook.py set    # Set webhook")
        print("  python scripts/setup_webhook.py remove # Remove webhook")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "set":
        success = asyncio.run(setup_webhook())
    elif command == "remove":
        success = asyncio.run(remove_webhook())
    else:
        print(f"Unknown command: {command}")
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 