## What does this PR do?

<!-- One-line summary -->

## Type of change

- [ ] Bug fix
- [ ] New connector
- [ ] New exporter
- [ ] New feature
- [ ] Documentation
- [ ] Refactor / cleanup

## New connector / exporter checklist

If this adds a connector or exporter, please confirm:

- [ ] Registered in `__init__.py`
- [ ] Defensive `.get()` used throughout (no `KeyError` on missing fields)
- [ ] `stable_id()` used for all node IDs
- [ ] Tests added
- [ ] Export format documented in module docstring (how users get their data)
- [ ] CHANGELOG updated

## Testing

```
pytest tests/ -v
```

Paste output or confirm all tests pass.

## Screenshots / demo (if relevant)
