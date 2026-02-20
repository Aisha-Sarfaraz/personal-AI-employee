---
name: schedule-content
description: Manage content calendar and schedule posts for optimal engagement times. Use when approved content needs scheduling or the content calendar needs updating.
version: 1.0.0
agent: social-media-agent
type: action
inputs:
  - post_content: Approved post content
  - platform: Target platform
  - preferred_time: Preferred posting time (optional)
  - campaign: Campaign or theme tag (optional)
outputs:
  - scheduled_entry: Calendar entry with date, time, platform, content
  - calendar_updated: Whether content calendar was updated
reusability: extremely-high
framework_agnostic: true
---

# Skill: schedule-content

## 1. Purpose

Schedule approved social media content at optimal times and maintain the content calendar for visibility and planning.

## 2. Optimal Posting Times (Defaults)

| Platform | Best Days | Best Times (UTC) |
|----------|-----------|-----------------|
| LinkedIn | Tue-Thu | 08:00-10:00, 12:00-13:00 |
| Twitter/X | Mon-Fri | 09:00-11:00, 17:00-18:00 |
| Instagram | Mon, Wed, Fri | 11:00-13:00, 19:00-21:00 |
| Facebook | Wed-Fri | 09:00-11:00, 13:00-15:00 |

## 3. Workflow

1. **Check Calendar**: Verify no conflicts with existing scheduled posts
2. **Determine Time**: Use preferred time or optimal default
3. **Schedule**: Add to content calendar (`vault/social/content-calendar.md`)
4. **Confirm**: Present schedule to human for final approval
5. **Track**: Monitor scheduled vs published status

## 4. HITL Gate

**Risk Level**: HIGH (public content scheduling)
**Approval Required**: YES — content must be approved before scheduling

## 5. Constraints

- Only schedule pre-approved content
- Maintain minimum 4-hour gap between posts on same platform
- Update content calendar after every scheduling action
- Log all scheduling decisions for audit trail
