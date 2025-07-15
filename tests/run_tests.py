#!/usr/bin/env python3
"""
Simple test runner for the Samna Salta bot.
Runs both quick and comprehensive tests automatically (no user input).
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def run_comprehensive_tests():
    """Run comprehensive tests"""
    print("🤖 Running comprehensive bot tests...")
    
    try:
        from tests.test_bot_comprehensive import ComprehensiveBotTester
        
        tester = ComprehensiveBotTester()
        success = await tester.run_all_tests()
        
        if success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Bot is fully functional and ready for production!")
            return True
        else:
            print("\n❌ SOME TESTS FAILED!")
            print("📋 Check test_report.json for detailed results")
            return False
            
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        return False

async def run_quick_tests():
    """Run quick tests for basic functionality"""
    print("⚡ Running quick functionality tests...")
    
    try:
        # Test imports
        from src.config import get_config
        from src.container import Container
        from src.db.operations import init_db
        
        # Test configuration
        config = get_config()
        assert config.bot_token, "Bot token not configured"
        
        # Test container
        container = Container()
        cart_service = container.get_cart_service()
        assert cart_service is not None, "Cart service not initialized"
        
        # Test database
        init_db()
        
        print("✅ Quick tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Quick tests failed: {e}")
        return False

async def main():
    """Main test runner"""
    print("="*60)
    print("🤖 SAMNA SALTA BOT - TESTING SUITE")
    print("="*60)
    
    print("\nRunning quick tests...")
    quick_success = await run_quick_tests()
    
    print("\n" + "="*40)
    print("Running comprehensive tests...")
    comprehensive_success = await run_comprehensive_tests()
    
    success = quick_success and comprehensive_success
    
    print("\n" + "="*60)
    if success:
        print("🎉 ALL TESTS PASSED! Bot is ready to use!")
        sys.exit(0)
    else:
        print("❌ TESTS FAILED! Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 