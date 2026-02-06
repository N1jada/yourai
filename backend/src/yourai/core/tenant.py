"""Tenant service — CRUD for tenants table.

The tenants table is platform-level (no tenant_id, no RLS).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select

from yourai.core.exceptions import NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession
from yourai.core.models import Tenant
from yourai.core.schemas import AIConfig, BrandingConfig, TenantConfig, UpdateTenant

logger = structlog.get_logger()


def _to_tenant_config(tenant: Tenant) -> TenantConfig:
    """Map a Tenant ORM instance to a TenantConfig response schema."""
    return TenantConfig(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        industry_vertical=tenant.industry_vertical,
        branding=BrandingConfig.model_validate(tenant.branding_config),
        ai_config=AIConfig.model_validate(tenant.ai_config),
        subscription_tier=tenant.subscription_tier,
        credit_limit=float(tenant.credit_limit),
        billing_period_start=tenant.billing_period_start,
        billing_period_end=tenant.billing_period_end,
        is_active=tenant.is_active,
        news_feed_urls=tenant.news_feed_urls,
        external_source_integrations=tenant.external_source_integrations,
        vector_namespace=tenant.vector_namespace,
    )


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_tenant(self, tenant_id: UUID) -> TenantConfig:
        """Return full tenant configuration. Raises 404 if not found."""
        result = await self._session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            raise NotFoundError("Tenant not found.")
        return _to_tenant_config(tenant)

    async def get_by_slug(self, slug: str) -> Tenant:
        """Fetch tenant by slug. Raises 404 if not found."""
        result = await self._session.execute(select(Tenant).where(Tenant.slug == slug))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            raise NotFoundError("Tenant not found.")
        return tenant

    async def get_branding(self, slug: str) -> BrandingConfig:
        """Return branding config for public pre-login use."""
        tenant = await self.get_by_slug(slug)
        return BrandingConfig.model_validate(tenant.branding_config)

    async def update_tenant(self, tenant_id: UUID, data: UpdateTenant) -> TenantConfig:
        """Update tenant settings."""
        result = await self._session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            raise NotFoundError("Tenant not found.")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self._session.flush()
        await self._session.refresh(tenant)
        logger.info("tenant_updated", tenant_id=str(tenant_id))
        return _to_tenant_config(tenant)
