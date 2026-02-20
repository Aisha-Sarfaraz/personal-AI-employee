---
name: validate-better-auth-security
description: Validate Better Auth implementation against security best practices using Context7 MCP documentation
version: 1.0.0
agent: better-auth-guardian
type: validation
inputs:
  - file_paths: Array of file paths containing Better Auth code
  - validation_scope: "full" | "session-only" | "config-only" | "client-only"
outputs:
  - validation_report: Security validation report with severity levels
  - security_score: Overall security score (0-100)
  - critical_issues: List of blocking security violations
  - recommendations: Actionable security improvements
reusability: extremely-high
framework_agnostic: yes
requires_context7: true
estimated_execution_time: 2-4 minutes
---

# Skill: validate-better-auth-security

## 1. Purpose

This skill validates Better Auth implementations against the latest security best practices, framework patterns, and official documentation. It ensures authentication code follows secure session management, CSRF protection, error handling, and secret management standards across ANY framework (Next.js, React, Vue, Express, etc.) and ANY domain (Todo, E-commerce, SaaS, etc.).

**Core Objectives:**
- **Security-First Validation**: Detect security vulnerabilities before production deployment
- **Pattern Enforcement**: Ensure Better Auth API usage aligns with official documentation
- **Configuration Auditing**: Validate environment variables, secrets, and trusted origins
- **Session Security**: Verify session lifecycle, token handling, and revocation patterns
- **Authorization Correctness**: Validate permission checks and access control logic
- **Framework/Domain Agnostic**: Works across all frameworks and application domains

**Why This Skill Exists:**

Authentication is the **highest-risk area** in any application. A single misconfiguration (disabled CSRF protection, hardcoded secrets, missing session expiration) can expose the entire system to breaches. This skill provides automated, repeatable validation to catch these issues before deployment.

Unlike general code review, this skill:
- Uses **Context7 MCP** to fetch the latest Better Auth documentation (prevents outdated pattern detection)
- Validates **security-critical configurations** that static analysis tools miss
- Enforces **Better Auth best practices** (httpOnly cookies, SameSite attributes, CSRF protection)
- Provides **actionable remediation** with code examples from official docs
- Works across **all frameworks** (Next.js, Express, Fastify, Hono) and **all domains** (Todo, E-commerce, Healthcare)

---

## 2. When to Use This Skill

### Mandatory Invocation Scenarios

**ALWAYS invoke this skill when:**

1. **Before Implementation** - Validating existing Better Auth code before making changes
2. **After Auth Changes** - Any modification to Better Auth configuration, session handling, or permission logic
3. **Pre-Deployment** - Security audit before production release
4. **Periodic Audits** - Regular security reviews (weekly/sprint-based)
5. **Post-Dependency Update** - After upgrading Better Auth version

### Specific Trigger Conditions

Invoke immediately when code includes:

- `betterAuth({` - Better Auth server configuration
- `auth.api.getSession(` - Server-side session retrieval
- `auth.api.hasPermission(` - Permission checking
- `authClient.signIn` - Client-side authentication flows
- `authClient.useSession()` - Client-side session hook
- `BETTER_AUTH_SECRET` - Environment variable references
- `trustedOrigins` - CSRF protection configuration
- `disableCSRFCheck` - Security-critical flags
- `onAPIError` - Error handling configuration

### User-Requested Scenarios

Users may explicitly request:
- "Validate my Better Auth setup"
- "Review auth security before deployment"
- "Check if my session management is secure"
- "Audit Better Auth configuration"

---

## 3. Inputs

### Required Inputs

| Input | Type | Description | Example |
|-------|------|-------------|---------|
| `file_paths` | `string[]` | Absolute paths to files containing Better Auth code | `["/auth/auth.ts", "/lib/auth-client.ts"]` |
| `validation_scope` | `"full" \| "session-only" \| "config-only" \| "client-only"` | Scope of validation to perform | `"full"` |

### Optional Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `better_auth_version` | `string` | `"latest"` | Specific Better Auth version to validate against |
| `severity_threshold` | `"low" \| "medium" \| "high" \| "critical"` | `"medium"` | Minimum severity to report |
| `include_recommendations` | `boolean` | `true` | Include non-blocking improvement suggestions |

### Input Validation Rules

- `file_paths` must be non-empty array
- Each path must be absolute (not relative)
- Files must exist and be readable
- `validation_scope` must be one of the four defined values

---

## 4. Outputs

### Validation Report Structure

```typescript
interface ValidationReport {
  summary: {
    total_files_scanned: number;
    total_issues_found: number;
    critical_issues: number;
    high_severity_issues: number;
    medium_severity_issues: number;
    low_severity_issues: number;
    security_score: number; // 0-100
    validation_timestamp: string;
    better_auth_version_validated: string;
  };

  critical_issues: SecurityIssue[];
  high_severity_issues: SecurityIssue[];
  medium_severity_issues: SecurityIssue[];
  low_severity_issues: SecurityIssue[];
  recommendations: Recommendation[];
  files_scanned: FileValidationResult[];
}
```

### Security Score Calculation

```
Security Score = 100 - (
  (critical_issues * 25) +
  (high_severity_issues * 10) +
  (medium_severity_issues * 3) +
  (low_severity_issues * 1)
)

Blocking Threshold: < 70 (deployment blocked)
Warning Threshold: 70-85 (review required)
Acceptable: > 85
```

---

## 5. Workflow

### Step 1: Context7 Integration - Fetch Latest Better Auth Documentation

**Purpose**: Ensure validation uses current Better Auth security patterns.

**Actions**:

1. **Query Context7 MCP for Better Auth Documentation**:
   ```typescript
   const context7Queries = [
     {
       libraryId: "/better-auth/better-auth",
       query: "Better Auth security best practices CSRF protection session management httpOnly cookies"
     },
     {
       libraryId: "/better-auth/better-auth",
       query: "Better Auth secret management environment variables BETTER_AUTH_SECRET production security"
     },
     {
       libraryId: "/better-auth/better-auth",
       query: "Better Auth session configuration expiresIn updateAge cookieCache storeSessionInDatabase"
     },
     {
       libraryId: "/better-auth/better-auth",
       query: "Better Auth error handling APIError client error responses onAPIError"
     },
     {
       libraryId: "/better-auth/better-auth",
       query: "Better Auth authorization hasPermission userHasPermission admin plugin"
     }
   ];
   ```

2. **Extract Current Patterns from Documentation**
3. **Build Reference Pattern Database**

---

### Step 2: Pattern Detection - Scan Code for Better Auth Usage

**Current Patterns (Expected)**:
- `secret: process.env.BETTER_AUTH_SECRET` - Secure secret management
- `auth.api.getSession({ headers })` - Server-side session retrieval
- `session: { expiresIn, updateAge }` - Session configuration
- `disableCSRFCheck: false` - CSRF protection enabled
- `trustedOrigins: [...]` - Explicit origin allowlist
- `httpOnly: true, secure: true, sameSite: "lax"` - Secure cookie attributes

**Security Anti-Patterns (Dangerous)**:
- `secret: "hardcoded-secret"` - **CRITICAL**: Hardcoded secret
- `disableCSRFCheck: true` - **CRITICAL**: CSRF protection disabled
- `trustedOrigins: ["*"]` - **HIGH**: Wildcard origin
- `httpOnly: false` - **HIGH**: XSS vulnerability
- Missing error handling - **HIGH**: Unhandled auth failures
- `expiresIn: 31536000` (1 year) - **MEDIUM**: Excessive session lifetime

---

### Step 3: Security Validation - Analyze Patterns

**Validation Categories**:

1. **Session Management**
   - ✅ Session expiration configured
   - ✅ Session storage configured
   - ❌ Missing session configuration
   - ❌ Session expiration > 30 days

2. **CSRF Protection**
   - ✅ CSRF check enabled
   - ❌ CSRF disabled without justification
   - ❌ Wildcard origins

3. **Secret Management**
   - ✅ Secret from environment variable
   - ❌ Hardcoded secret
   - ❌ Default secret in production

4. **Cookie Security**
   - ✅ httpOnly, secure, sameSite attributes
   - ❌ Insecure cookie configuration

5. **Error Handling**
   - ✅ Client/server error handling
   - ❌ Missing error handling

---

### Step 4: Generate Report

**Markdown Report Example**:

```markdown
# Better Auth Security Validation Report

**Security Score**: 85/100 ⚠️

## Summary
- Critical Issues: 0
- High Severity: 2
- Medium Severity: 4
- Low Severity: 2

## High Severity Issues

### 🔴 Missing Error Handling After Sign-In
**File**: `src/components/LoginForm.tsx:45`
**Impact**: Unhandled failures may expose errors

**Remediation**:
```tsx
const { data, error } = await authClient.signIn.email({...})
if (error) {
  console.error("Auth failed:", error.message);
  setErrorMessage("Invalid credentials");
  return;
}
```

## Deployment Recommendation
⚠️ **REVIEW REQUIRED** - Address 2 high-severity issues before deployment
```

---

## 6. Constraints & Limitations

**This skill validates:**
- Better Auth configuration patterns
- Session security
- CSRF protection
- Error handling
- Secret management

**This skill does NOT validate:**
- Runtime security issues
- Database connectivity
- Network security
- Rate limiting

---

## 7. Reusability & Extensibility

**Cross-Project Reusability: Extremely High**

Works across:
- Any frontend framework (Next.js, React, Vue, Svelte, Solid, Lynx)
- Any backend framework (Next.js Route Handlers, Express, Fastify, Hono)
- Any application domain (Todo, E-commerce, Healthcare, SaaS)
- Any database (PostgreSQL, MySQL, SQLite, MongoDB)

**CI/CD Integration Example**:
```bash
claude-code skill validate-better-auth-security \
  --files "auth/**/*.ts" \
  --validation-scope full \
  --severity-threshold high \
  --output-format json > report.json

SCORE=$(jq '.summary.security_score' report.json)
if [ $SCORE -lt 70 ]; then
  echo "❌ Security score too low: $SCORE/100"
  exit 1
fi
```

---

## 8. Integration Points

**Agent Integration**: Owned by `better-auth-guardian` (Operational Agent)

**Blocking Authority**:
- Better Auth Guardian has **YES** blocking authority for security violations
- If `critical_issues.length > 0`, Better Auth Guardian **MUST** block work
- High-severity issues trigger **WARN** (user discretion)

**Multi-Agent Coordination**:
- **Backend Architect**: Better Auth Guardian validates their session verification
- **Frontend Architect**: Better Auth Guardian validates their client usage
- **Integration Orchestrator**: Better Auth Guardian provides auth validation for E2E tests

---

## Appendix: Pattern Reference

### Security Anti-Patterns (Blocking)

| Pattern | Severity | Remediation |
|---------|----------|-------------|
| `secret: "hardcoded"` | Critical | Use `process.env.BETTER_AUTH_SECRET` |
| `disableCSRFCheck: true` | Critical | Remove or justify |
| `trustedOrigins: ["*"]` | High | Define explicit origins |
| `httpOnly: false` | High | Set `httpOnly: true` |
| Missing error handling | High | Add `if (error) { ... }` |

### Current Best Practices

| Pattern | Purpose |
|---------|---------|
| `secret: process.env.BETTER_AUTH_SECRET` | Secure secrets |
| `auth.api.getSession({ headers })` | Server validation |
| `expiresIn: 604800` | Reasonable expiration |
| `httpOnly: true` | XSS prevention |
| `if (error) { ... }` | Error handling |

---

**End of Skill Definition**
