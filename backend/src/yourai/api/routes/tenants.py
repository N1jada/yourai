"""Tenant routes — configuration and branding."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.database import get_db_session
from yourai.core.middleware import get_current_tenant, get_current_user, require_permission
from yourai.core.schemas import BrandingConfig, TenantConfig, UpdateTenant, UserResponse
from yourai.core.tenant import TenantService

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.get("/me", response_model=TenantConfig)
@router.get("/current", response_model=TenantConfig)
async def get_tenant(
    tenant: TenantConfig = Depends(get_current_tenant),
    _user: UserResponse = Depends(get_current_user),
) -> TenantConfig:
    """Return the full configuration for the current tenant."""
    return tenant


@router.patch("/me", response_model=TenantConfig)
@router.patch("/current", response_model=TenantConfig)
async def update_tenant(
    data: UpdateTenant,
    tenant: TenantConfig = Depends(get_current_tenant),
    _perm: None = Depends(require_permission("update_tenant_settings")),
    session: AsyncSession = Depends(get_db_session),
) -> TenantConfig:
    """Update tenant settings. Requires update_tenant_settings permission."""
    tenant_service = TenantService(session)
    return await tenant_service.update_tenant(tenant.id, data)


@router.get("/by-slug/{slug}/branding", response_model=BrandingConfig)
async def get_branding(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> BrandingConfig:
    """Return branding config for pre-login use. Public endpoint."""
    tenant_service = TenantService(session)
    return await tenant_service.get_branding_by_slug(slug)
