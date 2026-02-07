"""API routes for policy ontology management."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.config import settings
from yourai.core.database import get_session
from yourai.core.middleware import get_current_tenant, get_current_user
from yourai.core.models import Tenant, User
from yourai.policy.ontology import OntologyService
from yourai.policy.schemas import (
    BulkSeedRequest,
    CreatePolicyDefinition,
    CreatePolicyDefinitionGroup,
    CreatePolicyDefinitionTopic,
    PolicyDefinitionGroupResponse,
    PolicyDefinitionResponse,
    PolicyDefinitionTopicResponse,
    PolicyTypeIdentificationRequest,
    PolicyTypeIdentificationResult,
    UpdatePolicyDefinition,
    UpdatePolicyDefinitionGroup,
    UpdatePolicyDefinitionTopic,
)
from yourai.policy.type_identifier import PolicyTypeIdentifier

router = APIRouter(prefix="/api/v1/policy", tags=["policy"])


# ============================================================================
# Policy Definition Groups
# ============================================================================

@router.get("/groups", response_model=list[PolicyDefinitionGroupResponse])
async def list_policy_groups(
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[PolicyDefinitionGroupResponse]:
    """List all policy definition groups for the tenant."""
    service = OntologyService(session)
    return await service.list_groups(current_tenant.id)


@router.post(
    "/groups",
    response_model=PolicyDefinitionGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_policy_group(
    data: CreatePolicyDefinitionGroup,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyDefinitionGroupResponse:
    """Create a new policy definition group."""
    service = OntologyService(session)
    group = await service.create_group(current_tenant.id, data)
    await session.commit()
    return group


@router.get("/groups/{group_id}", response_model=PolicyDefinitionGroupResponse)
async def get_policy_group(
    group_id: UUID,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyDefinitionGroupResponse:
    """Get a policy definition group by ID."""
    service = OntologyService(session)
    return await service.get_group(group_id, current_tenant.id)


@router.patch("/groups/{group_id}", response_model=PolicyDefinitionGroupResponse)
async def update_policy_group(
    group_id: UUID,
    data: UpdatePolicyDefinitionGroup,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyDefinitionGroupResponse:
    """Update a policy definition group."""
    service = OntologyService(session)
    group = await service.update_group(group_id, current_tenant.id, data)
    await session.commit()
    return group


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_group(
    group_id: UUID,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a policy definition group."""
    service = OntologyService(session)
    await service.delete_group(group_id, current_tenant.id)
    await session.commit()


# ============================================================================
# Policy Definition Topics
# ============================================================================

@router.get("/topics", response_model=list[PolicyDefinitionTopicResponse])
async def list_policy_topics(
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[PolicyDefinitionTopicResponse]:
    """List all policy definition topics for the tenant."""
    service = OntologyService(session)
    return await service.list_topics(current_tenant.id)


@router.post(
    "/topics",
    response_model=PolicyDefinitionTopicResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_policy_topic(
    data: CreatePolicyDefinitionTopic,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyDefinitionTopicResponse:
    """Create a new policy definition topic."""
    service = OntologyService(session)
    topic = await service.create_topic(current_tenant.id, data)
    await session.commit()
    return topic


@router.get("/topics/{topic_id}", response_model=PolicyDefinitionTopicResponse)
async def get_policy_topic(
    topic_id: UUID,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyDefinitionTopicResponse:
    """Get a policy definition topic by ID."""
    service = OntologyService(session)
    return await service.get_topic(topic_id, current_tenant.id)


@router.patch("/topics/{topic_id}", response_model=PolicyDefinitionTopicResponse)
async def update_policy_topic(
    topic_id: UUID,
    data: UpdatePolicyDefinitionTopic,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyDefinitionTopicResponse:
    """Update a policy definition topic."""
    service = OntologyService(session)
    topic = await service.update_topic(topic_id, current_tenant.id, data)
    await session.commit()
    return topic


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_topic(
    topic_id: UUID,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a policy definition topic."""
    service = OntologyService(session)
    await service.delete_topic(topic_id, current_tenant.id)
    await session.commit()


# ============================================================================
# Policy Definitions
# ============================================================================

@router.get("/definitions", response_model=list[PolicyDefinitionResponse])
async def list_policy_definitions(
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
    group_id: UUID | None = None,
    status_filter: str | None = None,
) -> list[PolicyDefinitionResponse]:
    """List all policy definitions for the tenant.

    Query parameters:
    - group_id: Optional filter by group
    - status: Optional filter by status (active/inactive)
    """
    service = OntologyService(session)
    return await service.list_definitions(current_tenant.id, group_id, status_filter)


@router.post(
    "/definitions",
    response_model=PolicyDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_policy_definition(
    data: CreatePolicyDefinition,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyDefinitionResponse:
    """Create a new policy definition."""
    service = OntologyService(session)
    definition = await service.create_definition(current_tenant.id, data)
    await session.commit()
    return definition


@router.get("/definitions/{definition_id}", response_model=PolicyDefinitionResponse)
async def get_policy_definition(
    definition_id: UUID,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyDefinitionResponse:
    """Get a policy definition by ID."""
    service = OntologyService(session)
    return await service.get_definition(definition_id, current_tenant.id)


@router.patch(
    "/definitions/{definition_id}",
    response_model=PolicyDefinitionResponse,
)
async def update_policy_definition(
    definition_id: UUID,
    data: UpdatePolicyDefinition,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyDefinitionResponse:
    """Update a policy definition."""
    service = OntologyService(session)
    definition = await service.update_definition(definition_id, current_tenant.id, data)
    await session.commit()
    return definition


@router.delete("/definitions/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_definition(
    definition_id: UUID,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a policy definition."""
    service = OntologyService(session)
    await service.delete_definition(definition_id, current_tenant.id)
    await session.commit()


@router.post(
    "/definitions/seed",
    response_model=list[PolicyDefinitionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def seed_policy_definitions(
    data: BulkSeedRequest,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[PolicyDefinitionResponse]:
    """Bulk seed policy definitions for tenant setup.

    This endpoint is idempotent - duplicate URIs will be skipped.
    """
    service = OntologyService(session)
    definitions = await service.seed_definitions(current_tenant.id, data.definitions)
    await session.commit()
    return definitions


# ============================================================================
# Policy Type Identification
# ============================================================================

@router.post("/identify", response_model=PolicyTypeIdentificationResult)
async def identify_policy_type(
    data: PolicyTypeIdentificationRequest,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PolicyTypeIdentificationResult:
    """Identify policy type from document text.

    Uses Haiku model to classify the uploaded document against the tenant's
    policy definition ontology.

    Returns the best matching definition with confidence score, or null if
    no clear match found.
    """
    anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    identifier = PolicyTypeIdentifier(anthropic_client)

    result = await identifier.identify_policy_type(
        data.document_text,
        current_tenant.id,
        session,
    )

    return result
