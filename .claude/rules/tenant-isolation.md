# Tenant Isolation Rules

These rules are non-negotiable. Violation is a security vulnerability.

1. Every new database table with tenant data MUST have a `tenant_id UUID NOT NULL` column
2. Every new table MUST have an RLS policy in its Alembic migration
3. Every database query MUST filter by `tenant_id` at the application level (belt-and-braces with RLS)
4. Every Qdrant operation MUST use the tenant-specific collection name: `tenant_{tenant_id}_documents`
5. Every API endpoint MUST extract tenant_id from the authenticated user's JWT, never from request parameters
6. Every Celery task that touches tenant data MUST receive and validate `tenant_id` as a parameter
7. Every structured log line MUST include `tenant_id`
8. Cross-tenant data access is a critical security bug — treat it as severity P0
