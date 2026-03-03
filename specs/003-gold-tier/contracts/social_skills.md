# Social Media Skills — API Contract

**Feature**: 003-gold-tier
**Modules**: `src/skills/post_facebook.py`, `src/skills/post_twitter.py`
**Date**: 2026-02-25

---

## Contract: `post_facebook.py`

### Interface

```python
def run(vault_root: str) -> dict:
    """
    Draft a Facebook + Instagram cross-post, gate on HITL, publish on approval.

    Returns:
        {"created": 1, "approval_file": "<path>"}    — approval file written
        {"skipped": 1, "reason": "too_soon"}          — posted within frequency_days
        {"skipped": 1, "reason": "disabled"}          — facebook.enabled = false in settings
        {"simulated": 1, "approval_file": "<path>"}   — dev_mode: true
    """
```

### Self-Guards

1. `settings.yaml` → `facebook.enabled` must be `true` (default: false).
2. Last Facebook post must be older than `facebook.frequency_days` (default: 3).
   Checked by scanning `vault/Logs/YYYY-MM-DD.json` for `action_type: post_facebook`.

### Execution Flow

```
1. Check guards → skip if disabled or too_soon
2. Draft post text using Claude API (fallback: template if dev_mode or no API key)
3. Write vault/Pending_Approval/FB_POST_<timestamp>.md
   frontmatter: {type: social_post_approval, platforms: [facebook, instagram],
                 draft_text: "...", character_count: N, risk_level: HIGH}
4. Return {created: 1, approval_file: "<path>"}
--- (approval moves file to vault/Approved/) ---
5. [On approval] Publish to Facebook: POST /v20.0/{page-id}/feed
6. [On approval] Publish to Instagram:
   a. POST /v20.0/{ig-user-id}/media → {id: creation_id}
   b. POST /v20.0/{ig-user-id}/media_publish → {id: media_id}
7. Audit log: {action_type: post_facebook, result: success, ...}
```

### Error Handling

| Error | Category | Action |
|-------|----------|--------|
| 401/403 from Meta API | `AUTH` | No retry; create vault alert; pause FacebookWatcher |
| 429 from Meta API | `TRANSIENT` | `@with_retry` (3 attempts, exponential back-off) |
| 5xx from Meta API | `TRANSIENT` | `@with_retry`; log `result: degraded` if exhausted |
| Claude API unavailable | `SYSTEM` | Fall back to template text; continue |

### Env Vars Required

| Var | Description |
|-----|-------------|
| `FACEBOOK_PAGE_ID` | Facebook Page ID for feed post |
| `FACEBOOK_ACCESS_TOKEN` | Long-lived Page access token (60-day) |
| `INSTAGRAM_USER_ID` | Instagram Business account user ID |

### Meta Graph API Calls

```
POST https://graph.facebook.com/v20.0/{FACEBOOK_PAGE_ID}/feed
Authorization: Bearer {FACEBOOK_ACCESS_TOKEN}
Body: {"message": "<draft_text>"}
→ {"id": "<post-id>"}

POST https://graph.facebook.com/v20.0/{INSTAGRAM_USER_ID}/media
Authorization: Bearer {FACEBOOK_ACCESS_TOKEN}
Body: {"caption": "<draft_text>", "image_url": "<optional>"}
→ {"id": "<creation-id>"}

POST https://graph.facebook.com/v20.0/{INSTAGRAM_USER_ID}/media_publish
Authorization: Bearer {FACEBOOK_ACCESS_TOKEN}
Body: {"creation_id": "<creation-id>"}
→ {"id": "<media-id>"}
```

---

## Contract: `post_twitter.py`

### Interface

```python
def run(vault_root: str) -> dict:
    """
    Draft a tweet, gate on HITL, publish on approval.

    Returns:
        {"created": 1, "approval_file": "<path>"}    — approval file written
        {"skipped": 1, "reason": "rate_limit"}        — already tweeted today
        {"skipped": 1, "reason": "disabled"}          — twitter.enabled = false
        {"simulated": 1, "approval_file": "<path>"}   — dev_mode: true
    """
```

### Self-Guards

1. `settings.yaml` → `twitter.enabled` must be `true` (default: false).
2. `rate_limiter.check_and_increment(vault_root, "post_tweet", limit_per_hour=1)` —
   effectively 1 tweet per 24h (rate_limiter uses hourly window; configured to 1 per period).
   Tweet limit stored in `settings.yaml` → `twitter.tweets_per_day: 1`.

### Execution Flow

```
1. Check guards → skip if disabled or rate limit exceeded
2. Draft tweet using Claude API (≤280 chars enforced; truncate + warn if over)
3. Write vault/Pending_Approval/TWEET_<timestamp>.md
   frontmatter: {type: social_post_approval, platforms: [twitter],
                 draft_text: "...", character_count: N, risk_level: HIGH}
4. Return {created: 1, approval_file: "<path>"}
--- (approval moves file to vault/Approved/) ---
5. [On approval] Post via tweepy:
   client = tweepy.Client(consumer_key, consumer_secret, access_token, access_secret)
   client.create_tweet(text=draft_text)
6. Audit log: {action_type: post_tweet, result: success, ...}
```

### Error Handling

| Error | Category | Action |
|-------|----------|--------|
| 401 from Twitter API | `AUTH` | No retry; vault alert; pause TwitterWatcher |
| 429 from Twitter API | `TRANSIENT` | `@with_retry` (3 attempts, max 60s delay) |
| 403 (suspended/blocked) | `AUTH` | No retry; vault alert |
| Tweet > 280 chars | `DATA` | Truncate at 277 + "..."; log warning |

### Env Vars Required

| Var | Description |
|-----|-------------|
| `TWITTER_BEARER_TOKEN` | For read-only calls (TwitterWatcher) |
| `TWITTER_API_KEY` | OAuth 1.0a consumer key |
| `TWITTER_API_SECRET` | OAuth 1.0a consumer secret |
| `TWITTER_ACCESS_TOKEN` | OAuth 1.0a access token |
| `TWITTER_ACCESS_SECRET` | OAuth 1.0a access token secret |
| `TWITTER_USER_ID` | Static numeric user ID for `GET /2/users/:id/tweets` |

### Twitter API v2 Calls

```python
# Read (TwitterWatcher)
client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
tweets = client.get_users_tweets(id=TWITTER_USER_ID,
                                  tweet_fields=["public_metrics"], max_results=10)

# Write (post_twitter.py on approval)
client = tweepy.Client(consumer_key=TWITTER_API_KEY,
                       consumer_secret=TWITTER_API_SECRET,
                       access_token=TWITTER_ACCESS_TOKEN,
                       access_token_secret=TWITTER_ACCESS_SECRET)
response = client.create_tweet(text=draft_text)
```

---

## FacebookWatcher Contract

```python
class FacebookWatcher(BaseWatcher):
    """
    Polls Meta Graph API for Page engagement every 3600s.
    Dev-mode reads vault/Watch/facebook_mock/sample_post.json.
    """
    POLL_INTERVAL_S = 3600

    def check_for_updates(self) -> list[dict]:
        """
        Returns list of engagement items:
        [{"id": "post-id", "text": "...", "likes": N, "comments": N,
          "reach": N, "created_at": "ISO8601"}]
        """

    def create_action_file(self, vault_root: str, item: dict) -> str:
        """
        Writes vault/Inbox/FB_ENGAGEMENT_<id>_<ts>.md with YAML frontmatter:
        {type: social_media_engagement, source: facebook, post_id: ..., likes: N, ...}
        Returns absolute path.
        """
```

Mock file format (`vault/Watch/facebook_mock/sample_post.json`):
```json
[
  {"id": "fb001", "text": "Our Q1 update!", "likes": 42, "comments": 7,
   "reach": 310, "created_at": "2026-02-24T09:00:00Z"}
]
```

---

## TwitterWatcher Contract

```python
class TwitterWatcher(BaseWatcher):
    """
    Polls Twitter API v2 for timeline metrics every 86400s (24h).
    Dev-mode reads vault/Watch/twitter_mock/sample_tweet.json.
    """
    POLL_INTERVAL_S = 86400

    def check_for_updates(self) -> list[dict]:
        """
        Returns list of tweet metric items:
        [{"id": "tweet-id", "text": "...", "retweet_count": N,
          "like_count": N, "reply_count": N, "created_at": "ISO8601"}]
        """

    def create_action_file(self, vault_root: str, item: dict) -> str:
        """
        Writes vault/Inbox/TW_ENGAGEMENT_<id>_<ts>.md with YAML frontmatter:
        {type: social_media_engagement, source: twitter, tweet_id: ..., likes: N, ...}
        Returns absolute path.
        """
```

Mock file format (`vault/Watch/twitter_mock/sample_tweet.json`):
```json
[
  {"id": "tw001", "text": "Big announcement!", "retweet_count": 5,
   "like_count": 28, "reply_count": 3, "created_at": "2026-02-24T08:00:00Z"}
]
```
