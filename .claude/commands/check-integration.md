Check that interfaces between work packages are compatible.

Steps:
1. Read `docs/architecture/API_CONTRACTS.md`
2. Find all interface definitions (classes with docstrings marked as "Interface")
3. Find all consumers of those interfaces (imports/usage)
4. For each interface:
   - [ ] Implementation exists and matches the contract
   - [ ] All method signatures match (parameters, return types)
   - [ ] Error handling is consistent (same exceptions/error codes)
   - [ ] Tenant scoping is consistent (tenant_id parameter present where needed)
5. Run integration tests: `cd backend && uv run pytest tests/integration/ -x`
6. Report any contract violations or test failures
