# Skill Interface Contract

All agent skills MUST conform to this interface.

## Entry Point

```python
def run(vault_root: str) -> dict:
    """
    Execute the skill against the vault.

    Args:
        vault_root: Absolute path to the vault directory (e.g., "D:/project/vault")

    Returns:
        dict with keys:
            - processed: int — number of items processed
            - errors: list[str] — any error messages
            - skipped: int — number of items skipped
    """
```

## Skills Registry

| Skill | Module | Reads From | Writes To |
|-------|--------|-----------|-----------|
| triage_inbox | `src/skills/triage_inbox.py` | `/Inbox` | `/Needs_Action` |
| check_handbook | `src/skills/check_handbook.py` | `Company_Handbook.md` | (returns validation result) |
| plan_task | `src/skills/plan_task.py` | `/Needs_Action` | `/Plans` |
| execute_plan | `src/skills/execute_plan.py` | `/Plans`, `/Approved`, `/Rejected` | `/Pending_Approval`, `/Done`, `/Logs` |
| update_dashboard | `src/skills/update_dashboard.py` | All folders | `Dashboard.md` |

## Action Executor Contract

```python
def execute_action(action_type: str, details: dict, dev_mode: bool = True) -> dict:
    """
    Execute or simulate an external action.

    Args:
        action_type: One of "send_email", "create_invoice", "post_social", "update_calendar", "file_operation"
        details: Action-specific parameters
        dev_mode: If True, simulate only (log without executing)

    Returns:
        dict with keys:
            - success: bool
            - action_type: str
            - details: str — human-readable result
            - simulated: bool — True if dev_mode
    """
```
