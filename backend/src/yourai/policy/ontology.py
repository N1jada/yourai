"""Policy ontology service — CRUD for groups, topics, and definitions."""

from __future__ import annotations

from uuid import UUID

import structlog
import uuid_utils
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from yourai.core.exceptions import ConflictError, NotFoundError
from yourai.policy.models import (
    PolicyDefinition,
    PolicyDefinitionGroup,
    PolicyDefinitionTopic,
)
from yourai.policy.schemas import (
    CreatePolicyDefinition,
    CreatePolicyDefinitionGroup,
    CreatePolicyDefinitionTopic,
    PolicyDefinitionGroupResponse,
    PolicyDefinitionResponse,
    PolicyDefinitionTopicResponse,
    UpdatePolicyDefinition,
    UpdatePolicyDefinitionGroup,
    UpdatePolicyDefinitionTopic,
)

logger = structlog.get_logger()


class OntologyService:
    """Service for managing policy ontology (groups, topics, definitions)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ========================================================================
    # Policy Definition Groups
    # ========================================================================

    async def create_group(
        self,
        tenant_id: UUID,
        data: CreatePolicyDefinitionGroup,
    ) -> PolicyDefinitionGroupResponse:
        """Create a new policy definition group.

        Args:
            tenant_id: Tenant UUID
            data: Group creation data

        Returns:
            Created group

        Raises:
            ConflictError: If group name already exists for tenant
        """
        # Check for existing group with same name
        result = await self._session.execute(
            select(PolicyDefinitionGroup).where(
                PolicyDefinitionGroup.tenant_id == tenant_id,
                PolicyDefinitionGroup.name == data.name,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ConflictError(f"Group '{data.name}' already exists")

        group = PolicyDefinitionGroup(
            id=uuid_utils.uuid7(),
            tenant_id=tenant_id,
            **data.model_dump(),
        )
        self._session.add(group)
        await self._session.flush()

        logger.info(
            "policy_group_created",
            tenant_id=str(tenant_id),
            group_id=str(group.id),
            name=group.name,
        )

        return self._group_to_response(group)

    async def list_groups(
        self,
        tenant_id: UUID,
    ) -> list[PolicyDefinitionGroupResponse]:
        """List all policy definition groups for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            List of groups
        """
        result = await self._session.execute(
            select(PolicyDefinitionGroup)
            .where(PolicyDefinitionGroup.tenant_id == tenant_id)
            .order_by(PolicyDefinitionGroup.name)
        )
        groups = list(result.scalars().all())

        return [self._group_to_response(g) for g in groups]

    async def get_group(
        self,
        group_id: UUID,
        tenant_id: UUID,
    ) -> PolicyDefinitionGroupResponse:
        """Get a policy definition group by ID.

        Args:
            group_id: Group UUID
            tenant_id: Tenant UUID

        Returns:
            Group

        Raises:
            NotFoundError: If group not found
        """
        result = await self._session.execute(
            select(PolicyDefinitionGroup).where(
                PolicyDefinitionGroup.id == group_id,
                PolicyDefinitionGroup.tenant_id == tenant_id,
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            raise NotFoundError(f"Group {group_id} not found")

        return self._group_to_response(group)

    async def update_group(
        self,
        group_id: UUID,
        tenant_id: UUID,
        data: UpdatePolicyDefinitionGroup,
    ) -> PolicyDefinitionGroupResponse:
        """Update a policy definition group.

        Args:
            group_id: Group UUID
            tenant_id: Tenant UUID
            data: Update data

        Returns:
            Updated group

        Raises:
            NotFoundError: If group not found
        """
        result = await self._session.execute(
            select(PolicyDefinitionGroup).where(
                PolicyDefinitionGroup.id == group_id,
                PolicyDefinitionGroup.tenant_id == tenant_id,
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            raise NotFoundError(f"Group {group_id} not found")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(group, key, value)

        await self._session.flush()

        logger.info(
            "policy_group_updated",
            tenant_id=str(tenant_id),
            group_id=str(group_id),
        )

        return self._group_to_response(group)

    async def delete_group(
        self,
        group_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Delete a policy definition group.

        Args:
            group_id: Group UUID
            tenant_id: Tenant UUID

        Raises:
            NotFoundError: If group not found
        """
        result = await self._session.execute(
            select(PolicyDefinitionGroup).where(
                PolicyDefinitionGroup.id == group_id,
                PolicyDefinitionGroup.tenant_id == tenant_id,
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            raise NotFoundError(f"Group {group_id} not found")

        await self._session.delete(group)
        await self._session.flush()

        logger.info(
            "policy_group_deleted",
            tenant_id=str(tenant_id),
            group_id=str(group_id),
        )

    # ========================================================================
    # Policy Definition Topics
    # ========================================================================

    async def create_topic(
        self,
        tenant_id: UUID,
        data: CreatePolicyDefinitionTopic,
    ) -> PolicyDefinitionTopicResponse:
        """Create a new policy definition topic.

        Args:
            tenant_id: Tenant UUID
            data: Topic creation data

        Returns:
            Created topic

        Raises:
            ConflictError: If topic name already exists for tenant
        """
        # Check for existing topic with same name
        result = await self._session.execute(
            select(PolicyDefinitionTopic).where(
                PolicyDefinitionTopic.tenant_id == tenant_id,
                PolicyDefinitionTopic.name == data.name,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ConflictError(f"Topic '{data.name}' already exists")

        topic = PolicyDefinitionTopic(
            id=uuid_utils.uuid7(),
            tenant_id=tenant_id,
            **data.model_dump(),
        )
        self._session.add(topic)
        await self._session.flush()

        logger.info(
            "policy_topic_created",
            tenant_id=str(tenant_id),
            topic_id=str(topic.id),
            name=topic.name,
        )

        return self._topic_to_response(topic)

    async def list_topics(
        self,
        tenant_id: UUID,
    ) -> list[PolicyDefinitionTopicResponse]:
        """List all policy definition topics for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            List of topics
        """
        result = await self._session.execute(
            select(PolicyDefinitionTopic)
            .where(PolicyDefinitionTopic.tenant_id == tenant_id)
            .order_by(PolicyDefinitionTopic.name)
        )
        topics = list(result.scalars().all())

        return [self._topic_to_response(t) for t in topics]

    async def get_topic(
        self,
        topic_id: UUID,
        tenant_id: UUID,
    ) -> PolicyDefinitionTopicResponse:
        """Get a policy definition topic by ID.

        Args:
            topic_id: Topic UUID
            tenant_id: Tenant UUID

        Returns:
            Topic

        Raises:
            NotFoundError: If topic not found
        """
        result = await self._session.execute(
            select(PolicyDefinitionTopic).where(
                PolicyDefinitionTopic.id == topic_id,
                PolicyDefinitionTopic.tenant_id == tenant_id,
            )
        )
        topic = result.scalar_one_or_none()
        if not topic:
            raise NotFoundError(f"Topic {topic_id} not found")

        return self._topic_to_response(topic)

    async def update_topic(
        self,
        topic_id: UUID,
        tenant_id: UUID,
        data: UpdatePolicyDefinitionTopic,
    ) -> PolicyDefinitionTopicResponse:
        """Update a policy definition topic.

        Args:
            topic_id: Topic UUID
            tenant_id: Tenant UUID
            data: Update data

        Returns:
            Updated topic

        Raises:
            NotFoundError: If topic not found
        """
        result = await self._session.execute(
            select(PolicyDefinitionTopic).where(
                PolicyDefinitionTopic.id == topic_id,
                PolicyDefinitionTopic.tenant_id == tenant_id,
            )
        )
        topic = result.scalar_one_or_none()
        if not topic:
            raise NotFoundError(f"Topic {topic_id} not found")

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(topic, key, value)

        await self._session.flush()

        logger.info(
            "policy_topic_updated",
            tenant_id=str(tenant_id),
            topic_id=str(topic_id),
        )

        return self._topic_to_response(topic)

    async def delete_topic(
        self,
        topic_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Delete a policy definition topic.

        Args:
            topic_id: Topic UUID
            tenant_id: Tenant UUID

        Raises:
            NotFoundError: If topic not found
        """
        result = await self._session.execute(
            select(PolicyDefinitionTopic).where(
                PolicyDefinitionTopic.id == topic_id,
                PolicyDefinitionTopic.tenant_id == tenant_id,
            )
        )
        topic = result.scalar_one_or_none()
        if not topic:
            raise NotFoundError(f"Topic {topic_id} not found")

        await self._session.delete(topic)
        await self._session.flush()

        logger.info(
            "policy_topic_deleted",
            tenant_id=str(tenant_id),
            topic_id=str(topic_id),
        )

    # ========================================================================
    # Policy Definitions
    # ========================================================================

    async def create_definition(
        self,
        tenant_id: UUID,
        data: CreatePolicyDefinition,
    ) -> PolicyDefinitionResponse:
        """Create a new policy definition.

        Args:
            tenant_id: Tenant UUID
            data: Definition creation data

        Returns:
            Created definition

        Raises:
            ConflictError: If definition URI already exists for tenant
            NotFoundError: If group_id or topic_ids reference non-existent entities
        """
        # Check for existing definition with same URI
        result = await self._session.execute(
            select(PolicyDefinition).where(
                PolicyDefinition.tenant_id == tenant_id,
                PolicyDefinition.uri == data.uri,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ConflictError(f"Policy definition with URI '{data.uri}' already exists")

        # Validate group_id if provided
        if data.group_id:
            group_result = await self._session.execute(
                select(PolicyDefinitionGroup).where(
                    PolicyDefinitionGroup.id == data.group_id,
                    PolicyDefinitionGroup.tenant_id == tenant_id,
                )
            )
            if not group_result.scalar_one_or_none():
                raise NotFoundError(f"Group {data.group_id} not found")

        # Load topics if provided
        topics = []
        if data.topic_ids:
            topics_result = await self._session.execute(
                select(PolicyDefinitionTopic).where(
                    PolicyDefinitionTopic.id.in_(data.topic_ids),
                    PolicyDefinitionTopic.tenant_id == tenant_id,
                )
            )
            topics = list(topics_result.scalars().all())
            if len(topics) != len(data.topic_ids):
                raise NotFoundError("One or more topic IDs not found")

        # Extract topic_ids from data for creation
        creation_data = data.model_dump(exclude={"topic_ids"})
        
        # Convert nested Pydantic models to dicts for JSON columns
        creation_data["scoring_criteria"] = [
            sc.model_dump() for sc in data.scoring_criteria
        ]
        creation_data["compliance_criteria"] = [
            cc.model_dump() for cc in data.compliance_criteria
        ]
        creation_data["legislation_references"] = [
            lr.model_dump() for lr in data.legislation_references
        ]

        definition = PolicyDefinition(
            id=uuid_utils.uuid7(),
            tenant_id=tenant_id,
            **creation_data,
        )
        definition.topics = topics
        self._session.add(definition)
        await self._session.flush()

        # Refresh with eager loading for relationships
        await self._session.refresh(definition, ["topics", "group"])

        logger.info(
            "policy_definition_created",
            tenant_id=str(tenant_id),
            definition_id=str(definition.id),
            uri=definition.uri,
        )

        return self._definition_to_response(definition)

    async def list_definitions(
        self,
        tenant_id: UUID,
        group_id: UUID | None = None,
        status: str | None = None,
    ) -> list[PolicyDefinitionResponse]:
        """List policy definitions for a tenant.

        Args:
            tenant_id: Tenant UUID
            group_id: Optional filter by group
            status: Optional filter by status (active/inactive)

        Returns:
            List of definitions
        """
        query = (
            select(PolicyDefinition)
            .where(PolicyDefinition.tenant_id == tenant_id)
            .options(
                selectinload(PolicyDefinition.topics),
                selectinload(PolicyDefinition.group),
            )
        )

        if group_id:
            query = query.where(PolicyDefinition.group_id == group_id)
        if status:
            query = query.where(PolicyDefinition.status == status)

        query = query.order_by(PolicyDefinition.name)

        result = await self._session.execute(query)
        definitions = list(result.scalars().all())

        return [self._definition_to_response(d) for d in definitions]

    async def get_definition(
        self,
        definition_id: UUID,
        tenant_id: UUID,
    ) -> PolicyDefinitionResponse:
        """Get a policy definition by ID.

        Args:
            definition_id: Definition UUID
            tenant_id: UUID

        Returns:
            Definition

        Raises:
            NotFoundError: If definition not found
        """
        result = await self._session.execute(
            select(PolicyDefinition)
            .where(
                PolicyDefinition.id == definition_id,
                PolicyDefinition.tenant_id == tenant_id,
            )
            .options(
                selectinload(PolicyDefinition.topics),
                selectinload(PolicyDefinition.group),
            )
        )
        definition = result.scalar_one_or_none()
        if not definition:
            raise NotFoundError(f"Policy definition {definition_id} not found")

        return self._definition_to_response(definition)

    async def update_definition(
        self,
        definition_id: UUID,
        tenant_id: UUID,
        data: UpdatePolicyDefinition,
    ) -> PolicyDefinitionResponse:
        """Update a policy definition.

        Args:
            definition_id: Definition UUID
            tenant_id: Tenant UUID
            data: Update data

        Returns:
            Updated definition

        Raises:
            NotFoundError: If definition not found
        """
        result = await self._session.execute(
            select(PolicyDefinition).where(
                PolicyDefinition.id == definition_id,
                PolicyDefinition.tenant_id == tenant_id,
            )
        )
        definition = result.scalar_one_or_none()
        if not definition:
            raise NotFoundError(f"Policy definition {definition_id} not found")

        # Update topics if provided
        if data.topic_ids is not None:
            topics_result = await self._session.execute(
                select(PolicyDefinitionTopic).where(
                    PolicyDefinitionTopic.id.in_(data.topic_ids),
                    PolicyDefinitionTopic.tenant_id == tenant_id,
                )
            )
            topics = list(topics_result.scalars().all())
            if len(topics) != len(data.topic_ids):
                raise NotFoundError("One or more topic IDs not found")
            definition.topics = topics

        # Update other fields
        update_data = data.model_dump(exclude_unset=True, exclude={"topic_ids"})
        
        # Convert nested Pydantic models to dicts for JSON columns
        if "scoring_criteria" in update_data and update_data["scoring_criteria"]:
            update_data["scoring_criteria"] = [
                sc.model_dump() for sc in data.scoring_criteria  # type: ignore[union-attr]
            ]
        if "compliance_criteria" in update_data and update_data["compliance_criteria"]:
            update_data["compliance_criteria"] = [
                cc.model_dump() for cc in data.compliance_criteria  # type: ignore[union-attr]
            ]
        if "legislation_references" in update_data and update_data["legislation_references"]:
            update_data["legislation_references"] = [
                lr.model_dump() for lr in data.legislation_references  # type: ignore[union-attr]
            ]

        for key, value in update_data.items():
            setattr(definition, key, value)

        await self._session.flush()

        # Refresh with eager loading for relationships
        await self._session.refresh(definition, ["topics", "group"])

        logger.info(
            "policy_definition_updated",
            tenant_id=str(tenant_id),
            definition_id=str(definition_id),
        )

        return self._definition_to_response(definition)

    async def delete_definition(
        self,
        definition_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Delete a policy definition.

        Args:
            definition_id: Definition UUID
            tenant_id: Tenant UUID

        Raises:
            NotFoundError: If definition not found
        """
        result = await self._session.execute(
            select(PolicyDefinition).where(
                PolicyDefinition.id == definition_id,
                PolicyDefinition.tenant_id == tenant_id,
            )
        )
        definition = result.scalar_one_or_none()
        if not definition:
            raise NotFoundError(f"Policy definition {definition_id} not found")

        await self._session.delete(definition)
        await self._session.flush()

        logger.info(
            "policy_definition_deleted",
            tenant_id=str(tenant_id),
            definition_id=str(definition_id),
        )

    async def seed_definitions(
        self,
        tenant_id: UUID,
        definitions: list[CreatePolicyDefinition],
    ) -> list[PolicyDefinitionResponse]:
        """Bulk seed policy definitions for a tenant.

        Args:
            tenant_id: Tenant UUID
            definitions: List of definitions to create

        Returns:
            List of created definitions
        """
        created = []
        for data in definitions:
            try:
                definition = await self.create_definition(tenant_id, data)
                created.append(definition)
            except ConflictError:
                # Skip duplicates
                logger.warning(
                    "policy_definition_seed_duplicate",
                    tenant_id=str(tenant_id),
                    uri=data.uri,
                )
                continue

        logger.info(
            "policy_definitions_seeded",
            tenant_id=str(tenant_id),
            count=len(created),
        )

        return created

    # ========================================================================
    # Response Converters
    # ========================================================================

    @staticmethod
    def _group_to_response(group: PolicyDefinitionGroup) -> PolicyDefinitionGroupResponse:
        """Convert ORM model to response schema."""
        return PolicyDefinitionGroupResponse(
            id=UUID(str(group.id)),
            tenant_id=UUID(str(group.tenant_id)),
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )

    @staticmethod
    def _topic_to_response(topic: PolicyDefinitionTopic) -> PolicyDefinitionTopicResponse:
        """Convert ORM model to response schema."""
        return PolicyDefinitionTopicResponse(
            id=UUID(str(topic.id)),
            tenant_id=UUID(str(topic.tenant_id)),
            name=topic.name,
            created_at=topic.created_at,
            updated_at=topic.updated_at,
        )

    @staticmethod
    def _definition_to_response(definition: PolicyDefinition) -> PolicyDefinitionResponse:
        """Convert ORM model to response schema."""
        from yourai.policy.schemas import (
            ComplianceCriterion,
            LegislationReference,
            ScoringCriterion,
        )

        return PolicyDefinitionResponse(
            id=UUID(str(definition.id)),
            tenant_id=UUID(str(definition.tenant_id)),
            name=definition.name,
            uri=definition.uri,
            status=definition.status,
            group_id=UUID(str(definition.group_id)) if definition.group_id else None,
            description=definition.description,
            is_required=definition.is_required,
            review_cycle=definition.review_cycle,
            name_variants=definition.name_variants,
            scoring_criteria=[
                ScoringCriterion(**sc) for sc in definition.scoring_criteria
            ],
            compliance_criteria=[
                ComplianceCriterion(**cc) for cc in definition.compliance_criteria
            ],
            required_sections=definition.required_sections,
            legislation_references=[
                LegislationReference(**lr) for lr in definition.legislation_references
            ],
            last_regulatory_update_date=definition.last_regulatory_update_date,
            regulatory_change_flags=definition.regulatory_change_flags,
            created_at=definition.created_at,
            updated_at=definition.updated_at,
            group=(
                OntologyService._group_to_response(definition.group)
                if definition.group
                else None
            ),
            topics=[OntologyService._topic_to_response(t) for t in definition.topics],
        )
