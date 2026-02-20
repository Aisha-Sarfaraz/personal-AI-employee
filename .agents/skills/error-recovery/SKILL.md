---
name: error-recovery
description: Automated retry, fallback, and circuit-breaker execution for failed operations. Use when any agent encounters a recoverable error and needs structured recovery.
version: 1.0.0
type: system
inputs:
  - failed_action: The action that failed
  - error: Error details (type, message, code)
  - agent: The agent that encountered the error
  - retry_count: Number of retries already attempted
outputs:
  - recovery_action: What recovery action was taken (retry, fallback, circuit_break, escalate)
  - result: Success or continued failure
  - recommendation: Next steps if recovery failed
reusability: extremely-high
framework_agnostic: true
---

# Skill: error-recovery

## 1. Purpose

Provide structured error recovery for failed operations using industry-standard patterns: retry with exponential backoff, fallback to alternative actions, and circuit breaker to prevent cascading failures.

## 2. When to Use This Skill

**Mandatory invocation:**
- Any MCP server call fails
- External API returns an error
- Timeout occurs during action execution
- Resource temporarily unavailable

## 3. Recovery Strategy Matrix

| Error Type | Strategy | Max Retries | Backoff |
|-----------|----------|-------------|---------|
| Network timeout | Retry with backoff | 3 | Exponential (1s, 2s, 4s) |
| Rate limit (429) | Retry with backoff | 3 | Use Retry-After header |
| Server error (5xx) | Retry with backoff | 2 | Exponential (2s, 4s) |
| Auth error (401) | No retry — escalate | 0 | N/A |
| Not found (404) | No retry — report | 0 | N/A |
| Validation error (400) | No retry — fix input | 0 | N/A |
| MCP disconnected | Retry connection | 3 | Exponential (5s, 10s, 20s) |
| Unknown error | Circuit break | 1 | 30s pause |

## 4. Circuit Breaker Pattern

```
States: CLOSED → OPEN → HALF_OPEN → CLOSED

CLOSED (normal): Actions execute normally
  → If 3 failures in 1 minute: transition to OPEN

OPEN (blocking): Actions rejected immediately
  → After 30 seconds: transition to HALF_OPEN

HALF_OPEN (testing): Allow 1 test action
  → If success: transition to CLOSED
  → If failure: transition to OPEN
```

## 5. Fallback Hierarchy

When primary action fails after max retries:

1. **Alternative MCP**: Try alternative MCP server if available
2. **Cached Data**: Use last known good data if read operation
3. **Queue for Later**: Add to retry queue for later execution
4. **Escalate to Human**: Alert human with error context and options

## 6. Workflow

1. **Receive**: Accept failed action with error details
2. **Classify**: Determine error type and recoverability
3. **Check Circuit**: Verify circuit breaker state for this service
4. **Recover**: Apply appropriate strategy (retry, fallback, break)
5. **Log**: Record recovery attempt and outcome
6. **Report**: Return result with recommendation

## 7. Constraints

- Never retry non-idempotent actions (send email, post transaction) without human approval
- Circuit breaker thresholds are configurable but have safe defaults
- All recovery attempts are logged for observability
- Escalate to human after max retries exhausted
- Never mask errors — always surface them even if recovery succeeds
