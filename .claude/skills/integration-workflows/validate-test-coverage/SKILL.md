---
name: validate-test-coverage
description: Validate test coverage against minimum thresholds using pytest-cov and coverage.py
version: 1.0.0
agent: integration-orchestrator
type: validation
inputs:
  - test_paths: Array of test directory paths
  - source_paths: Array of source code paths to measure coverage
  - coverage_thresholds: Minimum coverage percentages (line, branch)
outputs:
  - coverage_report: Test coverage validation report with severity levels
  - coverage_score: Overall coverage score (0-100)
  - critical_issues: List of blocking coverage violations
  - uncovered_critical_paths: Critical code paths lacking tests
  - recommendations: Actionable coverage improvements
reusability: extremely-high
framework_agnostic: yes
requires_context7: true
estimated_execution_time: 1-3 minutes
---

# Skill: validate-test-coverage

## 1. Purpose

This skill validates test coverage against minimum quality thresholds using industry-standard tools (pytest-cov, coverage.py). It automates coverage analysis, identifies critical paths lacking tests, and enforces coverage requirements before deployment across ANY Python project and ANY domain.

**Core Objectives:**
- **Automated Coverage Analysis**: Run pytest-cov/coverage.py to measure line and branch coverage
- **Threshold Enforcement**: Validate coverage meets minimum requirements (e.g., 80% line, 70% branch)
- **Critical Path Identification**: Detect untested critical code (domain entities, API endpoints, core business logic)
- **Multi-Format Reporting**: Generate JSON, XML, HTML, and terminal reports
- **CI/CD Integration**: Block deployments if coverage below thresholds
- **Framework/Domain Agnostic**: Works across all Python projects (Flask, FastAPI, Django, etc.) and domains

**Why This Skill Exists:**

Test coverage is a **critical quality metric** that indicates how thoroughly code is tested. Insufficient coverage leads to:
- **Undetected bugs**: Critical paths without tests ship to production
- **Regression risks**: Changes break untested code paths
- **Maintenance nightmares**: Developers fear refactoring untested code
- **Technical debt**: Coverage gaps accumulate over time

This skill provides automated, repeatable validation to enforce coverage standards before deployment.

**Unlike manual coverage reviews, this skill:**
- Uses **pytest-cov and coverage.py** (industry-standard Python coverage tools)
- Validates **branch coverage** in addition to line coverage (catches untested conditional logic)
- Identifies **critical untested paths** (domain models, API endpoints, core services)
- Enforces **configurable thresholds** (80% line, 70% branch, custom per-project)
- Generates **multi-format reports** (JSON for CI/CD, HTML for developers, terminal for quick checks)
- Works across **all Python frameworks** and **all domains**

---

## 2. When to Use This Skill

### Mandatory Invocation Scenarios

**ALWAYS invoke this skill when:**

1. **Pre-Deployment Quality Gate** - Validate coverage before production release
2. **After Feature Implementation** - Ensure new features are adequately tested
3. **Pull Request Validation** - Block PRs with insufficient test coverage
4. **Periodic Audits** - Regular coverage reviews (weekly/sprint-based)
5. **Post-Refactoring** - Verify refactoring didn't reduce coverage

### Specific Trigger Conditions

Invoke immediately when:

**New Code Added:**
- New domain entities, value objects, aggregates
- New API endpoints or route handlers
- New business logic services
- New database repositories or queries

**Refactoring:**
- Code refactoring completed (verify coverage maintained)
- Test refactoring completed (verify coverage preserved)

**CI/CD Pipeline:**
- Pre-merge quality gate in pull request workflow
- Pre-deployment validation in release pipeline
- Scheduled coverage audits (nightly builds)

### User-Requested Scenarios

Users may explicitly request:
- "Validate test coverage before deployment"
- "Check if coverage meets 80% threshold"
- "Identify untested critical code"
- "Generate coverage report for code review"

---

## 3. Inputs

### Required Inputs

| Input | Type | Description | Example |
|-------|------|-------------|---------|
| `test_paths` | `string[]` | Absolute paths to test directories | `["tests/", "src/*/tests/"]` |
| `source_paths` | `string[]` | Absolute paths to source code to measure | `["src/", "backend/"]` |
| `coverage_thresholds` | `object` | Minimum coverage percentages | `{"line": 80, "branch": 70}` |

### Optional Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `critical_paths` | `string[]` | `["domain/", "api/", "services/"]` | Paths to code requiring 100% coverage |
| `omit_paths` | `string[]` | `["*/tests/*", "*/migrations/*"]` | Paths to exclude from coverage |
| `report_formats` | `string[]` | `["term-missing", "json", "html"]` | Report formats to generate |
| `fail_under_line` | `number` | `80` | Minimum line coverage percentage |
| `fail_under_branch` | `number` | `70` | Minimum branch coverage percentage |
| `severity_threshold` | `"low" \| "medium" \| "high" \| "critical"` | `"medium"` | Minimum severity to report |

### Input Validation Rules

- `test_paths` must be non-empty array
- `source_paths` must be non-empty array
- Each path must exist and be readable
- `fail_under_line` must be 0-100
- `fail_under_branch` must be 0-100
- `coverage_thresholds.line` must be 0-100
- `coverage_thresholds.branch` must be 0-100

---

## 4. Outputs

### Validation Report Structure

```typescript
interface CoverageReport {
  summary: {
    total_lines: number;
    covered_lines: number;
    line_coverage_percent: number;
    total_branches: number;
    covered_branches: number;
    branch_coverage_percent: number;
    total_files: number;
    coverage_score: number; // 0-100 (weighted: 60% line + 40% branch)
    validation_timestamp: string;
    pytest_cov_version: string;
  };

  thresholds: {
    line_threshold: number;
    branch_threshold: number;
    line_pass: boolean;
    branch_pass: boolean;
  };

  critical_issues: CoverageIssue[];
  high_severity_issues: CoverageIssue[];
  medium_severity_issues: CoverageIssue[];
  low_severity_issues: CoverageIssue[];

  uncovered_critical_paths: UncoveredPath[];
  recommendations: Recommendation[];
  files_analyzed: FileCoverage[];
}

interface CoverageIssue {
  severity: "critical" | "high" | "medium" | "low";
  category: "domain" | "api" | "service" | "infrastructure" | "overall";
  issue_type: string;
  file: string;
  line_coverage: number;
  branch_coverage: number;
  missing_lines: number[];
  missing_branches: string[];
  description: string;
  impact: string;
  remediation: string;
}

interface UncoveredPath {
  path: string;
  type: "domain_entity" | "api_endpoint" | "service" | "repository";
  line_coverage: number;
  branch_coverage: number;
  priority: "critical" | "high" | "medium";
  suggested_tests: string[];
}
```

### Coverage Score Calculation

```
Coverage Score = (line_coverage_percent * 0.6) + (branch_coverage_percent * 0.4)

Blocking Threshold: < 70 (deployment blocked)
Warning Threshold: 70-80 (review required)
Good: 80-90
Excellent: > 90
```

**Rationale**:
- Line coverage weighted 60% (measures statement execution)
- Branch coverage weighted 40% (measures decision path coverage)
- Branch coverage catches untested conditional logic (if/else, try/except, loops)

---

## 5. Workflow

### Step 1: Context7 Integration - Fetch Latest Coverage Tool Documentation

**Purpose**: Ensure validation uses current pytest-cov and coverage.py patterns.

**Actions**:

1. **Query Context7 MCP for Coverage Tool Documentation**:
   ```typescript
   const context7Queries = [
     {
       libraryId: "/pytest-dev/pytest-cov",
       query: "pytest-cov coverage threshold enforcement minimum coverage fail-under configuration line coverage branch coverage reports"
     },
     {
       libraryId: "/nedbat/coveragepy",
       query: "coverage.py configuration line coverage branch coverage threshold fail_under coverage reports HTML JSON XML"
     },
     {
       libraryId: "/websites/pytest_en_stable",
       query: "pytest test coverage integration best practices test organization critical path testing"
     }
   ];
   ```

2. **Extract Current Tool Patterns**
3. **Build Reference Configuration Templates**

**Key Patterns to Extract:**

**pytest-cov Configuration:**
```bash
# Command-line enforcement
pytest --cov=src --cov-branch --cov-fail-under=80 --cov-report=term-missing tests/
```

**pyproject.toml Configuration:**
```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=json:coverage.json",
    "--cov-branch",
    "--cov-fail-under=80",
]

[tool.coverage.run]
branch = true
source = ["src"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
precision = 2
show_missing = true
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]

[tool.coverage.html]
directory = "htmlcov"

[tool.coverage.json]
output = "coverage.json"
pretty_print = true
```

**coverage.py Direct Usage:**
```bash
# Run coverage and generate reports
coverage run -m pytest tests/
coverage report --fail-under=80
coverage json -o coverage.json --pretty-print
coverage html -d htmlcov
coverage xml -o coverage.xml
```

---

### Step 2: Coverage Analysis Execution

**Run pytest-cov with configured thresholds:**

**Option 1: pytest-cov (Recommended)**
```bash
pytest \
  --cov=src \
  --cov=backend \
  --cov-branch \
  --cov-fail-under=80 \
  --cov-report=term-missing \
  --cov-report=json:coverage.json \
  --cov-report=html:htmlcov \
  tests/
```

**Option 2: coverage.py**
```bash
coverage run --source=src,backend --branch -m pytest tests/
coverage report --fail-under=80 --show-missing
coverage json -o coverage.json --pretty-print
coverage html -d htmlcov
```

**Parse Coverage Reports:**

**JSON Report Structure (coverage.json):**
```json
{
  "meta": {
    "version": "7.6.0",
    "timestamp": "2026-01-08T10:30:00",
    "branch_coverage": true,
    "show_contexts": false
  },
  "files": {
    "src/domain/task.py": {
      "executed_lines": [1, 2, 5, 8, 10, 15, 20],
      "missing_lines": [25, 30],
      "excluded_lines": [],
      "summary": {
        "covered_lines": 7,
        "num_statements": 9,
        "percent_covered": 77.78,
        "missing_lines": 2,
        "covered_branches": 4,
        "num_branches": 6,
        "num_partial_branches": 2,
        "percent_covered_display": "77.78"
      }
    }
  },
  "totals": {
    "covered_lines": 450,
    "num_statements": 500,
    "percent_covered": 90.0,
    "missing_lines": 50,
    "covered_branches": 85,
    "num_branches": 100,
    "num_partial_branches": 15,
    "percent_covered_display": "90"
  }
}
```

---

### Step 3: Critical Path Identification

**Identify Untested Critical Code:**

**Domain Layer (Highest Priority - Require 100% Coverage):**
- Domain entities (e.g., `Task`, `User`)
- Value objects (e.g., `Email`, `TaskTitle`)
- Domain services (e.g., `TaskPriorityService`)
- Aggregates and aggregate roots

**API Layer (High Priority - Require 90%+ Coverage):**
- API route handlers (`/api/tasks`, `/api/users`)
- Request/response validation
- Authentication/authorization middleware

**Service Layer (High Priority - Require 85%+ Coverage):**
- Application services (e.g., `TaskService`, `UserService`)
- Use case orchestration
- Transaction boundaries

**Repository Layer (Medium Priority - Require 80%+ Coverage):**
- Database repository implementations
- Query builders
- Data access logic

**Critical Path Detection Algorithm:**
```python
def identify_uncovered_critical_paths(coverage_data, critical_paths_config):
    uncovered = []

    for file_path, coverage_info in coverage_data['files'].items():
        # Check if file is in critical paths
        for critical_path in critical_paths_config:
            if critical_path in file_path:
                # Determine priority based on path
                if 'domain/' in file_path:
                    priority = 'critical'
                    threshold = 100
                elif 'api/' in file_path or 'services/' in file_path:
                    priority = 'high'
                    threshold = 90
                elif 'repositories/' in file_path:
                    priority = 'medium'
                    threshold = 80
                else:
                    continue

                # Check if coverage below threshold
                line_cov = coverage_info['summary']['percent_covered']
                branch_cov = (coverage_info['summary']['covered_branches'] /
                             coverage_info['summary']['num_branches'] * 100
                             if coverage_info['summary']['num_branches'] > 0 else 100)

                if line_cov < threshold or branch_cov < threshold:
                    uncovered.append({
                        'path': file_path,
                        'type': detect_type(file_path),
                        'line_coverage': line_cov,
                        'branch_coverage': branch_cov,
                        'priority': priority,
                        'missing_lines': coverage_info['missing_lines'],
                        'suggested_tests': generate_test_suggestions(file_path)
                    })

    return uncovered
```

---

### Step 4: Threshold Validation & Issue Classification

**Severity Classification:**

| Severity | Condition |
|----------|-----------|
| **Critical** | Domain entities < 100% coverage OR Overall coverage < 70% |
| **High** | API endpoints < 90% coverage OR Critical services < 85% coverage OR Overall coverage 70-80% |
| **Medium** | Repository < 80% coverage OR Overall coverage 80-90% |
| **Low** | Non-critical files < 80% coverage OR Overall coverage > 90% |

**Example Issue Detection:**

```python
def classify_coverage_issues(coverage_data, thresholds):
    issues = {
        'critical': [],
        'high': [],
        'medium': [],
        'low': []
    }

    # Check overall coverage
    overall_line = coverage_data['totals']['percent_covered']
    overall_branch = (coverage_data['totals']['covered_branches'] /
                     coverage_data['totals']['num_branches'] * 100)

    if overall_line < 70 or overall_branch < 60:
        issues['critical'].append({
            'issue_type': 'insufficient_overall_coverage',
            'description': f'Overall coverage ({overall_line:.2f}% line, {overall_branch:.2f}% branch) below minimum (70% line, 60% branch)',
            'impact': 'High risk of untested code in production',
            'remediation': 'Add tests to increase overall coverage above 70%'
        })

    # Check per-file coverage
    for file_path, file_cov in coverage_data['files'].items():
        line_cov = file_cov['summary']['percent_covered']

        if 'domain/' in file_path and line_cov < 100:
            issues['critical'].append({
                'file': file_path,
                'line_coverage': line_cov,
                'missing_lines': file_cov['missing_lines'],
                'issue_type': 'domain_entity_untested',
                'description': f'Domain entity has {100 - line_cov:.2f}% uncovered lines',
                'impact': 'Core business logic untested - high risk of domain bugs',
                'remediation': 'Add unit tests for all domain entity methods and invariants'
            })

        if 'api/' in file_path and line_cov < 90:
            issues['high'].append({
                'file': file_path,
                'line_coverage': line_cov,
                'issue_type': 'api_endpoint_untested',
                'description': f'API endpoint has {90 - line_cov:.2f}% coverage gap',
                'impact': 'API behavior not fully tested - risk of runtime errors',
                'remediation': 'Add integration tests for all API endpoints and error paths'
            })

    return issues
```

---

### Step 5: Generate Report

**Markdown Report Example**:

```markdown
# Test Coverage Validation Report

**Coverage Score**: 87/100 ✅

## Summary
- **Line Coverage**: 88.5% (443/500 lines) ✅
- **Branch Coverage**: 84.2% (85/101 branches) ✅
- **Files Analyzed**: 45
- **Critical Issues**: 0
- **High Severity**: 2
- **Medium Severity**: 4

## Thresholds
- Line Coverage Threshold: 80% ✅ PASS (88.5%)
- Branch Coverage Threshold: 70% ✅ PASS (84.2%)

## High Severity Issues

### 🔴 API Endpoint Insufficiently Tested
**File**: `src/backend/api/tasks.py:45-67`
**Category**: API
**Line Coverage**: 75.0% (15/20 lines)
**Branch Coverage**: 66.7% (4/6 branches)
**Impact**: Task creation endpoint has untested error paths

**Missing Coverage**:
- Lines: 55, 58, 62, 65, 67
- Branches: Error handling for invalid task title, duplicate task detection

**Remediation**:
```python
# Add integration tests for error cases
def test_create_task_with_invalid_title():
    response = client.post('/api/tasks', json={'title': ''})
    assert response.status_code == 400
    assert 'title' in response.json()['error']

def test_create_task_duplicate_title():
    client.post('/api/tasks', json={'title': 'Buy milk'})
    response = client.post('/api/tasks', json={'title': 'Buy milk'})
    assert response.status_code == 409
```

---

### 🔴 Service Layer Branch Coverage Gap
**File**: `src/backend/services/task_service.py:30-45`
**Category**: Service
**Line Coverage**: 90.0% (18/20 lines)
**Branch Coverage**: 60.0% (3/5 branches)
**Impact**: Task priority validation has untested branches

**Missing Branches**:
- Priority validation: HIGH priority edge case not tested
- Error handling: Domain error propagation not tested

**Remediation**:
```python
def test_task_service_high_priority_validation():
    service = TaskService()
    task = service.create_task(title="Urgent", priority="HIGH")
    assert task.priority == Priority.HIGH

def test_task_service_domain_error_propagation():
    service = TaskService()
    with pytest.raises(TaskValidationError):
        service.create_task(title="", priority="LOW")
```

## Uncovered Critical Paths

### Domain Entity: Task
**File**: `src/domain/task.py`
**Line Coverage**: 95.0% ⚠️ (Below 100% requirement for domain)
**Branch Coverage**: 90.0%
**Priority**: Critical

**Missing Lines**: 78, 82 (validation edge cases)

**Suggested Tests**:
```python
def test_task_title_max_length_boundary():
    # Test title at exactly 200 characters (max length)
    title = "a" * 200
    task = Task(title=title)
    assert len(task.title) == 200

def test_task_title_exceeds_max_length():
    # Test title exceeding max length raises error
    title = "a" * 201
    with pytest.raises(TaskTitleTooLongError):
        Task(title=title)
```

## Recommendations

### 1. Increase Domain Entity Coverage to 100%
**Current**: 95.0%
**Target**: 100.0%
**Files**: `src/domain/task.py`, `src/domain/user.py`
**Effort**: Low (2-3 tests needed)

### 2. Add Integration Tests for API Error Paths
**Current**: 75.0%
**Target**: 90.0%
**Files**: `src/backend/api/tasks.py`, `src/backend/api/users.py`
**Effort**: Medium (10-15 tests needed)

### 3. Improve Branch Coverage for Service Layer
**Current**: 84.2%
**Target**: 90.0%
**Files**: `src/backend/services/*.py`
**Effort**: Medium (8-10 tests for untested branches)

## Deployment Recommendation
✅ **APPROVED** - Coverage meets thresholds (88.5% line, 84.2% branch)
⚠️ **RECOMMENDED** - Address 2 high-severity issues before next release
```

---

## 6. Constraints & Limitations

**This skill validates:**
- Line coverage (statement execution)
- Branch coverage (decision path coverage)
- Coverage thresholds (configurable minimums)
- Critical path coverage (domain, API, services)
- Multi-format report generation

**This skill does NOT validate:**
- Test quality (can have 100% coverage with poor tests)
- Mutation testing (whether tests actually catch bugs)
- Test execution time or performance
- Test maintainability or readability

---

## 7. Reusability & Extensibility

**Cross-Project Reusability: Extremely High**

Works across:
- **Any Python framework**: Flask, FastAPI, Django, Pyramid, Tornado
- **Any testing framework**: pytest, unittest, nose2
- **Any domain**: Todo, E-commerce, Healthcare, SaaS, FinTech
- **Any Python version**: Python 3.8+

**CI/CD Integration Example**:
```yaml
# GitHub Actions
name: Coverage Validation
on: [pull_request]
jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov coverage
          pip install -r requirements.txt
      - name: Run coverage validation
        run: |
          pytest --cov=src --cov-branch --cov-fail-under=80 --cov-report=json:coverage.json tests/
      - name: Upload coverage report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: coverage.json
```

**Pre-commit Hook Example**:
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running test coverage validation..."
pytest --cov=src --cov-branch --cov-fail-under=80 --cov-report=term-missing tests/

if [ $? -ne 0 ]; then
    echo "❌ Coverage below 80% - commit blocked"
    exit 1
fi

echo "✅ Coverage validation passed"
```

---

## 8. Integration Points

**Agent Integration**: Owned by `integration-orchestrator` (Operational Agent)

**Blocking Authority**:
- Integration Orchestrator has **YES** blocking authority for coverage violations
- If overall coverage < 70%, Integration Orchestrator **MUST** block deployment
- If critical paths < required coverage, Integration Orchestrator **MUST** block
- High-severity issues trigger **WARN** (user discretion)

**Multi-Agent Coordination**:
- **Test Strategy Architect**: Integration Orchestrator enforces coverage thresholds defined by Test Strategy Architect
- **Domain Guardian**: Integration Orchestrator validates domain entities have 100% coverage
- **Backend Architect**: Integration Orchestrator validates API/service layer coverage
- **Frontend Architect**: Integration Orchestrator can extend to JavaScript/TypeScript coverage (future)

---

## Appendix: Pattern Reference

### Coverage Best Practices

| Practice | Rationale |
|----------|-----------|
| Domain entities: 100% coverage | Core business logic must be fully tested |
| API endpoints: 90%+ coverage | Public interfaces require thorough testing |
| Service layer: 85%+ coverage | Orchestration logic needs comprehensive tests |
| Branch coverage enabled | Catches untested conditional logic |
| Exclude test files from coverage | Avoid inflated coverage metrics |
| Exclude migrations from coverage | Database migrations are not business logic |

### Coverage Thresholds by Layer

| Layer | Line Coverage | Branch Coverage | Justification |
|-------|---------------|-----------------|---------------|
| **Domain** | 100% | 100% | Core business logic - no untested paths |
| **API** | 90% | 85% | Public interfaces - high test requirement |
| **Service** | 85% | 80% | Orchestration - moderate test requirement |
| **Repository** | 80% | 75% | Data access - lower complexity |
| **Infrastructure** | 70% | 65% | Framework wrappers - lower priority |

### pytest-cov Configuration Reference

```toml
# pyproject.toml - Full configuration example
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=src",
    "--cov=backend",
    "--cov-branch",
    "--cov-report=term-missing:skip-covered",
    "--cov-report=html:htmlcov",
    "--cov-report=json:coverage.json",
    "--cov-report=xml:coverage.xml",
    "--cov-fail-under=80",
]

[tool.coverage.run]
branch = true
source = ["src", "backend"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*_test.py",
    "*/migrations/*",
    "*/__pycache__/*",
    "*/site-packages/*",
    "*/.venv/*",
]
parallel = true

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
skip_empty = true
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "def __str__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
    "@overload",
    "\\.\\.\\.",
]

[tool.coverage.html]
directory = "htmlcov"
show_contexts = true

[tool.coverage.json]
output = "coverage.json"
pretty_print = true
show_contexts = true

[tool.coverage.xml]
output = "coverage.xml"
```

---

**End of Skill Definition**
