---
name: anomaly-detection
description: Detect unusual patterns in agent behavior, event frequency, error rates, and resource usage. Use for proactive issue identification before failures occur.
version: 1.0.0
agent: monitoring-agent
type: analysis
inputs:
  - metrics_source: Data source to analyze (logs, events, health_reports)
  - baseline_period: Period to use as baseline (default last_7_days)
  - sensitivity: Detection sensitivity (low, medium, high)
outputs:
  - anomalies: List of detected anomalies with severity and context
  - baseline_comparison: Current metrics vs baseline
  - risk_assessment: Overall system risk level based on anomalies
reusability: extremely-high
framework_agnostic: true
---

# Skill: anomaly-detection

## 1. Purpose

Proactively detect unusual patterns in system behavior before they become failures. Uses baseline comparison and threshold rules to identify deviations from normal operation.

## 2. Anomaly Types

| Type | Description | Threshold |
|------|-------------|-----------|
| Event flood | Event rate > 3x baseline | Configurable |
| Event drought | No events for > 2x expected interval | Configurable |
| Error spike | Error rate > 3x baseline | Configurable |
| Stuck workflow | Task unchanged for > 30 minutes | Configurable |
| Resource growth | Log/disk growth > 2x baseline rate | Configurable |
| Action burst | Agent actions > 100 in 1 minute | Fixed (safety) |
| Repeat pattern | Same action repeated > 10 times | Fixed (safety) |

## 3. Workflow

1. **Collect**: Gather metrics from logs, events, and health reports
2. **Baseline**: Calculate baseline from configured period
3. **Compare**: Current metrics vs baseline
4. **Detect**: Apply threshold rules to identify anomalies
5. **Classify**: Assign severity (info, warning, error, critical)
6. **Alert**: Generate alerts for significant anomalies
7. **Log**: Record all detections for trend analysis

## 4. HITL Gate

**Risk Level**: LOW (analysis only)
**Approval Required**: NO — auto-approved
**Exception**: CRITICAL anomalies trigger Monitoring Agent blocking authority

## 5. Constraints

- Never modify data — analysis only
- Log all detections including false positives (for tuning)
- Fixed safety thresholds (action burst, repeat pattern) cannot be overridden
- Include confidence score with each detection
