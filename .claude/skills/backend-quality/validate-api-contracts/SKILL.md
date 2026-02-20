---
name: validate-api-contracts
description: Verify API endpoints match OpenAPI schema using automated contract testing
version: 1.0.0
agent: python-backend-architect
type: validation
inputs:
  - api_base_url: Base URL of the API to test
  - openapi_schema_path: Path to OpenAPI schema file (openapi.json or openapi.yaml)
  - test_endpoints: List of endpoints to validate (optional, validates all if not specified)
outputs:
  - validation_report: API contract validation report with severity levels
  - contract_score: Overall contract compliance score (0-100)
  - schema_violations: List of endpoints violating OpenAPI schema
  - recommendations: Actionable contract improvements
reusability: extremely-high
framework_agnostic: yes
requires_context7: true
estimated_execution_time: 2-5 minutes
---

# Skill: validate-api-contracts

## 1. Purpose

This skill validates that API endpoints match their OpenAPI schema specification using automated contract testing. It ensures request/response models, status codes, and data types align with the OpenAPI schema across ANY Python backend framework (FastAPI, Flask, Django) and ANY domain.

**Core Objectives:**
- **Schema Compliance Validation**: Verify API responses match Pydantic/OpenAPI models
- **Request/Response Validation**: Ensure request bodies and response bodies conform to schema
- **Status Code Verification**: Validate HTTP status codes match documented responses
- **Data Type Enforcement**: Check that all fields match declared types (string, integer, array, object)
- **Required Field Validation**: Verify all required fields are present in responses
- **Framework/Domain Agnostic**: Works across FastAPI, Flask, Django, and all domains

**Why This Skill Exists:**

API contract violations lead to:
- **Client integration failures**: Clients receive unexpected response structures
- **Runtime errors**: Type mismatches cause crashes
- **Documentation drift**: OpenAPI docs don't match actual behavior
- **Breaking changes**: Unintentional API changes break consumers

This skill provides automated, repeatable validation to catch contract violations before deployment.

**Unlike manual API testing, this skill:**
- Uses **OpenAPI schema** as the source of truth
- Validates **Pydantic model alignment** (FastAPI) or schema definitions (Flask/Django)
- Checks **request and response** bodies, headers, status codes
- Identifies **schema drift** (implementation diverging from documentation)
- Generates **detailed violation reports** with remediation guidance
- Works across **all Python backends** (FastAPI, Flask, Django, Pyramid)

---

## 2. When to Use This Skill

### Mandatory Invocation Scenarios

**ALWAYS invoke this skill when:**

1. **Pre-Deployment Quality Gate** - Validate API contracts before production release
2. **After API Changes** - Verify endpoint modifications maintain schema compliance
3. **Pull Request Validation** - Block PRs with contract violations
4. **Post-Migration** - Ensure API migration didn't break contracts
5. **Periodic Audits** - Regular contract validation (weekly/sprint-based)

### Specific Trigger Conditions

Invoke immediately when code includes:

**FastAPI:**
- Route decorators (`@app.get`, `@app.post`, etc.)
- Pydantic model changes (`class TaskResponse(BaseModel)`)
- Response model declarations (`response_model=Task`)
- Status code declarations (`status_code=201`)

**Flask:**
- Route decorators (`@app.route`)
- Request/response schema definitions
- API Blueprint changes

**Django REST Framework:**
- ViewSet changes
- Serializer modifications
- API route configurations

### User-Requested Scenarios

Users may explicitly request:
- "Validate API contracts against OpenAPI schema"
- "Check if API responses match documentation"
- "Verify API endpoints follow schema"
- "Test API contract compliance"

---

## 3. Inputs

### Required Inputs

| Input | Type | Description | Example |
|-------|------|-------------|---------|
| `api_base_url` | `string` | Base URL of the running API | `"http://localhost:8000"` |
| `openapi_schema_path` | `string` | Path to OpenAPI schema file | `"openapi.json"` or `"/api/openapi.json"` (endpoint) |

### Optional Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `test_endpoints` | `string[]` | `[]` (all endpoints) | Specific endpoints to validate |
| `include_query_params` | `boolean` | `true` | Validate query parameter schemas |
| `include_request_bodies` | `boolean` | `true` | Validate request body schemas |
| `include_response_bodies` | `boolean` | `true` | Validate response body schemas |
| `strict_mode` | `boolean` | `false` | Fail on any schema violation (even minor) |
| `severity_threshold` | `"low" \| "medium" \| "high" \| "critical"` | `"medium"` | Minimum severity to report |

### Input Validation Rules

- `api_base_url` must be valid URL
- `openapi_schema_path` must exist (file path) or be accessible (URL endpoint)
- OpenAPI schema must be valid (OpenAPI 3.0+ format)

---

## 4. Outputs

### Validation Report Structure

```typescript
interface ContractValidationReport {
  summary: {
    total_endpoints: number;
    validated_endpoints: number;
    compliant_endpoints: number;
    violation_count: number;
    contract_score: number; // 0-100
    validation_timestamp: string;
    openapi_version: string;
  };

  schema_violations: SchemaViolation[];
  recommendations: Recommendation[];
  endpoint_results: EndpointValidationResult[];
}

interface SchemaViolation {
  severity: "critical" | "high" | "medium" | "low";
  endpoint: string;
  http_method: string;
  violation_type: string;
  expected_schema: object;
  actual_response: object;
  description: string;
  impact: string;
  remediation: string;
}

interface EndpointValidationResult {
  endpoint: string;
  http_method: string;
  status_code_tested: number;
  schema_compliant: boolean;
  violations: SchemaViolation[];
}
```

### Contract Score Calculation

```
Contract Score = (compliant_endpoints / total_endpoints) * 100

Blocking Threshold: < 80 (deployment blocked)
Warning Threshold: 80-95 (review required)
Excellent: > 95
```

---

## 5. Workflow

### Step 1: Context7 Integration - Fetch Latest OpenAPI Best Practices

**Purpose**: Ensure validation uses current OpenAPI 3.1 and framework-specific patterns.

**Actions**:

1. **Query Context7 MCP for OpenAPI Documentation**:
   ```typescript
   const context7Queries = [
     {
       libraryId: "/websites/fastapi_tiangolo",
       query: "OpenAPI schema generation Pydantic models automatic documentation response_model validation"
     },
     {
       libraryId: "/OAI/OpenAPI-Specification",
       query: "OpenAPI 3.1 specification schema components request response validation"
     },
     {
       libraryId: "/schemathesis/schemathesis",
       query: "API contract testing OpenAPI schema validation automated testing"
     }
   ];
   ```

2. **Extract Current Patterns**

**Key Patterns to Extract:**

**FastAPI OpenAPI Generation:**
```python
from fastapi import FastAPI
from pydantic import BaseModel

class TaskResponse(BaseModel):
    id: int
    title: str
    completed: bool

app = FastAPI()

@app.get("/tasks/{task_id}", response_model=TaskResponse, status_code=200)
async def get_task(task_id: int):
    return {"id": task_id, "title": "Buy milk", "completed": False}
```

**Generated OpenAPI Schema:**
```json
{
  "paths": {
    "/tasks/{task_id}": {
      "get": {
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {"$ref": "#/components/schemas/TaskResponse"}
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "TaskResponse": {
        "title": "TaskResponse",
        "required": ["id", "title", "completed"],
        "type": "object",
        "properties": {
          "id": {"title": "Id", "type": "integer"},
          "title": {"title": "Title", "type": "string"},
          "completed": {"title": "Completed", "type": "boolean"}
        }
      }
    }
  }
}
```

---

### Step 2: Load and Parse OpenAPI Schema

**Load Schema from File or Endpoint:**

```python
import json
import yaml
import requests

def load_openapi_schema(schema_path: str):
    # Option 1: Load from file
    if schema_path.endswith('.json'):
        with open(schema_path, 'r') as f:
            return json.load(f)
    elif schema_path.endswith(('.yaml', '.yml')):
        with open(schema_path, 'r') as f:
            return yaml.safe_load(f)

    # Option 2: Fetch from API endpoint (e.g., /openapi.json)
    elif schema_path.startswith('http'):
        response = requests.get(schema_path)
        return response.json()

    raise ValueError(f"Invalid schema path: {schema_path}")
```

**Extract Endpoint Definitions:**

```python
def extract_endpoints(openapi_schema):
    endpoints = []

    for path, methods in openapi_schema['paths'].items():
        for method, spec in methods.items():
            endpoints.append({
                'path': path,
                'method': method.upper(),
                'responses': spec.get('responses', {}),
                'request_body': spec.get('requestBody', {}),
                'parameters': spec.get('parameters', [])
            })

    return endpoints
```

---

### Step 3: Execute Contract Tests

**Test Each Endpoint Against Schema:**

**Using Schemathesis (Recommended):**
```python
import schemathesis

schema = schemathesis.from_uri("http://localhost:8000/openapi.json")

@schema.parametrize()
def test_api_contract(case):
    # Schemathesis automatically generates test cases from OpenAPI schema
    response = case.call()
    case.validate_response(response)
```

**Manual Contract Validation:**
```python
import requests
from jsonschema import validate, ValidationError

def validate_endpoint_contract(endpoint, base_url, openapi_schema):
    url = base_url + endpoint['path']
    method = endpoint['method']

    # Send request
    response = requests.request(method, url)

    # Get expected schema for status code
    status_code = str(response.status_code)
    expected_response = endpoint['responses'].get(status_code, {})

    if not expected_response:
        return {
            'compliant': False,
            'violation': f'Unexpected status code {status_code} not documented in OpenAPI schema'
        }

    # Extract schema reference
    content_type = 'application/json'
    schema_ref = expected_response['content'][content_type]['schema']['$ref']

    # Resolve schema reference (e.g., #/components/schemas/TaskResponse)
    schema_name = schema_ref.split('/')[-1]
    expected_schema = openapi_schema['components']['schemas'][schema_name]

    # Validate response body against schema
    try:
        validate(instance=response.json(), schema=expected_schema)
        return {'compliant': True, 'violation': None}
    except ValidationError as e:
        return {
            'compliant': False,
            'violation': f'Schema violation: {e.message}',
            'expected_schema': expected_schema,
            'actual_response': response.json()
        }
```

---

### Step 4: Identify Schema Violations

**Violation Types:**

| Violation Type | Severity | Example |
|----------------|----------|---------|
| **Missing Required Field** | Critical | Response missing `id` field documented as required |
| **Incorrect Data Type** | Critical | Field `completed` is string but schema expects boolean |
| **Undocumented Endpoint** | High | `/tasks/archive` endpoint exists but not in OpenAPI schema |
| **Undocumented Status Code** | High | Endpoint returns 404 but only 200/422 documented |
| **Extra Field in Response** | Medium | Response includes `created_at` not in schema |
| **Missing Optional Field** | Low | Optional field `description` not in response |

**Example Violation Detection:**

```python
def detect_violations(endpoint_results):
    violations = []

    for result in endpoint_results:
        if not result['compliant']:
            violation_type = classify_violation(result)

            violations.append({
                'severity': determine_severity(violation_type),
                'endpoint': result['endpoint'],
                'http_method': result['method'],
                'violation_type': violation_type,
                'expected_schema': result.get('expected_schema'),
                'actual_response': result.get('actual_response'),
                'description': result['violation'],
                'impact': describe_impact(violation_type),
                'remediation': generate_remediation(violation_type, result)
            })

    return violations
```

---

### Step 5: Generate Report

**Markdown Report Example**:

```markdown
# API Contract Validation Report

**Contract Score**: 92/100 ✅

## Summary
- **Total Endpoints**: 25
- **Compliant Endpoints**: 23
- **Violations**: 2
- **Critical Issues**: 1
- **High Severity**: 1

## Critical Violations

### 🔴 Missing Required Field in Response
**Endpoint**: `GET /tasks/{task_id}`
**Status Code**: 200
**Violation Type**: Missing required field

**Expected Schema**:
```json
{
  "type": "object",
  "required": ["id", "title", "completed"],
  "properties": {
    "id": {"type": "integer"},
    "title": {"type": "string"},
    "completed": {"type": "boolean"}
  }
}
```

**Actual Response**:
```json
{
  "id": 1,
  "title": "Buy milk"
  // Missing "completed" field
}
```

**Impact**: Clients expecting `completed` field will encounter runtime errors

**Remediation**:
```python
@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    return {
        "id": task_id,
        "title": "Buy milk",
        "completed": False  # ✅ Add missing field
    }
```

---

### 🔴 Incorrect Data Type
**Endpoint**: `POST /tasks`
**Status Code**: 201
**Violation Type**: Data type mismatch

**Expected**: `id` field should be `integer`
**Actual**: `id` field is `string` (`"1"` instead of `1`)

**Remediation**:
```python
# Ensure Pydantic model uses correct type
class TaskResponse(BaseModel):
    id: int  # ✅ Not str
    title: str
    completed: bool
```

## Deployment Recommendation
✅ **APPROVED** - Contract score 92/100 (above 80% threshold)
⚠️ **RECOMMENDED** - Address 1 critical violation before next release
```

---

## 6. Constraints & Limitations

**This skill validates:**
- Request/response schema compliance
- Status code alignment with OpenAPI spec
- Data types and required fields
- Query parameter schemas
- Path parameter validation

**This skill does NOT validate:**
- Business logic correctness
- Performance or latency
- Authentication/authorization (see `check-authorization-coverage`)
- Database integrity

---

## 7. Reusability & Extensibility

**Cross-Project Reusability: Extremely High**

Works across:
- **Any Python backend**: FastAPI, Flask, Django REST Framework, Pyramid
- **Any domain**: Todo, E-commerce, Healthcare, SaaS
- **Any OpenAPI version**: 3.0, 3.1

**CI/CD Integration Example**:
```yaml
# GitHub Actions
- name: Validate API Contracts
  run: |
    # Start API server
    uvicorn main:app --host 0.0.0.0 --port 8000 &
    sleep 5

    # Run contract validation
    schemathesis run http://localhost:8000/openapi.json --checks all --base-url http://localhost:8000
```

---

## 8. Integration Points

**Agent Integration**: Owned by `python-backend-architect` (Operational Agent)

**Blocking Authority**:
- Backend Architect has **NO** blocking authority by default
- Integration Orchestrator can block if contract score < 80%

**Multi-Agent Coordination**:
- **Domain Guardian**: Backend Architect ensures response models align with domain entities
- **Integration Orchestrator**: Runs this skill as part of pre-deployment validation
- **Test Strategy Architect**: Contract tests count toward integration test coverage

---

## Appendix: Tools Reference

### Schemathesis (Recommended)

**Installation**:
```bash
pip install schemathesis
```

**CLI Usage**:
```bash
schemathesis run http://localhost:8000/openapi.json \
  --checks all \
  --base-url http://localhost:8000 \
  --hypothesis-max-examples=50
```

**Python Usage**:
```python
import schemathesis

schema = schemathesis.from_uri("http://localhost:8000/openapi.json")

@schema.parametrize()
def test_api(case):
    response = case.call()
    case.validate_response(response)
```

### Alternative: Dredd

```bash
npm install -g dredd
dredd openapi.yaml http://localhost:8000
```

---

**End of Skill Definition**
