---
name: engagement-summary
description: Analyze and report social media engagement metrics across platforms. Use for periodic performance reviews or on-demand analytics.
version: 1.0.0
agent: social-media-agent
type: analysis
inputs:
  - platforms: Platforms to analyze (all or specific)
  - time_range: Period to analyze (week, month, custom)
outputs:
  - engagement_report: Structured report with metrics per platform
  - top_posts: Best performing content with metrics
  - trends: Engagement trends over time
  - recommendations: Content strategy recommendations
reusability: extremely-high
framework_agnostic: true
---

# Skill: engagement-summary

## 1. Purpose

Compile and analyze social media engagement metrics to inform content strategy. Identifies top-performing content and engagement trends.

## 2. Metrics Tracked

| Metric | Platforms |
|--------|----------|
| Impressions / Reach | All |
| Likes / Reactions | All |
| Comments | All |
| Shares / Retweets | LinkedIn, Twitter, Facebook |
| Saves | Instagram |
| Click-through rate | All (if links) |
| Follower growth | All |

## 3. Workflow

1. **Collect**: Gather metrics from platform analytics (via browser-mcp)
2. **Aggregate**: Combine metrics across platforms
3. **Analyze**: Identify top posts, trends, patterns
4. **Compare**: Benchmark against previous periods
5. **Recommend**: Suggest content strategy adjustments
6. **Report**: Generate structured engagement report

## 4. HITL Gate

**Risk Level**: LOW (read-only analysis)
**Approval Required**: NO — auto-approved

## 5. Constraints

- Read-only — never modify social media content or settings
- Include comparative data when available
- Flag significant trend changes (positive or negative)
