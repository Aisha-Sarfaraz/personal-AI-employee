---
name: draft-social-post
description: Create platform-optimized social media content with appropriate tone, hashtags, and formatting. Use when the Social Media Agent needs to compose content for any platform.
version: 1.0.0
agent: social-media-agent
type: action
inputs:
  - platform: Target platform (linkedin, twitter, instagram, facebook)
  - topic: What the post is about
  - tone: Desired tone (professional, casual, inspirational, educational)
  - include_hashtags: Whether to include hashtags (default true)
  - media_suggestion: Whether to suggest accompanying visuals
outputs:
  - draft_post: Complete post draft optimized for platform
  - hashtags: Suggested hashtags
  - media_ideas: Suggested visual content descriptions
  - character_count: Post length vs platform limit
reusability: extremely-high
framework_agnostic: true
---

# Skill: draft-social-post

## 1. Purpose

Create engaging, platform-specific social media content that matches brand voice and optimizes for engagement. Every draft requires HITL approval before publishing.

## 2. Platform Specifications

| Platform | Max Length | Hashtags | Media | Tone |
|----------|-----------|----------|-------|------|
| LinkedIn | 3,000 chars | 3-5 | Optional | Professional |
| Twitter/X | 280 chars | 2-3 | Recommended | Concise |
| Instagram | 2,200 chars | 10-30 | Required | Visual-first |
| Facebook | 63,206 chars | 2-3 | Recommended | Conversational |

## 3. Workflow

1. **Context**: Understand topic, audience, and goals
2. **Draft**: Write platform-optimized content
3. **Hashtags**: Research and suggest relevant hashtags
4. **Media**: Suggest visual content ideas
5. **Review**: Check against brand guidelines
6. **Present**: Show draft to human for approval

## 4. HITL Gate

**Risk Level**: HIGH (public content)
**Approval Required**: YES — always before scheduling or publishing

## 5. Constraints

- Never publish without HITL approval
- Avoid controversial or political content unless explicitly requested
- Check hashtags for unintended associations
- Respect platform-specific formatting norms
