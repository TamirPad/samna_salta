# 🚀 Deployment Guide for Samna Salta Bot

## Render Deployment (Recommended)

### Prerequisites
1. **Telegram Bot Token**: Get from [@BotFather](https://t.me/botfather)
2. **Admin Chat ID**: Your Telegram user ID for admin notifications
3. **Render Account**: Free account at [render.com](https://render.com)

### Step-by-Step Deployment

#### 1. Fork/Clone Repository
```bash
git clone <your-repo-url>
cd samna_salta
```

#### 2. Create Render Service
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:

**Basic Settings:**
- **Name**: `samna-salta-bot`
- **Environment**: `Python`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your default branch)
- **Root Directory**: Leave empty (if repo is at root)

**Build & Deploy Settings:**
- **Build Command**: `./render-build.sh`
- **Start Command**: `python main.py`

#### 3. Environment Variables
Set these in Render Dashboard → Environment:

**Required:**
```
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_CHAT_ID=your_telegram_user_id_here
WEBHOOK_MODE=true
```

**Optional (with defaults):**
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/samna_salta
LOG_LEVEL=INFO
ENVIRONMENT=production
DELIVERY_CHARGE=5.00
CURRENCY=ILS
HILBEH_AVAILABLE_DAYS=["wednesday", "thursday", "friday"]
HILBEH_AVAILABLE_HOURS=09:00-18:00
PORT=8000
```

#### 4. Deploy
1. Click "Create Web Service"
2. Wait for build to complete (2-3 minutes)
3. Check logs for any errors

### Troubleshooting

#### Common Issues

**1. Build Fails**
- Check Python version compatibility (3.11.7)
- Verify all dependencies in `pyproject.toml`
- Check build logs for specific errors

**2. Bot Not Responding**
- Verify `BOT_TOKEN` is correct
- Check `ADMIN_CHAT_ID` is your Telegram user ID
- Ensure `WEBHOOK_MODE=true` is set

**3. Database Connection Issues**
- For free tier: Use SQLite (default)
- For paid tier: Set up PostgreSQL database
- Check `DATABASE_URL` format

**4. Health Check Fails**
- Verify `/health` endpoint is accessible
- Check application logs for startup errors
- Ensure port 8000 is available

#### Debug Steps

1. **Check Build Logs**
   ```bash
   # In Render Dashboard → Logs
   # Look for build errors or missing dependencies
   ```

2. **Check Runtime Logs**
   ```bash
   # In Render Dashboard → Logs
   # Look for startup errors or missing environment variables
   ```

3. **Test Health Endpoint**
   ```bash
   curl https://your-app-name.onrender.com/health
   ```

4. **Verify Webhook**
   ```bash
   curl https://your-app-name.onrender.com/
   # Should return bot status
   ```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | ✅ | - | Telegram bot token from @BotFather |
| `ADMIN_CHAT_ID` | ✅ | - | Your Telegram user ID for admin access |
| `WEBHOOK_MODE` | ❌ | `false` | Set to `true` for production |
| `DATABASE_URL` | ❌ | SQLite | Database connection string |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ENVIRONMENT` | ❌ | `development` | Environment name |
| `DELIVERY_CHARGE` | ❌ | `5.00` | Delivery fee amount |
| `CURRENCY` | ❌ | `ILS` | Currency code |
| `PORT` | ❌ | `8000` | Server port |

### Security Notes

1. **Never commit sensitive data** to your repository
2. **Use environment variables** for all secrets
3. **Keep dependencies updated** for security patches
4. **Monitor logs** for suspicious activity

### Performance Optimization

1. **Free Tier Limitations**
   - 750 hours/month
   - Sleeps after 15 minutes of inactivity
   - Limited CPU/memory

2. **Upgrade Considerations**
   - Paid plans for 24/7 uptime
   - PostgreSQL database for better performance
   - Custom domains for production use

### Monitoring

1. **Health Checks**
   - Automatic health checks every 30 seconds
   - Manual checks via `/health` endpoint

2. **Logs**
   - Access logs in Render Dashboard
   - Monitor for errors and performance issues

3. **Metrics**
   - Response times
   - Error rates
   - Resource usage

### Support

If you encounter issues:

1. Check this deployment guide
2. Review Render documentation
3. Check application logs
4. Verify environment variables
5. Test locally first

---

**Happy Deploying! 🎉** 