# InfiniteQ v0.2 Tests

## Running Tests

```bash
# Run all tests
pytest

# Run integration tests only
pytest backend/tests/test_v02_integration.py

# Run unit tests only
pytest backend/tests/test_services_v02.py

# Run with coverage
pytest --cov=backend/app --cov-report=html

# Run specific test class
pytest backend/tests/test_v02_integration.py::TestReflectionPulse

# Run specific test
pytest backend/tests/test_v02_integration.py::TestReflectionPulse::test_submit_reflection
```

## Test Structure

### Integration Tests (`test_v02_integration.py`)
Full API tests covering:
- Session creation with profiles
- Thread management
- Reflection pulse system
- Profile-aware question generation
- Plan synthesis with views and execution bundles
- Complete end-to-end workflows

### Unit Tests (`test_services_v02.py`)
Service-level tests for:
- PlanReducer v0.2 (notes extraction, phase coverage)
- PlanSynthesizer v0.2 (scaffolds, tasks, prompts)
- Profile integration

## Requirements

```bash
pip install pytest pytest-cov httpx
```

## Notes

- Integration tests require the FastAPI app to be importable
- Tests use TestClient for HTTP calls (no server needed)
- Mock external LLM calls for faster testing
- Use `-s` flag to see print statements during tests
