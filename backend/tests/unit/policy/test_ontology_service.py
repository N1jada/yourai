"""Unit tests for OntologyService — CRUD operations for policy ontology."""

from __future__ import annotations

import pytest
import uuid_utils
from sqlalchemy.ext.asyncio import AsyncSession

from yourai.core.exceptions import ConflictError, NotFoundError
from yourai.core.models import Tenant
from yourai.policy.ontology import OntologyService
from yourai.policy.schemas import (
    ComplianceCriterion,
    CreatePolicyDefinition,
    CreatePolicyDefinitionGroup,
    CreatePolicyDefinitionTopic,
    LegislationReference,
    ScoringCriterion,
    UpdatePolicyDefinition,
    UpdatePolicyDefinitionGroup,
    UpdatePolicyDefinitionTopic,
)

# ============================================================================
# Policy Definition Groups
# ============================================================================


async def test_create_group(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Creating a group returns a response with tenant_id."""
    svc = OntologyService(test_session)
    data = CreatePolicyDefinitionGroup(
        name="Operational Policies",
        description="Day-to-day operational policies",
    )
    group = await svc.create_group(sample_tenant.id, data)
    assert group.name == "Operational Policies"
    assert str(group.tenant_id) == str(sample_tenant.id)


async def test_get_group(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can retrieve a group by ID."""
    svc = OntologyService(test_session)
    data = CreatePolicyDefinitionGroup(name="Test Group")
    created = await svc.create_group(sample_tenant.id, data)

    fetched = await svc.get_group(created.id, sample_tenant.id)
    assert str(fetched.id) == str(created.id)
    assert fetched.name == "Test Group"


async def test_get_group_not_found(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Getting a non-existent group raises NotFoundError."""
    svc = OntologyService(test_session)
    with pytest.raises(NotFoundError):
        await svc.get_group(uuid_utils.uuid7(), sample_tenant.id)


async def test_list_groups(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Listing groups returns all groups for tenant."""
    svc = OntologyService(test_session)
    await svc.create_group(sample_tenant.id, CreatePolicyDefinitionGroup(name="Group A"))
    await svc.create_group(sample_tenant.id, CreatePolicyDefinitionGroup(name="Group B"))

    groups = await svc.list_groups(sample_tenant.id)
    assert len(groups) == 2
    assert {g.name for g in groups} == {"Group A", "Group B"}


async def test_update_group(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can update group name and description."""
    svc = OntologyService(test_session)
    created = await svc.create_group(sample_tenant.id, CreatePolicyDefinitionGroup(name="Old Name"))

    updated = await svc.update_group(
        created.id,
        sample_tenant.id,
        UpdatePolicyDefinitionGroup(name="New Name", description="Updated description"),
    )
    assert updated.name == "New Name"
    assert updated.description == "Updated description"


async def test_delete_group(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Deleting a group removes it from database."""
    svc = OntologyService(test_session)
    created = await svc.create_group(
        sample_tenant.id, CreatePolicyDefinitionGroup(name="To Delete")
    )

    await svc.delete_group(created.id, sample_tenant.id)
    await test_session.commit()

    with pytest.raises(NotFoundError):
        await svc.get_group(created.id, sample_tenant.id)


async def test_groups_tenant_isolation(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Groups from one tenant are not visible to another tenant."""
    # Create second tenant
    other_tenant = Tenant(
        id=uuid_utils.uuid7(),
        name="Other Tenant",
        slug="other-tenant",
        industry_vertical="healthcare",
        is_active=True,
    )
    test_session.add(other_tenant)
    await test_session.flush()

    svc = OntologyService(test_session)
    group = await svc.create_group(
        sample_tenant.id, CreatePolicyDefinitionGroup(name="Tenant A Group")
    )

    # Attempting to access from other tenant should fail
    with pytest.raises(NotFoundError):
        await svc.get_group(group.id, other_tenant.id)


# ============================================================================
# Policy Definition Topics
# ============================================================================


async def test_create_topic(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Creating a topic returns a response with tenant_id."""
    svc = OntologyService(test_session)
    data = CreatePolicyDefinitionTopic(name="Safeguarding")
    topic = await svc.create_topic(sample_tenant.id, data)
    assert topic.name == "Safeguarding"
    assert str(topic.tenant_id) == str(sample_tenant.id)


async def test_get_topic(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can retrieve a topic by ID."""
    svc = OntologyService(test_session)
    created = await svc.create_topic(
        sample_tenant.id, CreatePolicyDefinitionTopic(name="Test Topic")
    )

    fetched = await svc.get_topic(created.id, sample_tenant.id)
    assert str(fetched.id) == str(created.id)
    assert fetched.name == "Test Topic"


async def test_list_topics(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Listing topics returns all topics for tenant."""
    svc = OntologyService(test_session)
    await svc.create_topic(sample_tenant.id, CreatePolicyDefinitionTopic(name="Topic A"))
    await svc.create_topic(sample_tenant.id, CreatePolicyDefinitionTopic(name="Topic B"))

    topics = await svc.list_topics(sample_tenant.id)
    assert len(topics) == 2
    assert {t.name for t in topics} == {"Topic A", "Topic B"}


async def test_update_topic(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can update topic name."""
    svc = OntologyService(test_session)
    created = await svc.create_topic(
        sample_tenant.id, CreatePolicyDefinitionTopic(name="Old Topic")
    )

    updated = await svc.update_topic(
        created.id,
        sample_tenant.id,
        UpdatePolicyDefinitionTopic(name="New Topic"),
    )
    assert updated.name == "New Topic"


async def test_delete_topic(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Deleting a topic removes it from database."""
    svc = OntologyService(test_session)
    created = await svc.create_topic(
        sample_tenant.id, CreatePolicyDefinitionTopic(name="To Delete")
    )

    await svc.delete_topic(created.id, sample_tenant.id)
    await test_session.commit()

    with pytest.raises(NotFoundError):
        await svc.get_topic(created.id, sample_tenant.id)


# ============================================================================
# Policy Definitions
# ============================================================================


async def test_create_definition(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Creating a definition returns a response with tenant_id."""
    svc = OntologyService(test_session)
    data = CreatePolicyDefinition(
        name="Health & Safety Policy",
        uri="health-and-safety-policy",
        description="Covers workplace safety",
        is_required=True,
        review_cycle="annual",
    )
    definition = await svc.create_definition(sample_tenant.id, data)
    assert definition.name == "Health & Safety Policy"
    assert definition.uri == "health-and-safety-policy"
    assert definition.is_required is True
    assert str(definition.tenant_id) == str(sample_tenant.id)


async def test_create_definition_duplicate_uri_raises_conflict(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Creating a definition with duplicate URI raises ConflictError."""
    svc = OntologyService(test_session)
    data = CreatePolicyDefinition(
        name="Policy A",
        uri="duplicate-uri",
    )
    await svc.create_definition(sample_tenant.id, data)

    # Attempt to create another with same URI
    with pytest.raises(ConflictError, match="already exists"):
        await svc.create_definition(sample_tenant.id, data)


async def test_create_definition_with_group_and_topics(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can create definition with group and topics."""
    svc = OntologyService(test_session)

    # Create group and topics
    group = await svc.create_group(sample_tenant.id, CreatePolicyDefinitionGroup(name="Test Group"))
    topic1 = await svc.create_topic(sample_tenant.id, CreatePolicyDefinitionTopic(name="Topic 1"))
    topic2 = await svc.create_topic(sample_tenant.id, CreatePolicyDefinitionTopic(name="Topic 2"))

    # Create definition with group and topics
    data = CreatePolicyDefinition(
        name="Test Policy",
        uri="test-policy",
        group_id=group.id,
        topic_ids=[topic1.id, topic2.id],
    )
    definition = await svc.create_definition(sample_tenant.id, data)

    assert str(definition.group_id) == str(group.id)
    assert len(definition.topics) == 2
    assert {str(t.id) for t in definition.topics} == {str(topic1.id), str(topic2.id)}


async def test_create_definition_with_compliance_and_scoring_criteria(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can create definition with compliance and scoring criteria."""
    svc = OntologyService(test_session)
    data = CreatePolicyDefinition(
        name="Complex Policy",
        uri="complex-policy",
        compliance_criteria=[
            ComplianceCriterion(
                name="HSWA 1974 Compliance",
                priority="high",
                description="Must comply with Health & Safety at Work Act 1974",
                criteria_type="mandatory",
            )
        ],
        scoring_criteria=[
            ScoringCriterion(
                criterion="Risk Assessment",
                green_threshold="Comprehensive process",
                amber_threshold="Basic process",
                red_threshold="No process",
            )
        ],
        required_sections=["Policy Statement", "Procedures"],
        legislation_references=[
            LegislationReference(
                act_name="Health and Safety at Work etc. Act 1974",
                section="s.2",
                notes="Employer's duty",
            )
        ],
    )
    definition = await svc.create_definition(sample_tenant.id, data)

    assert len(definition.compliance_criteria) == 1
    assert definition.compliance_criteria[0].name == "HSWA 1974 Compliance"
    assert len(definition.scoring_criteria) == 1
    assert definition.scoring_criteria[0].criterion == "Risk Assessment"
    assert len(definition.required_sections) == 2
    assert len(definition.legislation_references) == 1


async def test_get_definition(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can retrieve a definition by ID."""
    svc = OntologyService(test_session)
    created = await svc.create_definition(
        sample_tenant.id,
        CreatePolicyDefinition(name="Test Policy", uri="test-policy"),
    )

    fetched = await svc.get_definition(created.id, sample_tenant.id)
    assert str(fetched.id) == str(created.id)
    assert fetched.name == "Test Policy"


async def test_list_definitions(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Listing definitions returns all definitions for tenant."""
    svc = OntologyService(test_session)
    await svc.create_definition(
        sample_tenant.id, CreatePolicyDefinition(name="Policy A", uri="policy-a")
    )
    await svc.create_definition(
        sample_tenant.id, CreatePolicyDefinition(name="Policy B", uri="policy-b")
    )

    definitions = await svc.list_definitions(sample_tenant.id)
    assert len(definitions) == 2
    assert {d.name for d in definitions} == {"Policy A", "Policy B"}


async def test_list_definitions_filter_by_group(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can filter definitions by group_id."""
    svc = OntologyService(test_session)

    group1 = await svc.create_group(sample_tenant.id, CreatePolicyDefinitionGroup(name="Group 1"))
    group2 = await svc.create_group(sample_tenant.id, CreatePolicyDefinitionGroup(name="Group 2"))

    await svc.create_definition(
        sample_tenant.id,
        CreatePolicyDefinition(name="Policy in Group 1", uri="policy-g1", group_id=group1.id),
    )
    await svc.create_definition(
        sample_tenant.id,
        CreatePolicyDefinition(name="Policy in Group 2", uri="policy-g2", group_id=group2.id),
    )

    # Filter by group1
    definitions = await svc.list_definitions(sample_tenant.id, group_id=group1.id)
    assert len(definitions) == 1
    assert definitions[0].name == "Policy in Group 1"


async def test_list_definitions_filter_by_status(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can filter definitions by status."""
    svc = OntologyService(test_session)

    await svc.create_definition(
        sample_tenant.id,
        CreatePolicyDefinition(name="Active Policy", uri="active", status="active"),
    )
    await svc.create_definition(
        sample_tenant.id,
        CreatePolicyDefinition(name="Inactive Policy", uri="inactive", status="inactive"),
    )

    # Filter by active status
    definitions = await svc.list_definitions(sample_tenant.id, status="active")
    assert len(definitions) == 1
    assert definitions[0].name == "Active Policy"


async def test_update_definition(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can update definition fields."""
    svc = OntologyService(test_session)
    created = await svc.create_definition(
        sample_tenant.id,
        CreatePolicyDefinition(name="Old Name", uri="test-uri", status="active"),
    )

    updated = await svc.update_definition(
        created.id,
        sample_tenant.id,
        UpdatePolicyDefinition(
            name="New Name",
            description="Updated description",
            status="inactive",
        ),
    )
    assert updated.name == "New Name"
    assert updated.description == "Updated description"
    assert updated.status == "inactive"


async def test_delete_definition(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Deleting a definition removes it from database."""
    svc = OntologyService(test_session)
    created = await svc.create_definition(
        sample_tenant.id,
        CreatePolicyDefinition(name="To Delete", uri="to-delete"),
    )

    await svc.delete_definition(created.id, sample_tenant.id)
    await test_session.commit()

    with pytest.raises(NotFoundError):
        await svc.get_definition(created.id, sample_tenant.id)


async def test_seed_definitions(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Can bulk seed definitions. Duplicate URIs are skipped."""
    svc = OntologyService(test_session)

    definitions_to_seed = [
        CreatePolicyDefinition(name="Policy A", uri="policy-a"),
        CreatePolicyDefinition(name="Policy B", uri="policy-b"),
        CreatePolicyDefinition(name="Policy C", uri="policy-c"),
    ]

    created = await svc.seed_definitions(sample_tenant.id, definitions_to_seed)
    assert len(created) == 3

    # Seed again with overlapping URIs
    more_definitions = [
        CreatePolicyDefinition(name="Policy B Updated", uri="policy-b"),  # Duplicate
        CreatePolicyDefinition(name="Policy D", uri="policy-d"),  # New
    ]

    created_second = await svc.seed_definitions(sample_tenant.id, more_definitions)
    # Only policy-d should be created (policy-b already exists)
    assert len(created_second) == 1
    assert created_second[0].uri == "policy-d"

    # Verify total count
    all_definitions = await svc.list_definitions(sample_tenant.id)
    assert len(all_definitions) == 4


async def test_definitions_tenant_isolation(
    test_session: AsyncSession,
    sample_tenant: Tenant,
) -> None:
    """Definitions from one tenant are not visible to another tenant."""
    # Create second tenant
    other_tenant = Tenant(
        id=uuid_utils.uuid7(),
        name="Other Tenant",
        slug="other-tenant",
        industry_vertical="healthcare",
        is_active=True,
    )
    test_session.add(other_tenant)
    await test_session.flush()

    svc = OntologyService(test_session)
    definition = await svc.create_definition(
        sample_tenant.id,
        CreatePolicyDefinition(name="Tenant A Policy", uri="tenant-a-policy"),
    )

    # Attempting to access from other tenant should fail
    with pytest.raises(NotFoundError):
        await svc.get_definition(definition.id, other_tenant.id)

    # Other tenant should see empty list
    other_definitions = await svc.list_definitions(other_tenant.id)
    assert len(other_definitions) == 0
