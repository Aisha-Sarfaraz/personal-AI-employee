---
name: generate-api-documentation
description: Auto-generate comprehensive API documentation from route definitions and Pydantic models
version: 1.0.0
agent: python-backend-architect
type: generation
inputs:
  - source_paths: Array of source code paths containing API routes
  - output_format: Documentation format (openapi-json, openapi-yaml, markdown, html)
  - include_examples: Whether to include request/response examples
outputs:
  - documentation_files: Generated documentation file paths
  - openapi_schema: OpenAPI 3.1 schema (if openapi format selected)
  - documentation_url: URL to interactive documentation (if server started)
reusability: extremely-high
framework_agnostic: yes
requires_context7: true
estimated_execution_time: 1-2 minutes
---

# Skill: generate-api-documentation

## 1. Purpose

This skill auto-generates comprehensive API documentation from route definitions, Pydantic models, and OpenAPI schemas. It eliminates manual documentation maintenance by extracting documentation directly from code across ANY Python backend framework (FastAPI, Flask, Django) and ANY domain.

**Core Objectives:**
- **Automatic OpenAPI Generation**: Extract OpenAPI 3.1 schema from route definitions
- **Interactive Documentation**: Generate Swagger UI and ReDoc interfaces
- **Markdown Export**: Create human-readable Markdown documentation
- **Code Example Generation**: Auto-generate request/response examples from Pydantic models
- **Documentation Sync**: Ensure docs always match implementation (no drift)
- **Framework/Domain Agnostic**: Works across FastAPI, Flask, Django, and all domains

**Why This Skill Exists:**

Manual API documentation suffers from:
- **Documentation drift**: Docs become outdated as code changes
- **Maintenance burden**: Developers must manually update docs
- **Inconsistency**: Different endpoints documented in different styles
- **Missing information**: Developers forget to document edge cases

This skill provides automated, repeatable documentation generation synchronized with code.

**Unlike manual documentation, this skill:**
- **Extracts from code**: Uses Pydantic models, type hints, docstrings as source of truth
- **Auto-generates OpenAPI**: Creates valid OpenAPI 3.1 schemas automatically
- **Multiple formats**: Exports to JSON, YAML, Markdown, HTML, Swagger UI, ReDoc
- **Request/response examples**: Generates realistic examples from model definitions
- **Always in sync**: Re-run after code changes to update docs
- Works across **all Python backends** (FastAPI has built-in support, Flask/Django via extensions)

---

## 2. When to Use This Skill

### Mandatory Invocation Scenarios

**ALWAYS invoke this skill when:**

1. **After API Changes** - Regenerate docs when endpoints modified
2. **Pre-Deployment** - Ensure docs match current implementation
3. **Pull Request Validation** - Verify documentation is up-to-date
4. **API Versioning** - Generate docs for new API version
5. **Client SDK Generation** - Export OpenAPI for client generator tools

### Specific Trigger Conditions

Invoke immediately when code includes:

**FastAPI:**
- New route decorators (`@app.get`, `@app.post`)
- Pydantic model changes
- Response model updates (`response_model=Task`)
- Endpoint descriptions updated

**Flask:**
- New Blueprint routes
- API endpoint additions
- Schema definition changes

**Django REST Framework:**
- New ViewSet definitions
- Serializer modifications

### User-Requested Scenarios

Users may explicitly request:
- "Generate API documentation"
- "Update OpenAPI schema"
- "Export API docs to Markdown"
- "Create Swagger UI documentation"

---

## 3. Inputs

### Required Inputs

| Input | Type | Description | Example |
|-------|------|-------------|---------|
| `source_paths` | `string[]` | Paths to source code containing API routes | `["src/backend/api/", "src/main.py"]` |
| `output_format` | `string` | Documentation format to generate | `"openapi-json"`, `"openapi-yaml"`, `"markdown"`, `"html"` |

### Optional Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `include_examples` | `boolean` | `true` | Generate request/response examples |
| `output_path` | `string` | `"docs/"` | Directory to write generated docs |
| `api_title` | `string` | Auto-detect | API title for documentation |
| `api_version` | `string` | `"1.0.0"` | API version number |
| `api_description` | `string` | Auto-detect | API description text |
| `server_url` | `string` | `"http://localhost:8000"` | Base URL for API server |
| `interactive_docs` | `boolean` | `false` | Start local server for Swagger UI/ReDoc |

### Input Validation Rules

- `source_paths` must be non-empty array
- Each path must exist
- `output_format` must be valid format

---

## 4. Outputs

### Generated Documentation Files

**OpenAPI JSON (`openapi.json`):**
```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Todo API",
    "version": "1.0.0",
    "description": "API for managing tasks"
  },
  "paths": {
    "/tasks": {
      "get": {
        "summary": "List all tasks",
        "responses": {
          "200": {
            "description": "Successful Response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "array",
                  "items": {"$ref": "#/components/schemas/TaskResponse"}
                }
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
          "id": {"type": "integer", "example": 1},
          "title": {"type": "string", "example": "Buy milk"},
          "completed": {"type": "boolean", "example": false}
        }
      }
    }
  }
}
```

**Markdown (`API.md`):**
```markdown
# Todo API

Version: 1.0.0

API for managing tasks

## Endpoints

### GET /tasks

List all tasks

**Response (200 OK)**:
```json
[
  {
    "id": 1,
    "title": "Buy milk",
    "completed": false
  }
]
```

**Response Schema**: `TaskResponse[]`

### POST /tasks

Create a new task

**Request Body**:
```json
{
  "title": "Buy milk",
  "completed": false
}
```

**Response (201 Created)**:
```json
{
  "id": 1,
  "title": "Buy milk",
  "completed": false
}
```
```

---

## 5. Workflow

### Step 1: Context7 Integration - Fetch Latest Documentation Patterns

**Purpose**: Ensure generation uses current OpenAPI 3.1 and framework best practices.

**Actions**:

1. **Query Context7 MCP for Documentation Patterns**:
   ```typescript
   const context7Queries = [
     {
       libraryId: "/websites/fastapi_tiangolo",
       query: "OpenAPI automatic documentation generation Swagger UI ReDoc metadata tags description"
     },
     {
       libraryId: "/OAI/OpenAPI-Specification",
       query: "OpenAPI 3.1 specification info object paths components schemas examples"
     }
   ];
   ```

**Key Patterns to Extract:**

**FastAPI Auto-Documentation:**
```python
from fastapi import FastAPI
from pydantic import BaseModel

class TaskCreate(BaseModel):
    title: str
    completed: bool = False

class TaskResponse(BaseModel):
    id: int
    title: str
    completed: bool

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Buy milk",
                "completed": False
            }
        }

app = FastAPI(
    title="Todo API",
    version="1.0.0",
    description="API for managing tasks",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)

@app.post("/tasks", response_model=TaskResponse, status_code=201, tags=["tasks"])
async def create_task(task: TaskCreate):
    """
    Create a new task.

    - **title**: Task title (required)
    - **completed**: Task completion status (default: false)
    """
    return {"id": 1, "title": task.title, "completed": task.completed}
```

**FastAPI automatically generates:**
- OpenAPI schema at `/openapi.json`
- Swagger UI at `/docs`
- ReDoc at `/redoc`

---

### Step 2: Extract OpenAPI Schema

**FastAPI (Built-in):**
```python
from fastapi import FastAPI

app = FastAPI()

# Get OpenAPI schema programmatically
openapi_schema = app.openapi()

import json
with open('openapi.json', 'w') as f:
    json.dump(openapi_schema, f, indent=2)
```

**Flask (Using flask-openapi3):**
```python
from flask_openapi3 import OpenAPI

app = OpenAPI(__name__, info={"title": "Todo API", "version": "1.0.0"})

# Generate OpenAPI schema
openapi_schema = app.api_doc

import json
with open('openapi.json', 'w') as f:
    json.dump(openapi_schema, f, indent=2)
```

**Django REST Framework (Using drf-spectacular):**
```python
from drf_spectacular.generators import SchemaGenerator

generator = SchemaGenerator(title='Todo API', version='1.0.0')
schema = generator.get_schema(request=None, public=True)

import json
with open('openapi.json', 'w') as f:
    json.dump(schema, f, indent=2)
```

---

### Step 3: Generate Multiple Documentation Formats

**OpenAPI JSON:**
```python
import json

with open('docs/openapi.json', 'w') as f:
    json.dump(openapi_schema, f, indent=2)
```

**OpenAPI YAML:**
```python
import yaml

with open('docs/openapi.yaml', 'w') as f:
    yaml.dump(openapi_schema, f, sort_keys=False)
```

**Markdown:**
```python
def generate_markdown_docs(openapi_schema):
    md = f"# {openapi_schema['info']['title']}\n\n"
    md += f"Version: {openapi_schema['info']['version']}\n\n"
    md += f"{openapi_schema['info']['description']}\n\n"
    md += "## Endpoints\n\n"

    for path, methods in openapi_schema['paths'].items():
        for method, spec in methods.items():
            md += f"### {method.upper()} {path}\n\n"
            md += f"{spec.get('summary', 'No description')}\n\n"

            # Add request body example
            if 'requestBody' in spec:
                md += "**Request Body**:\n```json\n"
                md += json.dumps(get_example(spec['requestBody']), indent=2)
                md += "\n```\n\n"

            # Add response examples
            for status, response in spec.get('responses', {}).items():
                md += f"**Response ({status})**:\n```json\n"
                md += json.dumps(get_example(response), indent=2)
                md += "\n```\n\n"

    return md

markdown_docs = generate_markdown_docs(openapi_schema)
with open('docs/API.md', 'w') as f:
    f.write(markdown_docs)
```

**HTML (Standalone Swagger UI):**
```python
html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{openapi_schema['info']['title']}</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {{
            SwaggerUIBundle({{
                spec: {json.dumps(openapi_schema)},
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ]
            }})
        }}
    </script>
</body>
</html>
"""

with open('docs/index.html', 'w') as f:
    f.write(html_template)
```

---

### Step 4: Add Request/Response Examples

**Extract Examples from Pydantic Models:**
```python
class TaskResponse(BaseModel):
    id: int
    title: str
    completed: bool

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "Buy milk",
                "completed": False
            }
        }
```

**Auto-Generate Examples if Missing:**
```python
from pydantic import BaseModel

def generate_example_from_model(model: type[BaseModel]):
    example = {}

    for field_name, field in model.model_fields.items():
        if field.annotation == int:
            example[field_name] = 1
        elif field.annotation == str:
            example[field_name] = f"example_{field_name}"
        elif field.annotation == bool:
            example[field_name] = False
        elif field.annotation == list:
            example[field_name] = []

    return example
```

---

### Step 5: Start Interactive Documentation Server (Optional)

**Start Local Server:**
```python
import uvicorn
import webbrowser

# Start FastAPI server
uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

# Open Swagger UI in browser
webbrowser.open("http://localhost:8000/docs")
```

**Output:**
```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

✅ Interactive documentation available at:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - OpenAPI Schema: http://localhost:8000/openapi.json
```

---

## 6. Constraints & Limitations

**This skill generates:**
- OpenAPI schemas (JSON, YAML)
- Markdown documentation
- HTML documentation
- Interactive Swagger UI / ReDoc

**This skill does NOT generate:**
- Client SDKs (use OpenAPI Generator separately)
- Postman collections (use openapi-to-postman converter)
- GraphQL schemas
- gRPC documentation

---

## 7. Reusability & Extensibility

**Cross-Project Reusability: Extremely High**

Works across:
- **Any Python backend**: FastAPI (built-in), Flask (flask-openapi3), Django (drf-spectacular)
- **Any domain**: Todo, E-commerce, Healthcare, SaaS
- **Any OpenAPI version**: 3.0, 3.1

**CI/CD Integration Example**:
```yaml
# GitHub Actions
- name: Generate API Documentation
  run: |
    python scripts/generate_docs.py --format all --output docs/

- name: Deploy Documentation
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./docs
```

**Pre-commit Hook:**
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Regenerating API documentation..."
python scripts/generate_docs.py --format openapi-json

git add docs/openapi.json
```

---

## 8. Integration Points

**Agent Integration**: Owned by `python-backend-architect` (Operational Agent)

**Multi-Agent Coordination**:
- **Integration Orchestrator**: Runs this skill during pre-deployment workflow
- **Frontend Architect**: Uses generated OpenAPI schema for TypeScript client generation
- **Test Strategy Architect**: Uses OpenAPI schema for contract testing

---

## Appendix: Tools Reference

### FastAPI (Automatic Documentation)

**Installation**:
```bash
pip install fastapi uvicorn
```

**Usage**:
```python
from fastapi import FastAPI

app = FastAPI(
    title="My API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)
```

**Access Documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Flask + flask-openapi3

**Installation**:
```bash
pip install flask-openapi3
```

**Usage**:
```python
from flask_openapi3 import OpenAPI

app = OpenAPI(__name__, info={"title": "My API", "version": "1.0.0"})

@app.get("/tasks", responses={"200": TaskResponse})
def get_tasks():
    return []
```

### Django REST Framework + drf-spectacular

**Installation**:
```bash
pip install drf-spectacular
```

**Usage**:
```python
# settings.py
INSTALLED_APPS = [
    ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

---

**End of Skill Definition**
