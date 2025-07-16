# 🗄️ Database Troubleshooting Guide

This guide helps resolve database connection issues with the Samna Salta bot.

## 🚨 Common Error: "Network is unreachable"

### Error Message
```
connection to server at "db.kwrwxtccbnvadqedaqdd.supabase.co" (2a05:d014:1c06:5f0f:4451:fa2e:285:6dc2), port 5432 failed: Network is unreachable
```

### Root Causes
1. **IPv6 Connection Issues**: The error shows an IPv6 address, which may not be supported
2. **Network Configuration**: Deployment environment cannot reach Supabase
3. **Firewall Blocking**: Port 5432 is blocked
4. **Supabase Service Down**: Database server is temporarily unavailable

## 🔧 Immediate Solutions

### 1. **Force IPv4 Connection**

Add this environment variable to force IPv4:
```bash
export PGHOSTADDR=your_supabase_ipv4_address
```

Or modify the connection string to use IPv4:
```
postgresql://user:password@ipv4_address:5432/database
```

### 2. **Check Supabase Status**

1. Visit [Supabase Status Page](https://status.supabase.com/)
2. Check if your region is experiencing issues
3. Verify your project is active and not paused

### 3. **Verify Connection String**

Ensure your `SUPABASE_CONNECTION_STRING` is correct:
```
postgresql://postgres:[YOUR-PASSWORD]@db.kwrwxtccbnvadqedaqdd.supabase.co:5432/postgres
```

### 4. **Test Connection Locally**

Run the diagnostic script:
```bash
python scripts/diagnose_db.py
```

Or test basic connectivity:
```bash
python scripts/test_connection.py
```

## 🛠️ Deployment-Specific Solutions

### Render.com Deployment

1. **Check Environment Variables**:
   - Go to your Render dashboard
   - Navigate to your service
   - Check "Environment" tab
   - Verify `SUPABASE_CONNECTION_STRING` is set correctly

2. **Network Configuration**:
   - Render services may have network restrictions
   - Contact Render support if database connectivity is blocked

3. **Use Health Check Endpoint**:
   ```
   GET https://your-app.onrender.com/health
   ```
   This will show database status.

### Railway Deployment

1. **Environment Variables**:
   - Check Railway dashboard
   - Verify all database-related variables are set

2. **Network Access**:
   - Railway may require specific network configuration
   - Check if outbound connections to port 5432 are allowed

### Heroku Deployment

1. **Add PostgreSQL Add-on** (if using Heroku Postgres):
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

2. **Check Config Vars**:
   ```bash
   heroku config
   ```

## 🔍 Diagnostic Steps

### Step 1: Run Connection Test
```bash
python scripts/test_connection.py
```

### Step 2: Check Environment Variables
```bash
echo $SUPABASE_CONNECTION_STRING
echo $DATABASE_URL
```

### Step 3: Test Network Connectivity
```bash
# Test if you can reach the database host
ping db.kwrwxtccbnvadqedaqdd.supabase.co

# Test port connectivity
telnet db.kwrwxtccbnvadqedaqdd.supabase.co 5432
```

### Step 4: Check Application Logs
Look for these log messages:
- `Database initialization attempt 1/3`
- `Database connection test successful`
- `Database tables created successfully`

## 🚀 Fallback Solutions

### 1. **Use Local SQLite (Development)**
If Supabase is unavailable, the bot can fall back to SQLite:

```bash
# Set environment variable to use local database
export DATABASE_URL=sqlite:///data/samna_salta.db
unset SUPABASE_CONNECTION_STRING
```

### 2. **Graceful Degradation**
The bot now continues to start even if database initialization fails:
- Basic bot functionality will work
- Database-dependent features (orders, analytics) will be limited
- Health check endpoint will show "degraded" status

### 3. **Retry Logic**
The bot includes automatic retry logic:
- 3 attempts with exponential backoff
- 5, 10, 20 second delays between attempts
- Continues startup even if all attempts fail

## 📊 Monitoring and Health Checks

### Health Check Endpoint
```
GET /health
```

**Response when database is connected:**
```json
{
  "status": "ok",
  "message": "Bot is running",
  "database": "connected",
  "database_type": "postgresql"
}
```

**Response when database is disconnected:**
```json
{
  "status": "degraded",
  "message": "Bot is running but database is unavailable",
  "database": "disconnected",
  "database_error": "connection to server failed"
}
```

### Log Monitoring
Watch for these log patterns:
- `Database initialization attempt X/3`
- `Database connection test successful`
- `All database initialization attempts failed`
- `Continuing without database initialization`

## 🔧 Advanced Troubleshooting

### 1. **Check Supabase Dashboard**
1. Log into [Supabase Dashboard](https://app.supabase.com/)
2. Navigate to your project
3. Check "Database" tab for connection info
4. Verify the connection string matches your environment

### 2. **Test with Different Client**
```bash
# Install psql if available
psql "postgresql://postgres:password@db.kwrwxtccbnvadqedaqdd.supabase.co:5432/postgres"
```

### 3. **Check Firewall Rules**
Ensure your deployment environment allows outbound connections to:
- `db.kwrwxtccbnvadqedaqdd.supabase.co:5432`
- Protocol: TCP

### 4. **DNS Resolution**
```bash
# Check if hostname resolves
nslookup db.kwrwxtccbnvadqedaqdd.supabase.co

# Try different DNS servers
nslookup db.kwrwxtccbnvadqedaqdd.supabase.co 8.8.8.8
```

## 🆘 Getting Help

### 1. **Check Supabase Status**
- [Supabase Status Page](https://status.supabase.com/)
- [Supabase Community](https://github.com/supabase/supabase/discussions)

### 2. **Contact Support**
- **Supabase**: [Support Portal](https://supabase.com/support)
- **Render**: [Support Documentation](https://render.com/docs/help)
- **Railway**: [Support](https://railway.app/help)

### 3. **Debug Information**
When reporting issues, include:
- Full error message
- Environment (Render/Railway/Heroku)
- Output from `scripts/diagnose_db.py`
- Application logs
- Health check endpoint response

## 📝 Prevention

### 1. **Regular Monitoring**
- Set up alerts for database connectivity
- Monitor health check endpoint
- Watch application logs for database errors

### 2. **Backup Strategy**
- Consider using multiple database providers
- Implement local SQLite fallback
- Regular database backups

### 3. **Connection Pooling**
The application includes connection pooling:
- Automatic retry logic
- Connection health checks
- Graceful error handling

---

**Last Updated**: July 2025
**Version**: 1.0 