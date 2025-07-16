# Deployment Guide for Render

This guide will help you deploy your Samna Salta bot to Render's free tier using webhooks.

## Prerequisites

1. A GitHub account with your bot code
2. A Render account (free tier)
3. A Telegram bot token from @BotFather
4. Your Telegram chat ID for admin notifications

## Step 1: Prepare Your Repository

Ensure your repository has the following files:
- `src/main.py` - FastAPI web service
- `Procfile` - Render process definition
- `render.yaml` - Render configuration
- `pyproject.toml` - Python dependencies
- `render-build.sh` - Build script

## Step 2: Deploy to Render

1. **Create a new Web Service on Render**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure the service**
   - **Name**: `samna-salta-bot` (or your preferred name)
   - **Environment**: `Python`
   - **Build Command**: `./render-build.sh`
   - **Start Command**: `.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port $PORT`

3. **Set Environment Variables**
   - `BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_CHAT_ID`: Your Telegram chat ID
   - `WEBHOOK_URL`: Your Render app URL (e.g., `https://your-app.onrender.com`)
   - `ENVIRONMENT`: `production`
   - `DATABASE_URL`: `sqlite:///data/samna_salta.db`
   - `LOG_LEVEL`: `INFO`
   - `DELIVERY_CHARGE`: `5.00`
   - `CURRENCY`: `ILS`

4. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your bot

## Step 3: Set Up Webhook

After successful deployment:

1. **Get your app URL**
   - Your app URL will be something like: `https://your-app-name.onrender.com`

2. **Set the webhook**
   ```bash
   # Clone your repository locally
   git clone <your-repo-url>
   cd samna_salta
   
   # Set environment variables
   export BOT_TOKEN=your_bot_token
   export WEBHOOK_URL=https://your-app-name.onrender.com
   
   # Set up the webhook
   python scripts/setup_webhook.py set
   ```

3. **Verify webhook is working**
   - Send `/start` to your bot
   - Check if it responds
   - Check Render logs for any errors

## Step 4: Test Your Bot

1. **Send a test message**
   - Open Telegram and find your bot
   - Send `/start`
   - The bot should respond with the welcome message

2. **Check logs**
   - Go to your Render dashboard
   - Click on your service
   - Check the "Logs" tab for any errors

## Troubleshooting

### Common Issues

1. **"terminated by other getUpdates request" error**
   - This happens when multiple bot instances are running
   - Solution: Use webhook mode (which this setup does)

2. **Bot not responding**
   - Check if the webhook is set correctly
   - Run: `python scripts/setup_webhook.py set`
   - Check Render logs for errors

3. **Build failures**
   - Ensure all dependencies are in `pyproject.toml`
   - Check that `render-build.sh` is executable
   - Verify Python version compatibility

4. **Webhook not receiving updates**
   - Check if your app URL is accessible
   - Verify the webhook URL is correct
   - Check Render logs for webhook endpoint errors

### Useful Commands

```bash
# Check webhook status
python scripts/setup_webhook.py set

# Remove webhook (switch to polling)
python scripts/setup_webhook.py remove

# Check bot status
python scripts/check_bot_status.py
```

### Monitoring

- **Health Check**: Visit `https://your-app.onrender.com/health`
- **Root Endpoint**: Visit `https://your-app.onrender.com/`
- **Logs**: Check Render dashboard → Logs tab

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOT_TOKEN` | Yes | Telegram bot token | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `ADMIN_CHAT_ID` | Yes | Your Telegram chat ID | `123456789` |
| `WEBHOOK_URL` | Yes | Your Render app URL | `https://your-app.onrender.com` |
| `ENVIRONMENT` | No | Environment name | `production` |
| `DATABASE_URL` | No | Database connection | `sqlite:///data/samna_salta.db` |
| `LOG_LEVEL` | No | Logging level | `INFO` |
| `DELIVERY_CHARGE` | No | Delivery fee | `5.00` |
| `CURRENCY` | No | Currency code | `ILS` |

## Security Notes

- Never commit your bot token to version control
- Use environment variables for sensitive data
- Keep your bot token private
- Regularly rotate your bot token if needed

## Scaling Considerations

- Render free tier has limitations on requests per month
- Consider upgrading to paid tier for production use
- Monitor usage in Render dashboard
- Set up alerts for high usage

## Support

If you encounter issues:
1. Check Render logs first
2. Verify all environment variables are set
3. Test webhook setup with the provided scripts
4. Check Telegram Bot API status
5. Review this documentation 