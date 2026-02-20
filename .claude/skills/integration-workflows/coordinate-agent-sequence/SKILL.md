---
name: coordinate-agent-sequence
description: Execute multi-agent workflows in correct dependency order with proper error handling
version: 1.0.0
agent: integration-orchestrator
reusability: high
---

# Coordinate Agent Sequence

## Purpose

Orchestrate execution of multiple specialized agents in the correct order, managing dependencies, passing context between agents, and handling failures gracefully.

## When to Use

- Multi-layer feature implementation (frontend + backend + domain + persistence)
- Cross-cutting feature requiring multiple agent coordination
- End-to-end workflow validation
- Complex architectural changes spanning multiple system layers

## Inputs

- **Feature specification** (`specs/<feature>/spec.md`)
- **Implementation plan** (`specs/<feature>/plan.md`)
- **Task breakdown** (`specs/<feature>/tasks.md`)
- **Agent dependency graph** (which agents depend on which)

## Outputs

- **Execution log** with agent sequence and results
- **Integration validation report**
- **Failure points** if any agent fails
- **Rollback recommendations** if workflow incomplete

## Workflow

### 1. Determine Agent Execution Order

**Dependency Analysis:**
```
Domain Guardian → Must run FIRST (defines domain model)
       ↓
Data Schema Guardian → Depends on domain model
       ↓
Python Backend Architect → Depends on domain + schema
       ↓ parallel ↓
Next.js Frontend Architect  ←  Better Auth Guardian
       ↓
Integration Orchestrator → Validates end-to-end
```

**Rules:**
- Domain always first (establishes contracts)
- Schema after domain (maps domain to persistence)
- Backend and Frontend can run in parallel if domain is stable
- Auth can run parallel with Backend
- Integration tests last (after all layers implemented)

### 2. Execute Agent Sequence

**For Each Agent in Order:**

```python
# Pseudocode for agent execution
def execute_agent_workflow(agent_name, context):
    """
    Execute single agent with context from previous agents.

    Args:
        agent_name: Name of agent to invoke
        context: Results and artifacts from previous agents

    Returns:
        AgentResult with status, artifacts, and errors
    """
    logger.info(f"Executing: {agent_name}")

    # 1. Validate prerequisites
    if not validate_prerequisites(agent_name, context):
        return AgentResult(
            status="SKIPPED",
            reason="Prerequisites not met"
        )

    # 2. Invoke agent via Task tool
    result = Task(
        subagent_type=agent_name,
        prompt=build_agent_prompt(agent_name, context),
        description=f"Execute {agent_name} workflow"
    )

    # 3. Validate agent output
    validation = validate_agent_output(result)
    if not validation.passed:
        return AgentResult(
            status="FAILED",
            errors=validation.errors
        )

    # 4. Extract artifacts for next agent
    artifacts = extract_artifacts(result)

    return AgentResult(
        status="SUCCESS",
        artifacts=artifacts
    )
```

### 3. Context Passing Between Agents

**Context Structure:**
```yaml
workflow_context:
  feature_name: "task-priority"
  domain_artifacts:
    entity_definitions: ["Task", "Priority"]
    invariants: ["priority_required_when_status_pending"]
    state_machine: "task_lifecycle.yml"
  schema_artifacts:
    migrations: ["001_add_priority_column.py"]
    tables: ["tasks"]
  backend_artifacts:
    services: ["TaskService"]
    repositories: ["TaskRepository"]
    api_endpoints: ["/api/tasks"]
  frontend_artifacts:
    pages: ["app/tasks/page.tsx"]
    components: ["PrioritySelector"]
```

### 4. Error Handling and Recovery

**Failure Scenarios:**

**A. Agent Fails Validation:**
```
Action: STOP workflow
Report: Which agent failed, what validation failed
Recommendation: Fix issue, re-run from failed agent
```

**B. Agent Partially Succeeds:**
```
Action: PAUSE workflow
Report: What was completed, what's missing
Recommendation: Complete missing items, resume workflow
```

**C. Integration Test Fails:**
```
Action: IDENTIFY layer causing failure
Report: Frontend/Backend/Domain/Schema issue
Recommendation: Re-run specific agent to fix layer
```

### 5. Workflow Coordination Patterns

**Pattern 1: Sequential (Default)**
```
Domain → Schema → Backend → Frontend → Integration
```

**Pattern 2: Parallel (When Possible)**
```
        ┌─ Backend ─┐
Domain →┤           ├→ Integration
        └─ Frontend ┘
```

**Pattern 3: Iterative (for Complex Features)**
```
1. Domain (minimal)
2. Schema (for domain)
3. Backend (basic CRUD)
4. Integration Test
5. Domain (extend)
6. Backend (extend)
7. Integration Test
```

## Constraints

- **DO NOT** run agents out of dependency order
- **DO NOT** pass incomplete context to dependent agents
- **DO NOT** continue workflow if critical agent fails
- **MUST** validate agent outputs before proceeding

## Reusability

**Domain-Agnostic:** Works for any multi-layer feature

**Applicable To:**
- Web app features (frontend + backend + domain)
- API-only features (backend + domain + schema)
- Infrastructure changes (schema + migration + rollback)

**Evolution:**
- Phase 1: Manual agent sequencing
- Phase 2: Automated dependency resolution
- Phase 3: Parallel agent execution where safe
- Phase 4: AI-optimized workflow ordering

## Integration Points

**Triggered By:**
- User request for multi-layer feature
- `/sp.implement` command for complex features
- Architecture changes requiring coordination

**Invokes:**
- Domain Guardian (if domain changes)
- Data Schema Guardian (if schema changes)
- Python Backend Architect (if backend changes)
- Next.js Frontend Architect (if frontend changes)
- Better Auth Guardian (if auth changes)
- Error Reliability Architect (if error handling changes)

**Outputs To:**
- Workflow execution log
- Integration test results
- Coordination report

## Example Workflow

**Feature: Add Task Priority**

```
1. Domain Guardian
   Input: Spec for priority field
   Output: Priority value object, Task entity updated
   Status: ✅ SUCCESS

2. Data Schema Guardian
   Input: Domain model with Priority
   Output: Migration file (add priority column)
   Status: ✅ SUCCESS

3. Python Backend Architect
   Input: Domain + Schema artifacts
   Output: TaskService with priority handling
   Status: ✅ SUCCESS

4. Next.js Frontend Architect
   Input: Backend API contract
   Output: PrioritySelector component
   Status: ✅ SUCCESS

5. Integration Orchestrator (self)
   Input: All layer artifacts
   Output: End-to-end test results
   Status: ✅ SUCCESS

WORKFLOW: COMPLETE
```
