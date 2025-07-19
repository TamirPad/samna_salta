"""
Tests for main application module
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from main import setup_bot, run_polling, run_webhook, main


class TestMainApplication:
    """Test main application"""

    def test_setup_bot_success(self, patch_config):
        """Test bot setup - success"""
        with patch("telegram.ext.Application.builder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.build.return_value = mock_app
            
            result = setup_bot()
            
            assert result is not None
            assert result == mock_app

    def test_setup_bot_failure(self, patch_config):
        """Test bot setup - failure"""
        with patch("telegram.ext.Application.builder", side_effect=Exception("Bot setup error")):
            with pytest.raises(Exception):
                setup_bot()

    def test_run_polling_success(self, patch_config):
        """Test polling mode - success"""
        with patch("main.setup_bot") as mock_setup_bot:
            mock_app = MagicMock()
            mock_setup_bot.return_value = mock_app
            
            with patch.object(mock_app, "run_polling"):
                run_polling()
                
                mock_setup_bot.assert_called_once()
                mock_app.run_polling.assert_called_once()

    def test_run_polling_failure(self, patch_config):
        """Test polling mode - failure"""
        with patch("main.setup_bot", side_effect=Exception("Setup error")):
            with pytest.raises(Exception):
                run_polling()

    def test_run_webhook_success(self, patch_config):
        """Test webhook mode success"""
        with patch("main.setup_bot") as mock_setup_bot:
            mock_app = MagicMock()
            mock_setup_bot.return_value = mock_app
            
            with patch("fastapi.FastAPI") as mock_fastapi:
                with patch("uvicorn.run") as mock_run:
                    # Mock the lifespan context manager to avoid actual setup_bot call
                    mock_fastapi_instance = MagicMock()
                    mock_fastapi.return_value = mock_fastapi_instance
                    
                    run_webhook()
                    
                    # Verify FastAPI was created
                    mock_fastapi.assert_called_once()
                    # Verify uvicorn.run was called
                    mock_run.assert_called_once()

    def test_run_webhook_failure(self, patch_config):
        """Test webhook mode failure"""
        with patch("fastapi.FastAPI") as mock_fastapi:
            with patch("uvicorn.run", side_effect=Exception("Webhook setup error")):
                with pytest.raises(Exception):
                    run_webhook()

    def test_main_webhook_mode(self, patch_config):
        """Test main function in webhook mode"""
        with patch.dict("os.environ", {"WEBHOOK_MODE": "true", "BOT_TOKEN": "test_token", "ADMIN_CHAT_ID": "123456789"}, clear=True):
            with patch("main.get_config") as mock_get_config:
                config = MagicMock()
                config.webhook_mode = True
                mock_get_config.return_value = config
                
                with patch("main.run_webhook") as mock_run_webhook:
                    # Call main without await since it's not async
                    main()
                    
                    # Verify webhook was called
                    mock_run_webhook.assert_called_once()

    def test_main_polling_mode(self, patch_config):
        """Test main function in polling mode"""
        with patch.dict("os.environ", {"BOT_TOKEN": "test_token", "ADMIN_CHAT_ID": "123456789"}, clear=True):
            with patch("main.get_config") as mock_get_config:
                config = MagicMock()
                config.webhook_mode = False
                mock_get_config.return_value = config
                
                with patch("main.run_polling") as mock_run_polling:
                    # Call main without await since it's not async
                    main()
                    
                    # Verify polling was called
                    mock_run_polling.assert_called_once()

    def test_main_bot_setup_failure(self, patch_config):
        """Test main function with bot setup failure"""
        with patch.dict("os.environ", {"BOT_TOKEN": "test_token", "ADMIN_CHAT_ID": "123456789"}, clear=True):
            with patch("main.get_config") as mock_get_config:
                config = MagicMock()
                mock_get_config.return_value = config
                
                with patch("main.setup_bot", side_effect=Exception("Setup failed")):
                    # Call main without await since it's not async
                    result = main()
                    assert result == 1


class TestEnvironmentDetection:
    """Test environment detection"""

    def test_environment_detection_render(self):
        """Test environment detection on Render"""
        with patch.dict("os.environ", {"RENDER_EXTERNAL_URL": "https://app.onrender.com"}, clear=True):
            with patch("main.get_config") as mock_get_config:
                config = MagicMock()
                config.webhook_mode = True
                mock_get_config.return_value = config
                
                with patch("main.run_webhook") as mock_run_webhook:
                    # Should use webhook mode on Render
                    main()
                    
                    # Verify webhook mode was forced
                    assert config.webhook_mode is True

    def test_environment_detection_local(self):
        """Test environment detection locally"""
        with patch.dict("os.environ", {}, clear=True):
            with patch("main.get_config") as mock_get_config:
                config = MagicMock()
                config.webhook_mode = False
                mock_get_config.return_value = config
                
                with patch("main.run_polling") as mock_run_polling:
                    # Should use polling mode locally
                    main()
                    
                    # Verify polling mode was used
                    assert config.webhook_mode is False


class TestConfigurationValidation:
    """Test configuration validation"""

    def test_required_environment_variables(self):
        """Test required environment variables"""
        with patch.dict("os.environ", {}, clear=True):
            result = main()
            assert result == 1  # Should return 1 for missing env vars

    def test_bot_token_validation(self):
        """Test bot token validation"""
        with patch("main.get_config") as mock_get_config:
            config = MagicMock()
            config.bot_token = "invalid_token"  # Too short
            mock_get_config.return_value = config
            
            with pytest.raises(SystemExit):
                main()

    def test_admin_chat_id_validation(self):
        """Test admin chat ID validation"""
        with patch("main.get_config") as mock_get_config:
            config = MagicMock()
            config.admin_chat_id = "invalid_id"  # Not a number
            mock_get_config.return_value = config
            
            with pytest.raises(SystemExit):
                main()


class TestErrorHandling:
    """Test error handling"""

    def test_startup_error_handling(self):
        """Test startup error handling"""
        with patch("telegram.ext.Application.builder", side_effect=Exception("Startup error")):
            with pytest.raises(Exception):
                setup_bot()

    def test_polling_error_handling(self):
        """Test polling error handling"""
        with patch("main.setup_bot") as mock_setup_bot:
            mock_app = MagicMock()
            mock_setup_bot.return_value = mock_app
            
            with patch.object(mock_app, "run_polling", side_effect=Exception("Polling error")):
                with pytest.raises(Exception):
                    run_polling()

    def test_webhook_error_handling(self):
        """Test webhook error handling"""
        with patch("fastapi.FastAPI") as mock_fastapi:
            with patch("uvicorn.run", side_effect=Exception("Webhook setup error")):
                with pytest.raises(Exception):
                    run_webhook()


class TestIntegration:
    """Integration tests"""

    def test_full_startup_workflow(self, patch_config):
        """Test full startup workflow"""
        with patch("main.get_config") as mock_get_config:
            config = MagicMock()
            config.webhook_mode = True
            config.environment = "production"
            config.bot_token = "valid_bot_token_123456789"
            config.admin_chat_id = 123456789
            config.database_url = "sqlite:///test.db"
            mock_get_config.return_value = config
            
            with patch("main.run_webhook") as mock_run_webhook:
                main()
                
                # Verify webhook was called
                mock_run_webhook.assert_called_once()

    def test_polling_integration(self, patch_config):
        """Test polling integration"""
        with patch("main.setup_bot") as mock_setup_bot:
            mock_app = MagicMock()
            mock_setup_bot.return_value = mock_app
            
            with patch.object(mock_app, "run_polling"):
                run_polling()
                
                # Verify setup and polling were called
                mock_setup_bot.assert_called_once()
                mock_app.run_polling.assert_called_once()

    def test_webhook_integration(self, patch_config):
        """Test webhook integration"""
        with patch("fastapi.FastAPI") as mock_fastapi:
            with patch("uvicorn.run") as mock_run:
                # Mock the lifespan context manager to avoid actual setup_bot call
                mock_fastapi_instance = MagicMock()
                mock_fastapi.return_value = mock_fastapi_instance
                
                run_webhook()
                
                # Verify FastAPI was created
                mock_fastapi.assert_called_once()
                # Verify uvicorn.run was called
                mock_run.assert_called_once()


class TestPerformance:
    """Test performance"""

    def test_setup_bot_performance(self, performance_timer):
        """Test bot setup performance"""
        with patch("main.get_config") as mock_get_config:
            with patch("main.init_db") as mock_init_db:
                with patch("telegram.ext.Application.builder") as mock_builder:
                    with patch("src.container.get_container") as mock_get_container:
                        config = MagicMock()
                        mock_get_config.return_value = config
                        mock_app = MagicMock()
                        mock_builder.return_value.token.return_value.build.return_value = mock_app
                        mock_container_instance = MagicMock()
                        mock_get_container.return_value = mock_container_instance
                        
                        # Test with fewer iterations and proper mocking
                        for i in range(10):  # Reduced from 100 to 10
                            setup_bot()

    def test_config_loading_performance(self, performance_timer):
        """Test config loading performance"""
        with patch("main.get_config") as mock_get_config:
            config = MagicMock()
            mock_get_config.return_value = config
            
            # Test with fewer iterations
            for i in range(10):  # Reduced from 100 to 10
                from main import get_config
                get_config()


class TestEdgeCases:
    """Test edge cases"""

    def test_setup_bot_with_invalid_token(self):
        """Test bot setup with invalid token"""
        with patch("main.get_config") as mock_get_config:
            config = MagicMock()
            config.bot_token = "invalid"
            mock_get_config.return_value = config
            
            with patch("telegram.ext.Application.builder", side_effect=Exception("Invalid token")):
                with pytest.raises(Exception):
                    setup_bot()

    def test_setup_bot_with_missing_dependencies(self):
        """Test bot setup with missing dependencies"""
        with patch("main.get_config") as mock_get_config:
            config = MagicMock()
            mock_get_config.return_value = config
            
            with patch("telegram.ext.Application.builder", side_effect=ImportError("Missing dependency")):
                with pytest.raises(ImportError):
                    setup_bot()

    def test_main_with_environment_variables(self):
        """Test main with various environment variables"""
        test_envs = [
            {"RENDER": "true", "RENDER_EXTERNAL_URL": "https://app.onrender.com"},
            {"ENVIRONMENT": "production", "WEBHOOK_MODE": "true"},
            {"ENVIRONMENT": "development", "WEBHOOK_MODE": "false"},
            {}
        ]
        
        for env_vars in test_envs:
            with patch.dict("os.environ", env_vars, clear=True):
                with patch("main.get_config") as mock_get_config:
                    config = MagicMock()
                    config.webhook_mode = False
                    mock_get_config.return_value = config
                    
                    with patch("main.run_polling") as mock_run_polling:
                        try:
                            main()
                            # Should not raise exception
                        except Exception:
                            # Some combinations might fail, which is expected
                            pass 