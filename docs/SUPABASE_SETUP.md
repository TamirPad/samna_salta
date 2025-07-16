# 🚀 Supabase PostgreSQL Setup Guide

Quick setup guide for using Supabase PostgreSQL with your Samna Salta bot.

## 📋 Prerequisites

1. **Supabase Account**: Create a free account at [supabase.com](https://supabase.com)
2. **PostgreSQL Database**: Set up a new PostgreSQL database in Supabase
3. **Connection String**: Get your database connection string from Supabase dashboard

## 🔧 Quick Setup

### 1. Get Your Supabase Connection String

1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **Database**
3. Copy the **Connection string** (URI format)
4. It should look like: `postgresql://postgres:[password]@[host]:[port]/postgres`

### 2. Update Environment Variables

Add your Supabase connection string to your `.env` file:

```bash
# For Supabase PostgreSQL (production)
SUPABASE_CONNECTION_STRING=postgresql://postgres:your_password@your_host:5432/postgres
```

### 3. Setup Supabase Database

Run the setup script to create tables and initialize default products:

```bash
# Setup fresh Supabase database
python scripts/setup_supabase.py

# Verify setup
python scripts/setup_supabase.py --verify
```

### 4. Test Connection

Test your Supabase connection:

```bash
python scripts/test_supabase_connection.py
```

### 5. Start Bot

Your bot will automatically use Supabase PostgreSQL:

```bash
python main.py
```

## 🔍 What the Setup Does

The setup script will:

- ✅ **Create Tables**: All necessary database tables (customers, products, carts, orders, order_items)
- ✅ **Initialize Products**: Add default Yemenite food products to the catalog
- ✅ **Test Connection**: Verify database connectivity
- ✅ **Ready to Use**: Bot is immediately ready for customers

## 🚨 Troubleshooting

### Common Issues

1. **Connection Failed**:
   ```
   Error: connection failed
   ```
   - Check your connection string format
   - Verify database credentials
   - Ensure database is accessible from your IP

2. **SSL Connection Required**:
   ```
   Error: SSL connection required
   ```
   - Add `?sslmode=require` to your connection string
   - Example: `postgresql://user:pass@host:5432/db?sslmode=require`

3. **Permission Denied**:
   ```
   Error: permission denied for table
   ```
   - Check database user permissions
   - Ensure user has CREATE, INSERT, SELECT privileges

### Debug Mode

Enable debug logging to see detailed setup progress:

```bash
export LOG_LEVEL=DEBUG
python scripts/setup_supabase.py
```

## 🔄 Switching Between Databases

### Use Supabase (Production)
```bash
# Set in .env
SUPABASE_CONNECTION_STRING=your_connection_string
python main.py
```

### Use SQLite (Development)
```bash
# Comment out Supabase in .env
# SUPABASE_CONNECTION_STRING=...

# Uncomment SQLite
DATABASE_URL=sqlite:///data/samna_salta.db
python main.py
```

## 📈 Benefits of Supabase PostgreSQL

- **Better Performance**: Faster queries and better concurrency
- **Scalability**: Easy to scale as your business grows
- **Reliability**: Automatic backups and high availability
- **Real-time Features**: Built-in real-time subscriptions (future use)
- **Security**: Enterprise-grade security and compliance

## 🔐 Security Best Practices

- **Connection String**: Keep your connection string secure
- **Environment Variables**: Never commit `.env` files to version control
- **Database Permissions**: Use least-privilege access
- **SSL**: Always use SSL connections in production

## 📞 Support

If you encounter issues:

1. Check the [Supabase documentation](https://supabase.com/docs)
2. Review the setup logs for specific errors
3. Verify your connection string format
4. Test database connectivity manually

---

**Setup Status**: ✅ **Ready for Production**

Your bot is now ready to use Supabase PostgreSQL for improved performance and scalability! 