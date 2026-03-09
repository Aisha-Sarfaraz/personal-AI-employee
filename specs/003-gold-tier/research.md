# Gold Tier Research — External API Decisions

**Feature**: 003-gold-tier
**Date**: 2026-02-25
**Status**: COMPLETE — all Phase 0 decisions resolved
**Branch**: 003-gold-tier

---

## Decision 1 — Odoo JSON-RPC Client Pattern

### Question
How does `OdooMCPClient` call Odoo 19+ over JSON-RPC? Authentication, endpoint, library.

### Research Findings

- **Endpoint**: `POST /web/dataset/call_kw` (Odoo External API)
- **Protocol**: JSON-RPC 2.0 over HTTP; `Content-Type: application/json`
- **Library**: `requests` (stdlib-compatible, synchronous — matches the rest of the Python codebase)
- **Auth strategy**: **Per-call, stateless** — each request body includes `db`, `uid`, and `password`
  as positional arguments to `execute_kw`; no session auth step, no cookie management.
- **Response shape**: `{"jsonrpc": "2.0", "result": <data>}` on success;
  `{"jsonrpc": "2.0", "error": {"message": "...", "data": {...}}}` on error.

### Canonical Pattern

```python
import requests

def _call(url: str, db: str, uid: int, password: str,
          model: str, method: str, args: list, kwargs: dict) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "id": 1,
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [db, uid, password, model, method, args, kwargs],
        },
    }
    resp = requests.post(f"{url}/web/dataset/call_kw", json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"]["data"].get("message", "Odoo error"))
    return data["result"]
```

### Decision
Use `requests` library, per-call auth, stateless design. `uid` and `password` read from
`ODOO_UID` and `ODOO_PASSWORD` env vars on `OdooMCPClient.__init__`.

### Alternatives Considered

| Option | Verdict |
|--------|---------|
| `xmlrpc.client` (stdlib) | Older Odoo API path; External API (JSON-RPC) is preferred in Odoo 17+ |
| Session-based auth (`/web/session/authenticate` first) | Adds statefulness; rejected per clarification C (per-call is simpler) |
| `odooly` third-party library | Extra dependency; JSON-RPC pattern is trivial to implement directly |

---

## Decision 2 — Meta Graph API (Facebook + Instagram)

### Question
Which Meta Graph API version, endpoint pattern, authentication model, and rate limits apply
to posting and reading engagement for a Facebook Page + Instagram Business account?

### Research Findings

- **API Version**: `v20.0` (stable, long-term support as of 2025)
- **Base URL**: `https://graph.facebook.com/v20.0`
- **Auth**: Long-lived Page access token in `FACEBOOK_ACCESS_TOKEN` env var (60-day lifespan).
  Header: `Authorization: Bearer {token}` (or `access_token` query param; use header for security).

#### Facebook Page Post

```
POST /v20.0/{page-id}/feed
Content-Type: application/json
Authorization: Bearer {token}
Body: {"message": "Post text"}
Response: {"id": "post-id"}
```

#### Instagram Publishing (Two-Step)

```
# Step 1 — Create container
POST /v20.0/{ig-user-id}/media
Body: {"caption": "text", "image_url": "https://..."}
Response: {"id": "creation-id"}

# Step 2 — Publish
POST /v20.0/{ig-user-id}/media_publish
Body: {"creation_id": "<creation-id>"}
Response: {"id": "media-id"}
```

- **Rate limits**: 200 calls/hour per token. Facebook engagement read: 25 posts returned
  per request with `limit` parameter.
- **Engagement read endpoint**:
  `GET /me/posts?fields=message,likes.summary(true),comments.summary(true),created_time`

### Decision
Use Meta Graph API v20.0 with long-lived Page token from `.env`.
Single `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN`, `INSTAGRAM_USER_ID` env vars.
No Instagram-specific token needed — same Page token works for cross-posting.
Library: raw `requests` (no `facebook-sdk` dependency needed).

### Alternatives Considered

| Option | Verdict |
|--------|---------|
| `facebook-sdk` Python library | Unmaintained; raw requests is simpler |
| Instagram separate token | Not needed; Page token scopes cover IG Business accounts |
| Graph API v19.0 | v20.0 is newer LTS; use v20.0 |

---

## Decision 3 — Twitter API v2 (Free Tier)

### Question
How does `TwitterWatcher` read timeline metrics and `post_twitter.py` post tweets using
Free tier Twitter API v2? Authentication, library, rate limits.

### Research Findings

- **Library**: `tweepy` v4.14+ — handles OAuth 1.0a signing and API v2 endpoints natively.
- **Read auth**: Bearer token (`TWITTER_BEARER_TOKEN`) — `tweepy.Client(bearer_token=...)`.
  Used for `GET /2/users/:id/tweets?tweet.fields=public_metrics`.
- **Write auth**: OAuth 1.0a — `tweepy.Client(consumer_key, consumer_secret, access_token, access_secret)`.
  Used for `POST /2/tweets`.
- **User ID**: Static env var `TWITTER_USER_ID` — no API round-trip needed; user looks up
  once from profile. Avoids costly `GET /2/users/by/username/:username` call.
- **Rate limits (Free tier)**:
  - Read: 300 requests per 15 minutes (Bearer token)
  - Write: 50 requests per 15 minutes; 1,500 tweets/month cap
  - Gold strategy: 1 tweet/day (rate_limiter guard); 24h poll interval for watcher

#### Read Pattern

```python
import tweepy
client = tweepy.Client(bearer_token=os.getenv("TWITTER_BEARER_TOKEN"))
tweets = client.get_users_tweets(
    id=os.getenv("TWITTER_USER_ID"),
    tweet_fields=["public_metrics"],
    max_results=10
)
```

#### Write Pattern

```python
client = tweepy.Client(
    consumer_key=os.getenv("TWITTER_API_KEY"),
    consumer_secret=os.getenv("TWITTER_API_SECRET"),
    access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
    access_token_secret=os.getenv("TWITTER_ACCESS_SECRET"),
)
response = client.create_tweet(text="Tweet text ≤280 chars")
```

### Decision
Use `tweepy` v4.14+. Bearer token for reads; OAuth 1.0a for writes.
Poll interval: 86400s (24h). Rate guard: `post_tweet: 1/day` via `rate_limiter.check_and_increment`.

### Alternatives Considered

| Option | Verdict |
|--------|---------|
| `twitter-api-v2` library | Less mature than tweepy; rejected |
| OAuth 2.0 PKCE for reads | Bearer token is simpler for server-side read-only access |
| `requests` + manual OAuth 1.0a signing | High complexity; tweepy handles signing correctly |

---

## Decision 4 — MCP Python SDK Server Pattern

### Question
How is a custom Python stdio MCP server implemented using the `mcp` Python SDK (v1.x)?
What class/decorator pattern is correct? How are tools tested without subprocess?

### Research Findings

- **SDK**: `mcp` Python package v1.x (pip install mcp)
- **Server class**: `mcp.server.Server` (NOT `FastMCP` — not available in v1.0+)
- **Decorators**: `@server.list_tools()` and `@server.call_tool()`
- **Transport**: stdio via `anyio` — `async with stdio_server() as (read, write): await server.run(read, write, ...)`
- **Testing**: Call `server.call_tool("tool_name", args_dict)` handler directly in pytest
  without spawning subprocess. Avoids I/O complexity.

#### Server Skeleton

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import anyio

server = Server("odoo-mcp")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="create_invoice", description="Create Odoo invoice",
             inputSchema={...})
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "create_invoice":
        result = await _create_invoice(arguments)
        return [TextContent(type="text", text=json.dumps(result))]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                        server.create_initialization_options())

if __name__ == "__main__":
    anyio.run(main)
```

#### Test Pattern (no subprocess)

```python
import pytest

@pytest.mark.asyncio
async def test_create_invoice_dev_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    # Import server module to get handler
    from src.mcp_servers.odoo_mcp.server import call_tool
    result = await call_tool("create_invoice", {"partner": "ACME", "amount": 100.0})
    assert result[0].text  # JSON string
    data = json.loads(result[0].text)
    assert data["status"] == "pending_approval"
```

### Decision
Use `mcp.server.Server` with `@server.list_tools()` + `@server.call_tool()` decorators.
Run with `anyio.run(main)` via stdio transport. Test handlers directly in pytest (no subprocess).

### Alternatives Considered

| Option | Verdict |
|--------|---------|
| `FastMCP` | Not in mcp v1.0+; rejected |
| HTTP transport | Spec requires stdio (same lifecycle as email-mcp); rejected |
| Manual JSON-RPC over stdin/stdout | mcp SDK handles protocol framing; no need |

---

## Summary Table

| Domain | Library | Auth | Rate Limit | Pattern |
|--------|---------|------|------------|---------|
| Odoo JSON-RPC | `requests` | Per-call (db/uid/pwd in body) | — | stateless |
| Facebook Page | `requests` | Page access token (Bearer) | 200 req/hr | `POST /v20.0/{page-id}/feed` |
| Instagram Business | `requests` | Same Page token | 200 req/hr | Two-step: create container → publish |
| Twitter/X reads | `tweepy` | Bearer token | 300 req/15min | `GET /2/users/{id}/tweets` |
| Twitter/X writes | `tweepy` | OAuth 1.0a | 1,500/month | `POST /2/tweets` |
| Odoo MCP server | `mcp` SDK | stdio process | — | `mcp.server.Server` |
