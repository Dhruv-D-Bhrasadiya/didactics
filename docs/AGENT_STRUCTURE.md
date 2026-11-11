# Backend structure and agent prompts

The six-agent workflow is split by responsibility:

- `backend/app/agents/`: one module per agent; shared provider invocation and prompt loading are separate modules.
- `backend/app/prompts/agent_*.txt`: each agent's instruction brief is stored separately from Python logic.
- `backend/app/schemas/workflow.py`: strict, bounded Pydantic contracts exchanged between agents.
- `backend/app/storage/out_manager.py`: creates run directories and writes JSON artifacts/manifests under repository-root `out/`.
- `backend/app/storage/checkpoint_manager.py`: owns checkpoint and failure-record persistence.
- `backend/app/agents/orchestrator.py`: coordinates stages; it does not implement JSON persistence itself.

## Agent 1 input boundary

Agent 1 receives only three problem fields: `statement`, `examples`, and `constraints`. Learner settings are separately whitelisted to `language`, `dsa_proficiency`, and `programming_proficiency`. Title, difficulty, tags, source metadata, URLs, timestamps and unrelated fields are never serialized into Agent 1's model request.

## Output layout

`out/runs/<run_id>/` stores run metadata, logs, media, checkpoints, result and manifest. `out/logs/didactics.log` stores application logs. Generated output is excluded from Git.

Run tests from repository root:

~~~powershell
python -m compileall -q backend
python -m unittest discover -s backend/test -p "test_*.py" -v
~~~
