# Deploying Samna Salta Bot to Render

This guide will help you deploy your Telegram bot to Render's cloud platform.

## Prerequisites

1. A GitHub/GitLab/Bitbucket repository with your bot code
2. A Telegram bot token from [@BotFather](https://t.me/botfather)
3. Your admin chat ID (you can get this by messaging your bot and checking the logs)

## Deployment Steps

### 1. Prepare Your Repository

The following files have been created for Render deployment:

- `render.yaml` - Infrastructure as code configuration
- `runtime.txt` - Python version specification
- `Procfile` - Process definition
- `render-build.sh` - Build script

### 2. Deploy to Render

#### Option A: Using render.yaml (Recommended)

1. Push your code to your Git repository
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click "New +" and select "Blueprint"
4. Connect your repository
5. Render will automatically detect the `render.yaml` file
6. Set the following environment variables in the Render dashboard:
   - `BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_CHAT_ID`: Your admin chat ID

#### Option B: Manual Service Creation

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" and select "Web Service"
3. Connect your repository
4. Configure the service:
   - **Name**: `samna-salta-bot`
   - **Environment**: `Python`
   - **Build Command**: `./render-build.sh`
   - **Start Command**: `python main.py`
   - **Plan**: Free (or choose a paid plan for production)

5. Add environment variables:
   - `BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_CHAT_ID`: Your admin chat ID
   - `DATABASE_URL`: `sqlite:///data/samna_salta.db`
   - `LOG_LEVEL`: `INFO`
   - `ENVIRONMENT`: `production`
   - `DELIVERY_CHARGE`: `5.00`
   - `CURRENCY`: `ILS`
   - `HILBEH_AVAILABLE_DAYS`: `wednesday,thursday,friday`
   - `HILBEH_AVAILABLE_HOURS`: `09:00-18:00`

### 3. Environment Variables

The following environment variables need to be set in Render:

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Your Telegram bot token from @BotFather | Yes |
| `ADMIN_CHAT_ID` | Your admin chat ID for notifications | Yes |
| `DATABASE_URL` | Database connection string | No (defaults to SQLite) |
| `LOG_LEVEL` | Logging level (INFO, DEBUG, etc.) | No |
| `ENVIRONMENT` | Environment (production, development) | No |
| `DELIVERY_CHARGE` | Delivery charge amount | No |
| `CURRENCY` | Currency code | No |
| `HILBEH_AVAILABLE_DAYS` | Days when Hilbeh is available | No |
| `HILBEH_AVAILABLE_HOURS` | Hours when Hilbeh is available | No |

### 4. Database Considerations

The bot currently uses SQLite for simplicity. For production, consider:

1. **SQLite (Current)**: Works for small to medium scale
2. **PostgreSQL**: Better for production with multiple users
   - Create a PostgreSQL database in Render
   - Update `DATABASE_URL` to use PostgreSQL connection string
   - Uncomment `psycopg2-binary==2.9.9` in `requirements.txt`

### 5. Monitoring and Logs

- View logs in the Render dashboard under your service
- Set up health checks if needed
- Monitor the bot's performance and error rates

### 6. Custom Domain (Optional)

1. Go to your service settings in Render
2. Add a custom domain
3. Configure DNS records as instructed

### 7. Scaling (For Production)

For production use, consider:
- Upgrading to a paid plan for better performance
- Using PostgreSQL instead of SQLite
- Setting up proper monitoring and alerting
- Implementing rate limiting and security measures

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check if `BOT_TOKEN` is correct
2. **Database errors**: Ensure the `data` directory is writable
3. **Import errors**: Verify all dependencies are in `requirements.txt`
4. **Environment variables**: Make sure all required variables are set

### Logs

Check the logs in Render dashboard for detailed error information.

## Security Notes

- Never commit your `BOT_TOKEN` to version control
- Use environment variables for all sensitive data
- Consider implementing rate limiting for production use
- Regularly update dependencies for security patches

## Support

If you encounter issues:
1. Check the Render documentation
2. Review the bot logs in Render dashboard
3. Verify all environment variables are set correctly
4. Test the bot locally before deploying 