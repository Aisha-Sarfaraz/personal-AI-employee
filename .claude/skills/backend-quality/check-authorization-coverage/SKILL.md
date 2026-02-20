---
name: check-authorization-coverage
description: Ensure all protected API endpoints verify permissions and authorization using Security() dependencies
version: 1.0.0
agent: python-backend-architect
type: validation
inputs:
  - source_paths: Array of source code paths containing API routes
  - protected_endpoints_config: Configuration defining which endpoints require authorization
outputs:
  - authorization_report: Authorization coverage validation report
  - coverage_score: Percentage of protected endpoints with authorization (0-100)
  - unprotected_endpoints: List of endpoints lacking authorization checks
  - recommendations: Actionable authorization improvements
reusability: extremely-high
framework_agnostic: yes
requires_context7: true
estimated_execution_time: 1-3 minutes
---

# Skill: check-authorization-coverage

## 1. Purpose

This skill ensures all protected API endpoints implement proper authorization checks using framework-specific security patterns (FastAPI Security(), Flask decorators, Django permissions). It prevents unauthorized access vulnerabilities by validating that all endpoints requiring authentication/authorization have proper security dependencies across ANY Python backend framework and ANY domain.

**Core Objectives:**
- **Authorization Coverage Validation**: Verify all protected endpoints have authorization checks
- **Security Dependency Detection**: Detect FastAPI Security(), Depends(), Flask @login_required, Django permissions
- **Permission Scope Validation**: Ensure OAuth2 scopes and role-based permissions are declared
- **Unauthenticated Endpoint Detection**: Identify endpoints missing authentication when required
- **Authorization Pattern Enforcement**: Validate framework-specific security best practices
- **Framework/Domain Agnostic**: Works across FastAPI, Flask, Django, and all domains

**Why This Skill Exists:**

Missing authorization leads to:
- **Security vulnerabilities**: Unauthorized users access protected resources
- **Data breaches**: Sensitive data exposed to unauthenticated users
- **Privilege escalation**: Users access resources beyond their permissions
- **Compliance violations**: GDPR, HIPAA, SOC 2 require access controls

This skill provides automated, repeatable validation to catch authorization gaps before deployment.

**Unlike manual security reviews, this skill:**
- **Detects missing authorization**: Scans all endpoints for security dependencies
- **Validates OAuth2 scopes**: Ensures endpoints declare required permissions
- **Checks permission patterns**: Verifies role-based access control (RBAC)
- **Framework-specific validation**: Uses FastAPI Security(), Flask @login_required, Django permissions
- **Generates audit reports**: Lists all endpoints with authorization status
- Works across **all Python backends**

---

## 2. When to Use This Skill

### Mandatory Invocation Scenarios

**ALWAYS invoke this skill when:**

1. **Pre-Deployment Security Audit** - Validate authorization before production release
2. **After API Changes** - Verify new endpoints have proper authorization
3. **Pull Request Security Review** - Block PRs with missing authorization
4. **Compliance Audits** - Generate authorization coverage reports for auditors
5. **Security Testing** - Validate authorization as part of penetration testing

### Specific Trigger Conditions

Invoke immediately when code includes:

**FastAPI:**
- New route decorators (`@app.get`, `@app.post`)
- Routes accessing sensitive data (user data, financial data, PII)
- Routes modifying resources (POST, PUT, DELETE endpoints)

**Flask:**
- New route decorators (`@app.route`, `@bp.route`)
- Routes requiring authentication

**Django REST Framework:**
- New ViewSet definitions
- API endpoint changes

### User-Requested Scenarios

Users may explicitly request:
- "Check authorization coverage before deployment"
- "Audit API security for missing auth checks"
- "Verify all protected endpoints require authentication"
- "Generate security compliance report"

---

## 3. Inputs

### Required Inputs

| Input | Type | Description | Example |
|-------|------|-------------|---------|
| `source_paths` | `string[]` | Paths to source code containing API routes | `["src/backend/api/", "src/main.py"]` |
| `protected_endpoints_config` | `object` | Configuration defining authorization requirements | See below |

### Protected Endpoints Configuration

```typescript
interface ProtectedEndpointsConfig {
  // Patterns for endpoints requiring authentication
  require_authentication: string[]; // e.g., ["/api/*", "/tasks/*"]

  // Endpoints that MUST be public (no auth required)
  public_endpoints: string[]; // e.g., ["/health", "/docs", "/openapi.json"]

  // Endpoints requiring specific scopes/permissions
  scope_requirements: {
    endpoint: string;
    required_scopes: string[];
  }[];

  // Endpoints requiring specific roles
  role_requirements: {
    endpoint: string;
    required_roles: string[];
  }[];
}
```

**Example Configuration**:
```json
{
  "require_authentication": [
    "/api/tasks/*",
    "/api/users/me",
    "/api/admin/*"
  ],
  "public_endpoints": [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/login",
    "/api/auth/register"
  ],
  "scope_requirements": [
    {
      "endpoint": "/api/tasks/*",
      "required_scopes": ["tasks:read", "tasks:write"]
    },
    {
      "endpoint": "/api/admin/*",
      "required_scopes": ["admin"]
    }
  ],
  "role_requirements": [
    {
      "endpoint": "/api/admin/*",
      "required_roles": ["admin"]
    }
  ]
}
```

### Optional Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `strict_mode` | `boolean` | `true` | Fail on any missing authorization (even warnings) |
| `severity_threshold` | `"low" \| "medium" \| "high" \| "critical"` | `"high"` | Minimum severity to report |

---

## 4. Outputs

### Validation Report Structure

```typescript
interface AuthorizationReport {
  summary: {
    total_endpoints: number;
    protected_endpoints: number;
    authorized_endpoints: number;
    unprotected_endpoints_count: number;
    coverage_score: number; // 0-100
    validation_timestamp: string;
  };

  critical_issues: AuthorizationIssue[];
  high_severity_issues: AuthorizationIssue[];
  unprotected_endpoints: UnprotectedEndpoint[];
  recommendations: Recommendation[];
}

interface AuthorizationIssue {
  severity: "critical" | "high" | "medium" | "low";
  endpoint: string;
  http_method: string;
  issue_type: string;
  description: string;
  impact: string;
  remediation: string;
  code_location: string;
}

interface UnprotectedEndpoint {
  endpoint: string;
  http_method: string;
  file_path: string;
  line_number: number;
  requires_auth: boolean;
  current_protection: "none" | "authentication" | "authorization";
  recommended_protection: string;
}
```

### Coverage Score Calculation

```
Coverage Score = (authorized_endpoints / total_protected_endpoints) * 100

Blocking Threshold: < 100 (all protected endpoints MUST have authorization)
Warning Threshold: N/A (authorization is binary - either protected or not)
```

---

## 5. Workflow

### Step 1: Context7 Integration - Fetch Latest Authorization Patterns

**Purpose**: Ensure validation uses current FastAPI Security(), Flask, Django authorization patterns.

**Key Patterns from Context7:**

**FastAPI Security() with OAuth2 Scopes:**
```python
from fastapi import Security, Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme)
):
    # Validate token and scopes
    return user

app = FastAPI()

@app.get("/tasks/", dependencies=[Security(get_current_user, scopes=["tasks:read"])])
async def get_tasks():
    return []

@app.post("/tasks/", dependencies=[Security(get_current_user, scopes=["tasks:write"])])
async def create_task():
    return {}

@app.delete("/admin/users/{user_id}", dependencies=[Security(get_current_user, scopes=["admin"])])
async def delete_user(user_id: int):
    return {}
```

**Flask Authorization:**
```python
from flask import Flask
from flask_login import login_required, current_user
from functools import wraps

app = Flask(__name__)

def require_role(role):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.has_role(role):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route("/tasks/")
@login_required
def get_tasks():
    return []

@app.route("/admin/users/", methods=["DELETE"])
@require_role("admin")
def delete_user():
    return {}
```

**Django REST Framework:**
```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminUser

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tasks(request):
    return Response([])

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_user(request, user_id):
    return Response({})
```

---

### Step 2: Scan Codebase for Endpoints

**Extract All Endpoints:**

**FastAPI AST Parsing:**
```python
import ast

def extract_fastapi_endpoints(file_path):
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())

    endpoints = []

    for node in ast.walk(tree):
        # Find route decorators: @app.get, @app.post, etc.
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if hasattr(decorator.func, 'attr'):
                        method = decorator.func.attr  # 'get', 'post', etc.
                        if method in ['get', 'post', 'put', 'delete', 'patch']:
                            # Extract path from decorator arguments
                            path = decorator.args[0].value if decorator.args else None

                            # Check for Security() or Depends() in function parameters
                            has_security = any(
                                'Security' in ast.unparse(param.annotation)
                                for param in node.args.args
                                if param.annotation
                            )

                            # Check for dependencies parameter in decorator
                            has_dependencies = any(
                                keyword.arg == 'dependencies'
                                for keyword in decorator.keywords
                            )

                            endpoints.append({
                                'path': path,
                                'method': method.upper(),
                                'function': node.name,
                                'file': file_path,
                                'line': node.lineno,
                                'has_security': has_security or has_dependencies
                            })

    return endpoints
```

---

### Step 3: Validate Authorization Coverage

**Check Each Endpoint Against Configuration:**

```python
def validate_authorization_coverage(endpoints, config):
    issues = []
    unprotected = []

    for endpoint in endpoints:
        # Check if endpoint requires authentication
        requires_auth = any(
            fnmatch.fnmatch(endpoint['path'], pattern)
            for pattern in config['require_authentication']
        )

        # Check if endpoint is explicitly public
        is_public = any(
            fnmatch.fnmatch(endpoint['path'], pattern)
            for pattern in config['public_endpoints']
        )

        # Skip public endpoints
        if is_public:
            continue

        # If endpoint requires auth but has no security
        if requires_auth and not endpoint['has_security']:
            issues.append({
                'severity': 'critical',
                'endpoint': f"{endpoint['method']} {endpoint['path']}",
                'issue_type': 'missing_authorization',
                'description': f'Protected endpoint lacks authorization check',
                'impact': 'Unauthorized users can access this endpoint',
                'remediation': generate_remediation(endpoint),
                'code_location': f"{endpoint['file']}:{endpoint['line']}"
            })

            unprotected.append({
                'endpoint': endpoint['path'],
                'http_method': endpoint['method'],
                'file_path': endpoint['file'],
                'line_number': endpoint['line'],
                'requires_auth': True,
                'current_protection': 'none',
                'recommended_protection': 'Security(get_current_user)'
            })

    return issues, unprotected
```

**Validate OAuth2 Scopes:**

```python
def validate_oauth2_scopes(endpoints, config):
    issues = []

    for scope_req in config.get('scope_requirements', []):
        matching_endpoints = [
            e for e in endpoints
            if fnmatch.fnmatch(e['path'], scope_req['endpoint'])
        ]

        for endpoint in matching_endpoints:
            # Parse Security() scopes from code
            declared_scopes = extract_security_scopes(endpoint)

            required_scopes = set(scope_req['required_scopes'])
            actual_scopes = set(declared_scopes)

            if not required_scopes.issubset(actual_scopes):
                missing_scopes = required_scopes - actual_scopes

                issues.append({
                    'severity': 'high',
                    'endpoint': f"{endpoint['method']} {endpoint['path']}",
                    'issue_type': 'missing_oauth2_scopes',
                    'description': f'Missing required OAuth2 scopes: {missing_scopes}',
                    'impact': 'Users without proper permissions can access this endpoint',
                    'remediation': f'Add scopes to Security(): Security(get_current_user, scopes={list(required_scopes)})',
                    'code_location': f"{endpoint['file']}:{endpoint['line']}"
                })

    return issues
```

---

### Step 4: Generate Remediation Recommendations

**Example Remediation Generation:**

```python
def generate_remediation(endpoint):
    if endpoint['framework'] == 'fastapi':
        return f"""
Add authorization to endpoint:

# Before (Vulnerable):
@app.{endpoint['method'].lower()}("{endpoint['path']}")
async def {endpoint['function']}():
    return {{}}

# After (Secure):
@app.{endpoint['method'].lower()}("{endpoint['path']}")
async def {endpoint['function']}(
    current_user: User = Security(get_current_user, scopes=["tasks:read"])
):
    return {{}}
"""

    elif endpoint['framework'] == 'flask':
        return f"""
Add @login_required decorator:

# Before (Vulnerable):
@app.route("{endpoint['path']}", methods=["{endpoint['method']}"])
def {endpoint['function']}():
    return {{}}

# After (Secure):
@app.route("{endpoint['path']}", methods=["{endpoint['method']}"])
@login_required
def {endpoint['function']}():
    return {{}}
"""
```

---

### Step 5: Generate Report

**Markdown Report Example**:

```markdown
# Authorization Coverage Report

**Coverage Score**: 85/100 ⚠️

## Summary
- **Total Endpoints**: 20
- **Protected Endpoints**: 15
- **Authorized Endpoints**: 13
- **Unprotected Endpoints**: 2
- **Critical Issues**: 2

## Critical Issues

### 🔴 Missing Authorization on Protected Endpoint
**Endpoint**: `DELETE /api/tasks/{task_id}`
**File**: `src/backend/api/tasks.py:45`
**Issue**: Protected endpoint lacks authorization check
**Impact**: Unauthorized users can delete tasks

**Current Code**:
```python
@app.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int):
    # No authorization check
    return {}
```

**Remediation**:
```python
@app.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    current_user: User = Security(get_current_user, scopes=["tasks:write"])
):
    # Verify user owns task or has admin permission
    if not await user_owns_task(current_user.id, task_id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")
    return {}
```

---

### 🔴 Missing OAuth2 Scopes
**Endpoint**: `POST /api/admin/users/{user_id}/ban`
**File**: `src/backend/api/admin.py:78`
**Issue**: Missing required OAuth2 scope: `admin`

**Current Code**:
```python
@app.post("/api/admin/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    current_user: User = Security(get_current_user)  # Missing scopes
):
    return {}
```

**Remediation**:
```python
@app.post("/api/admin/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    current_user: User = Security(get_current_user, scopes=["admin"])  # ✅ Added scope
):
    return {}
```

## Unprotected Endpoints

| Endpoint | Method | File | Recommended Protection |
|----------|--------|------|------------------------|
| `/api/tasks/{task_id}` | DELETE | `tasks.py:45` | `Security(get_current_user, scopes=["tasks:write"])` |
| `/api/admin/users/{user_id}/ban` | POST | `admin.py:78` | `Security(get_current_user, scopes=["admin"])` |

## Deployment Recommendation
❌ **BLOCKED** - Fix 2 critical authorization issues before deployment
```

---

## 6. Constraints & Limitations

**This skill validates:**
- Presence of authorization checks (Security(), Depends(), decorators)
- OAuth2 scope declarations
- Role-based access control patterns
- Authentication dependency usage

**This skill does NOT validate:**
- Authorization logic correctness (requires runtime testing)
- Session management security
- Token validation implementation
- Permission checking logic

---

## 7. Reusability & Extensibility

**Cross-Project Reusability: Extremely High**

Works across:
- **Any Python backend**: FastAPI, Flask, Django REST Framework, Pyramid
- **Any domain**: Todo, E-commerce, Healthcare, SaaS, FinTech
- **Any auth pattern**: OAuth2, JWT, session-based, API keys

**CI/CD Integration Example**:
```yaml
# GitHub Actions
- name: Check Authorization Coverage
  run: |
    python scripts/check_authorization.py \
      --source src/backend \
      --config authorization-config.json \
      --strict

    if [ $? -ne 0 ]; then
      echo "❌ Authorization coverage failed"
      exit 1
    fi
```

---

## 8. Integration Points

**Agent Integration**: Owned by `python-backend-architect` (Operational Agent)

**Blocking Authority**:
- Backend Architect has **NO** blocking authority by default
- Integration Orchestrator **MUST** block if any protected endpoint lacks authorization

**Multi-Agent Coordination**:
- **Better Auth Guardian**: Backend Architect validates authorization patterns align with Better Auth security model
- **Integration Orchestrator**: Runs this skill as security quality gate
- **Test Strategy Architect**: Authorization tests count toward integration coverage

---

## Appendix: Authorization Patterns Reference

### FastAPI Security Patterns

**Basic Authentication**:
```python
from fastapi import Security, Depends

@app.get("/tasks/")
async def get_tasks(current_user: User = Depends(get_current_user)):
    return []
```

**OAuth2 with Scopes**:
```python
@app.post("/tasks/")
async def create_task(
    current_user: User = Security(get_current_user, scopes=["tasks:write"])
):
    return {}
```

**Multiple Scopes**:
```python
@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Security(get_current_user, scopes=["admin", "users:delete"])
):
    return {}
```

### Common Authorization Anti-Patterns

| Anti-Pattern | Issue | Fix |
|--------------|-------|-----|
| No authorization on DELETE endpoint | Unauthorized users can delete resources | Add `Security(get_current_user, scopes=["resource:write"])` |
| Admin endpoint with no scope | Any authenticated user can access admin functions | Add `scopes=["admin"]` to Security() |
| Relying on query param for auth | User ID in query param (`?user_id=123`) | Use `current_user` from Security() dependency |
| Authorization in business logic only | No framework-level enforcement | Move to route-level Security() |

---

**End of Skill Definition**
