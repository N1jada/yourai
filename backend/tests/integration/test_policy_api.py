"""Integration tests for policy ontology API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPolicyGroupsAPI:
    """Tests for policy definition groups API endpoints."""

    async def test_create_group(self, async_client: AsyncClient) -> None:
        """POST /api/v1/policy/groups creates a new group."""
        response = await async_client.post(
            "/api/v1/policy/groups",
            json={
                "name": "Operational Policies",
                "description": "Day-to-day operational policies",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Operational Policies"
        assert data["description"] == "Day-to-day operational policies"
        assert "id" in data
        assert "tenant_id" in data

    async def test_list_groups(self, async_client: AsyncClient) -> None:
        """GET /api/v1/policy/groups returns all groups for tenant."""
        # Create two groups
        await async_client.post("/api/v1/policy/groups", json={"name": "Group A"})
        await async_client.post("/api/v1/policy/groups", json={"name": "Group B"})

        response = await async_client.get("/api/v1/policy/groups")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        names = {g["name"] for g in data}
        assert "Group A" in names
        assert "Group B" in names

    async def test_get_group(self, async_client: AsyncClient) -> None:
        """GET /api/v1/policy/groups/{id} returns a specific group."""
        create_response = await async_client.post(
            "/api/v1/policy/groups", json={"name": "Test Group"}
        )
        group_id = create_response.json()["id"]

        response = await async_client.get(f"/api/v1/policy/groups/{group_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == group_id
        assert data["name"] == "Test Group"

    async def test_update_group(self, async_client: AsyncClient) -> None:
        """PATCH /api/v1/policy/groups/{id} updates a group."""
        create_response = await async_client.post(
            "/api/v1/policy/groups", json={"name": "Old Name"}
        )
        group_id = create_response.json()["id"]

        response = await async_client.patch(
            f"/api/v1/policy/groups/{group_id}",
            json={"name": "New Name", "description": "Updated"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "Updated"

    async def test_delete_group(self, async_client: AsyncClient) -> None:
        """DELETE /api/v1/policy/groups/{id} deletes a group."""
        create_response = await async_client.post(
            "/api/v1/policy/groups", json={"name": "To Delete"}
        )
        group_id = create_response.json()["id"]

        response = await async_client.delete(f"/api/v1/policy/groups/{group_id}")
        assert response.status_code == 204

        # Verify deletion
        get_response = await async_client.get(f"/api/v1/policy/groups/{group_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
class TestPolicyTopicsAPI:
    """Tests for policy definition topics API endpoints."""

    async def test_create_topic(self, async_client: AsyncClient) -> None:
        """POST /api/v1/policy/topics creates a new topic."""
        response = await async_client.post(
            "/api/v1/policy/topics",
            json={"name": "Safeguarding"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Safeguarding"
        assert "id" in data

    async def test_list_topics(self, async_client: AsyncClient) -> None:
        """GET /api/v1/policy/topics returns all topics for tenant."""
        await async_client.post("/api/v1/policy/topics", json={"name": "Topic A"})
        await async_client.post("/api/v1/policy/topics", json={"name": "Topic B"})

        response = await async_client.get("/api/v1/policy/topics")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        names = {t["name"] for t in data}
        assert "Topic A" in names
        assert "Topic B" in names

    async def test_get_topic(self, async_client: AsyncClient) -> None:
        """GET /api/v1/policy/topics/{id} returns a specific topic."""
        create_response = await async_client.post(
            "/api/v1/policy/topics", json={"name": "Test Topic"}
        )
        topic_id = create_response.json()["id"]

        response = await async_client.get(f"/api/v1/policy/topics/{topic_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == topic_id
        assert data["name"] == "Test Topic"

    async def test_update_topic(self, async_client: AsyncClient) -> None:
        """PATCH /api/v1/policy/topics/{id} updates a topic."""
        create_response = await async_client.post(
            "/api/v1/policy/topics", json={"name": "Old Topic"}
        )
        topic_id = create_response.json()["id"]

        response = await async_client.patch(
            f"/api/v1/policy/topics/{topic_id}",
            json={"name": "New Topic"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Topic"

    async def test_delete_topic(self, async_client: AsyncClient) -> None:
        """DELETE /api/v1/policy/topics/{id} deletes a topic."""
        create_response = await async_client.post(
            "/api/v1/policy/topics", json={"name": "To Delete"}
        )
        topic_id = create_response.json()["id"]

        response = await async_client.delete(f"/api/v1/policy/topics/{topic_id}")
        assert response.status_code == 204

        get_response = await async_client.get(f"/api/v1/policy/topics/{topic_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
class TestPolicyDefinitionsAPI:
    """Tests for policy definitions API endpoints."""

    async def test_create_definition(self, async_client: AsyncClient) -> None:
        """POST /api/v1/policy/definitions creates a new definition."""
        response = await async_client.post(
            "/api/v1/policy/definitions",
            json={
                "name": "Health & Safety Policy",
                "uri": "health-and-safety-policy",
                "description": "Covers workplace safety",
                "is_required": True,
                "review_cycle": "annual",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Health & Safety Policy"
        assert data["uri"] == "health-and-safety-policy"
        assert data["is_required"] is True
        assert data["review_cycle"] == "annual"

    async def test_create_definition_with_criteria(self, async_client: AsyncClient) -> None:
        """Can create definition with compliance and scoring criteria."""
        response = await async_client.post(
            "/api/v1/policy/definitions",
            json={
                "name": "Complex Policy",
                "uri": "complex-policy",
                "compliance_criteria": [
                    {
                        "name": "HSWA 1974 Compliance",
                        "priority": "high",
                        "description": "Must comply with Health & Safety at Work Act 1974",
                        "criteria_type": "mandatory",
                    }
                ],
                "scoring_criteria": [
                    {
                        "criterion": "Risk Assessment",
                        "green_threshold": "Comprehensive process",
                        "amber_threshold": "Basic process",
                        "red_threshold": "No process",
                    }
                ],
                "required_sections": ["Policy Statement", "Procedures"],
                "legislation_references": [
                    {
                        "act_name": "Health and Safety at Work etc. Act 1974",
                        "section": "s.2",
                        "notes": "Employer's duty",
                    }
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["compliance_criteria"]) == 1
        assert len(data["scoring_criteria"]) == 1
        assert len(data["required_sections"]) == 2
        assert len(data["legislation_references"]) == 1

    async def test_create_definition_with_group_and_topics(self, async_client: AsyncClient) -> None:
        """Can create definition with group and topics."""
        # Create group and topics
        group_resp = await async_client.post("/api/v1/policy/groups", json={"name": "Test Group"})
        group_id = group_resp.json()["id"]

        topic1_resp = await async_client.post("/api/v1/policy/topics", json={"name": "Topic 1"})
        topic1_id = topic1_resp.json()["id"]

        topic2_resp = await async_client.post("/api/v1/policy/topics", json={"name": "Topic 2"})
        topic2_id = topic2_resp.json()["id"]

        # Create definition with group and topics
        response = await async_client.post(
            "/api/v1/policy/definitions",
            json={
                "name": "Test Policy",
                "uri": "test-policy-with-relations",
                "group_id": group_id,
                "topic_ids": [topic1_id, topic2_id],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["group_id"] == group_id
        assert len(data["topics"]) == 2
        topic_ids = {t["id"] for t in data["topics"]}
        assert topic1_id in topic_ids
        assert topic2_id in topic_ids

    async def test_create_definition_duplicate_uri_fails(self, async_client: AsyncClient) -> None:
        """Creating definition with duplicate URI returns 409."""
        await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "Policy A", "uri": "duplicate-uri"},
        )

        response = await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "Policy B", "uri": "duplicate-uri"},
        )
        assert response.status_code == 409

    async def test_list_definitions(self, async_client: AsyncClient) -> None:
        """GET /api/v1/policy/definitions returns all definitions."""
        await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "Policy A", "uri": "policy-a"},
        )
        await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "Policy B", "uri": "policy-b"},
        )

        response = await async_client.get("/api/v1/policy/definitions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        names = {d["name"] for d in data}
        assert "Policy A" in names
        assert "Policy B" in names

    async def test_list_definitions_filter_by_group(self, async_client: AsyncClient) -> None:
        """Can filter definitions by group_id."""
        group1_resp = await async_client.post("/api/v1/policy/groups", json={"name": "Group 1"})
        group1_id = group1_resp.json()["id"]

        group2_resp = await async_client.post("/api/v1/policy/groups", json={"name": "Group 2"})
        group2_id = group2_resp.json()["id"]

        await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "Policy G1", "uri": "policy-g1", "group_id": group1_id},
        )
        await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "Policy G2", "uri": "policy-g2", "group_id": group2_id},
        )

        response = await async_client.get(f"/api/v1/policy/definitions?group_id={group1_id}")
        assert response.status_code == 200
        data = response.json()
        assert all(d["group_id"] == group1_id for d in data)

    async def test_list_definitions_filter_by_status(self, async_client: AsyncClient) -> None:
        """Can filter definitions by status."""
        await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "Active", "uri": "active", "status": "active"},
        )
        await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "Inactive", "uri": "inactive", "status": "inactive"},
        )

        response = await async_client.get("/api/v1/policy/definitions?status_filter=active")
        assert response.status_code == 200
        data = response.json()
        assert all(d["status"] == "active" for d in data)

    async def test_get_definition(self, async_client: AsyncClient) -> None:
        """GET /api/v1/policy/definitions/{id} returns a specific definition."""
        create_response = await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "Test Policy", "uri": "test-policy-get"},
        )
        definition_id = create_response.json()["id"]

        response = await async_client.get(f"/api/v1/policy/definitions/{definition_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == definition_id
        assert data["name"] == "Test Policy"

    async def test_update_definition(self, async_client: AsyncClient) -> None:
        """PATCH /api/v1/policy/definitions/{id} updates a definition."""
        create_response = await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "Old Name", "uri": "update-test", "status": "active"},
        )
        definition_id = create_response.json()["id"]

        response = await async_client.patch(
            f"/api/v1/policy/definitions/{definition_id}",
            json={
                "name": "New Name",
                "description": "Updated description",
                "status": "inactive",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "Updated description"
        assert data["status"] == "inactive"

    async def test_delete_definition(self, async_client: AsyncClient) -> None:
        """DELETE /api/v1/policy/definitions/{id} deletes a definition."""
        create_response = await async_client.post(
            "/api/v1/policy/definitions",
            json={"name": "To Delete", "uri": "to-delete-def"},
        )
        definition_id = create_response.json()["id"]

        response = await async_client.delete(f"/api/v1/policy/definitions/{definition_id}")
        assert response.status_code == 204

        get_response = await async_client.get(f"/api/v1/policy/definitions/{definition_id}")
        assert get_response.status_code == 404

    async def test_seed_definitions(self, async_client: AsyncClient) -> None:
        """POST /api/v1/policy/definitions/seed bulk creates definitions."""
        response = await async_client.post(
            "/api/v1/policy/definitions/seed",
            json={
                "definitions": [
                    {"name": "Seed Policy A", "uri": "seed-a"},
                    {"name": "Seed Policy B", "uri": "seed-b"},
                    {"name": "Seed Policy C", "uri": "seed-c"},
                ]
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3

        # Seed again with overlapping URIs
        response2 = await async_client.post(
            "/api/v1/policy/definitions/seed",
            json={
                "definitions": [
                    {"name": "Seed Policy B Updated", "uri": "seed-b"},  # Duplicate
                    {"name": "Seed Policy D", "uri": "seed-d"},  # New
                ]
            },
        )
        assert response2.status_code == 201
        data2 = response2.json()
        # Only seed-d should be created
        assert len(data2) == 1
        assert data2[0]["uri"] == "seed-d"


@pytest.mark.asyncio
class TestPolicyTypeIdentificationAPI:
    """Tests for policy type identification endpoint."""

    @patch("yourai.api.routes.policy_ontology.AsyncAnthropic")
    @patch("yourai.api.routes.policy_ontology.PolicyTypeIdentifier")
    async def test_identify_policy_type(
        self,
        mock_identifier_cls,
        mock_anthropic_cls,
        async_client: AsyncClient,
    ) -> None:
        """POST /api/v1/policy/identify classifies document text."""
        # Create a definition to match against
        await async_client.post(
            "/api/v1/policy/definitions",
            json={
                "name": "Health & Safety Policy",
                "uri": "health-and-safety-policy",
                "status": "active",
            },
        )

        # Mock the identifier response
        mock_identifier = AsyncMock()
        mock_identifier.identify_policy_type = AsyncMock(
            return_value=Mock(
                matched_definition_id="some-uuid",
                matched_definition_uri="health-and-safety-policy",
                matched_definition_name="Health & Safety Policy",
                confidence=0.92,
                reasoning="Document discusses risk assessments",
                alternative_matches=[],
            )
        )
        mock_identifier_cls.return_value = mock_identifier

        response = await async_client.post(
            "/api/v1/policy/identify",
            json={
                "document_text": """
                Health and Safety Policy

                1. Policy Statement
                Our organization is committed to providing a safe working environment...

                2. Risk Assessment
                All work activities must be subject to risk assessment...
                """
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["matched_definition_uri"] == "health-and-safety-policy"
        assert data["matched_definition_name"] == "Health & Safety Policy"
        assert data["confidence"] == 0.92
        assert "risk assessments" in data["reasoning"].lower()

    @patch("yourai.api.routes.policy_ontology.AsyncAnthropic")
    @patch("yourai.api.routes.policy_ontology.PolicyTypeIdentifier")
    async def test_identify_policy_type_no_match(
        self,
        mock_identifier_cls,
        mock_anthropic_cls,
        async_client: AsyncClient,
    ) -> None:
        """Identification returns null when no clear match found."""
        mock_identifier = AsyncMock()
        mock_identifier.identify_policy_type = AsyncMock(
            return_value=Mock(
                matched_definition_id=None,
                matched_definition_uri=None,
                matched_definition_name=None,
                confidence=0.42,
                reasoning="No clear match found",
                alternative_matches=[],
            )
        )
        mock_identifier_cls.return_value = mock_identifier

        response = await async_client.post(
            "/api/v1/policy/identify",
            json={"document_text": "Staff Handbook - General information"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["matched_definition_uri"] is None
        assert data["confidence"] == 0.42

    async def test_identify_policy_type_requires_text(self, async_client: AsyncClient) -> None:
        """Identification requires document_text parameter."""
        response = await async_client.post(
            "/api/v1/policy/identify",
            json={},
        )
        assert response.status_code == 422  # Validation error
