# MCP Server Setup Guide

This guide covers configuring the MCP servers used by the Personal AI Employee system.

## Overview

| Server | Agent | Purpose | Auth Required |
|--------|-------|---------|---------------|
| filesystem | All | Read/write vault files | No |
| context7 | Dev agents | Fetch latest documentation | No |
| email-mcp | Communication Agent | Gmail send/draft/search | OAuth 2.0 |
| browser-mcp | Social Media, Finance | Navigate/fill/click | No |
| calendar-mcp | Communication Agent | Google Calendar CRUD | OAuth 2.0 |
| slack-mcp | Communication Agent | Slack messaging | Bot Token |
| odoo-mcp | Finance Agent | Odoo JSON-RPC accounting | API Key |

## 1. Filesystem (Built-in)

No setup required. Automatically scoped to the project directory.

## 2. Context7

No setup required. Uses `@upstash/context7-mcp` via npx.

Usage: Agents call `resolve_library_id` then `get_library_docs` to fetch latest API documentation.

## 3. Gmail (email-mcp)

### Prerequisites
- Google Cloud project with Gmail API enabled
- OAuth 2.0 credentials (Desktop application type)

### Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download credentials JSON
6. Run the OAuth flow to get refresh token
7. Set environment variables in `.env`:
   ```
   GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GMAIL_CLIENT_SECRET=your-client-secret
   GMAIL_REFRESH_TOKEN=your-refresh-token
   ```

### Scopes Required
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/gmail.compose`

## 4. Browser (browser-mcp)

### Prerequisites
- Playwright browsers installed

### Setup
```bash
npx playwright install chromium
```

No environment variables required. Browser runs headless by default.

## 5. Google Calendar (calendar-mcp)

### Prerequisites
- Same Google Cloud project as Gmail
- Google Calendar API enabled

### Setup
1. Enable Google Calendar API in your Google Cloud project
2. Use the same OAuth credentials as Gmail (add calendar scopes)
3. Set environment variables in `.env`:
   ```
   GOOGLE_CALENDAR_CLIENT_ID=your-client-id
   GOOGLE_CALENDAR_CLIENT_SECRET=your-client-secret
   GOOGLE_CALENDAR_REFRESH_TOKEN=your-refresh-token
   ```

### Scopes Required
- `https://www.googleapis.com/auth/calendar`
- `https://www.googleapis.com/auth/calendar.events`

## 6. Slack (slack-mcp)

### Prerequisites
- Slack workspace admin access
- Slack App created

### Setup
1. Go to [Slack API](https://api.slack.com/apps)
2. Create new app (from manifest or scratch)
3. Add Bot Token Scopes:
   - `chat:write`
   - `channels:read`
   - `channels:history`
   - `users:read`
4. Install app to workspace
5. Copy Bot User OAuth Token
6. Set environment variables in `.env`:
   ```
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_TEAM_ID=T00000000
   ```

## 7. Odoo (odoo-mcp)

### Prerequisites
- Odoo 19 Community Edition installed (self-hosted)
- Database created with Chart of Accounts

### Setup
1. Install Odoo Community:
   ```bash
   # Docker (recommended)
   docker run -d -p 8069:8069 --name odoo -t odoo:19
   ```
2. Create database at `http://localhost:8069/web/database/create`
3. Install Accounting module
4. Generate API key:
   - Settings > Users > Select user > API Keys tab > New API Key
5. Set environment variables in `.env`:
   ```
   ODOO_URL=http://localhost:8069
   ODOO_DB=fte-accounting
   ODOO_USER=admin
   ODOO_API_KEY=your-api-key
   ```

### Odoo JSON-RPC Endpoints
- Authentication: `/web/session/authenticate`
- Search/Read: `/web/dataset/call_kw`
- Create: `/web/dataset/call_kw` with `create` method
- Models used: `account.move`, `account.move.line`, `res.partner`, `account.account`

## Security Notes

- Never commit `.env` to version control
- Use environment variable references (`${VAR}`) in `settings.local.json`
- Rotate API keys periodically
- Use minimum required OAuth scopes
- All MCP actions involving external services go through HITL approval
