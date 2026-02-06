Review recent code changes against the YourAI architectural standards.

Steps:
1. Run `git diff main --name-only` to see changed files
2. Read `docs/architecture/TECH_DECISIONS.md`
3. For each changed file, check:
   - [ ] Tenant isolation: all DB queries include tenant_id filter
   - [ ] RLS: any new tables have RLS policies in migrations
   - [ ] Logging: endpoints include tenant_id, request_id in structured logs
   - [ ] Error handling: uses error taxonomy from spec Section 14.2
   - [ ] British English: all user-facing strings use British spelling
   - [ ] Types: Pydantic schemas match TypeScript types where applicable
   - [ ] Tests: new code has corresponding test files
   - [ ] Naming: follows project conventions (snake_case Python, camelCase TypeScript)
4. Report findings as a checklist with pass/fail per item
5. Suggest fixes for any failures
