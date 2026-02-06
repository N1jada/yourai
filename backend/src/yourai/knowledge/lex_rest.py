"""Async REST client for the Lex legislation API."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, TypeVar

import httpx
import structlog
from pydantic import BaseModel, Field

from yourai.knowledge.exceptions import (
    LexConnectionError,
    LexError,
    LexNotFoundError,
    LexTimeoutError,
)

logger = structlog.get_logger()

_M = TypeVar("_M", bound=BaseModel)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LegislationType(StrEnum):
    UKPGA = "ukpga"
    ASP = "asp"
    ASC = "asc"
    ANAW = "anaw"
    WSI = "wsi"
    UKSI = "uksi"
    SSI = "ssi"
    UKCM = "ukcm"
    NISR = "nisr"
    NIA = "nia"
    EUDN = "eudn"
    EUDR = "eudr"
    EUR = "eur"
    UKLA = "ukla"
    UKPPA = "ukppa"
    APNI = "apni"
    GBLA = "gbla"
    AOSP = "aosp"
    AEP = "aep"
    APGB = "apgb"
    MWA = "mwa"
    AIP = "aip"
    MNIA = "mnia"
    NISRO = "nisro"
    NISI = "nisi"
    UKSRO = "uksro"
    UKMO = "ukmo"
    UKCI = "ukci"


class LegislationCategory(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EUROPEAN = "european"
    EU_RETAINED = "euretained"


class GeographicalExtent(StrEnum):
    ENGLAND = "England"
    WALES = "Wales"
    SCOTLAND = "Scotland"
    NORTHERN_IRELAND = "Northern Ireland"
    UNITED_KINGDOM = "United Kingdom"
    EMPTY = ""


class ProvisionType(StrEnum):
    SECTION = "section"
    SCHEDULE = "schedule"


class ExplanatoryNoteType(StrEnum):
    OVERVIEW = "overview"
    POLICY_BACKGROUND = "policy_background"
    LEGAL_BACKGROUND = "legal_background"
    EXTENT = "extent"
    PROVISIONS = "provisions"
    COMMENCEMENT = "commencement"


class ExplanatoryNoteSectionType(StrEnum):
    SECTION = "section"
    SCHEDULE = "schedule"
    PART = "part"


class ProvenanceSource(StrEnum):
    XML = "xml"
    LLM_OCR = "llm_ocr"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class Legislation(BaseModel):
    """A single piece of legislation (Act or Statutory Instrument)."""

    id: str
    uri: str
    title: str
    description: str
    publisher: str
    category: LegislationCategory
    type: LegislationType
    year: int
    number: int
    status: str
    number_of_provisions: int
    text: str = ""
    created_at: datetime | None = None
    enactment_date: date | None = None
    valid_date: date | None = None
    modified_date: date | None = None
    extent: list[GeographicalExtent] = Field(default_factory=list)
    provenance_source: ProvenanceSource | None = None
    provenance_model: str | None = None
    provenance_prompt_version: str | None = None
    provenance_timestamp: datetime | None = None
    provenance_response_id: str | None = None


class LegislationSection(BaseModel):
    """A section within a piece of legislation."""

    id: str
    uri: str
    legislation_id: str
    number: int | None = None
    legislation_type: LegislationType
    legislation_year: int
    legislation_number: int
    text: str = ""
    title: str = ""
    created_at: datetime | None = None
    extent: list[GeographicalExtent] = Field(default_factory=list)
    provision_type: ProvisionType = ProvisionType.SECTION
    provenance_source: ProvenanceSource | None = None
    provenance_model: str | None = None
    provenance_prompt_version: str | None = None
    provenance_timestamp: datetime | None = None
    provenance_response_id: str | None = None


class LegislationFullText(BaseModel):
    """Full text content of a piece of legislation."""

    legislation: Legislation
    full_text: str


class Amendment(BaseModel):
    """An amendment linking affecting and changed legislation."""

    id: str
    changed_legislation: str
    changed_year: int
    changed_number: str
    changed_url: str
    affecting_url: str
    changed_provision: str | None = None
    changed_provision_url: str | None = None
    affecting_legislation: str | None = None
    affecting_year: int | None = None
    affecting_number: str | None = None
    affecting_provision: str | None = None
    affecting_provision_url: str | None = None
    type_of_effect: str | None = None
    ai_explanation: str | None = None
    ai_explanation_model: str | None = None
    ai_explanation_timestamp: datetime | None = None


class ExplanatoryNote(BaseModel):
    """An explanatory note for a piece of legislation."""

    id: str
    legislation_id: str
    text: str
    route: list[str]
    order: int
    created_at: datetime | None = None
    note_type: ExplanatoryNoteType | None = None
    section_type: ExplanatoryNoteSectionType | None = None
    section_number: int | None = None


class LegislationSearchResponse(BaseModel):
    """Paginated search results for legislation."""

    results: list[dict[str, Any]]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT = 30.0


class LexRestClient:
    """Async REST client for the Lex legislation API.

    All endpoints use POST with JSON bodies, matching the Lex API convention.
    """

    def __init__(self, base_url: str, *, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
            headers={"Accept": "application/json"},
        )
        self._log = logger.bind(lex_base_url=self._base_url)

    # ------------------------------------------------------------------
    # Legislation
    # ------------------------------------------------------------------

    async def search_legislation(
        self,
        query: str,
        *,
        year_from: int | None = None,
        year_to: int | None = None,
        legislation_type: list[str] | None = None,
        offset: int = 0,
        limit: int = 10,
        include_text: bool = True,
    ) -> LegislationSearchResponse:
        """Search Acts and Statutory Instruments by title, content, or metadata."""
        body: dict[str, Any] = {
            "query": query,
            "offset": offset,
            "limit": limit,
            "include_text": include_text,
        }
        if year_from is not None:
            body["year_from"] = year_from
        if year_to is not None:
            body["year_to"] = year_to
        if legislation_type is not None:
            body["legislation_type"] = legislation_type
        return await self._post("/legislation/search", body, LegislationSearchResponse)

    async def lookup_legislation(
        self,
        legislation_type: str,
        year: int,
        number: int,
    ) -> Legislation:
        """Retrieve a single Act or SI by citation."""
        body = {
            "legislation_type": legislation_type,
            "year": year,
            "number": number,
        }
        return await self._post("/legislation/lookup", body, Legislation)

    async def get_legislation_sections(
        self,
        legislation_id: str,
        *,
        limit: int = 10,
    ) -> list[LegislationSection]:
        """Get all sections for a specific piece of legislation."""
        body = {"legislation_id": legislation_id, "limit": limit}
        return await self._post_list("/legislation/section/lookup", body, LegislationSection)

    async def get_legislation_full_text(
        self,
        legislation_id: str,
        *,
        include_schedules: bool = False,
    ) -> LegislationFullText:
        """Get the complete text content of a piece of legislation."""
        body = {
            "legislation_id": legislation_id,
            "include_schedules": include_schedules,
        }
        return await self._post("/legislation/text", body, LegislationFullText)

    async def search_legislation_sections(
        self,
        query: str,
        *,
        legislation_id: str | None = None,
        legislation_category: list[str] | None = None,
        legislation_type: list[str] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        offset: int = 0,
        size: int = 10,
        include_text: bool = True,
    ) -> list[LegislationSection]:
        """Find text within legislation sections."""
        body: dict[str, Any] = {
            "query": query,
            "offset": offset,
            "size": size,
            "include_text": include_text,
        }
        if legislation_id is not None:
            body["legislation_id"] = legislation_id
        if legislation_category is not None:
            body["legislation_category"] = legislation_category
        if legislation_type is not None:
            body["legislation_type"] = legislation_type
        if year_from is not None:
            body["year_from"] = year_from
        if year_to is not None:
            body["year_to"] = year_to
        return await self._post_list("/legislation/section/search", body, LegislationSection)

    # ------------------------------------------------------------------
    # Amendments
    # ------------------------------------------------------------------

    async def search_amendments(
        self,
        legislation_id: str,
        *,
        search_amended: bool = True,
        size: int = 100,
    ) -> list[Amendment]:
        """Search amendments by affected legislation."""
        body = {
            "legislation_id": legislation_id,
            "search_amended": search_amended,
            "size": size,
        }
        return await self._post_list("/amendment/search", body, Amendment)

    async def search_amendment_sections(
        self,
        provision_id: str,
        *,
        search_amended: bool = True,
        size: int = 100,
    ) -> list[Amendment]:
        """Search within amendment sections."""
        body = {
            "provision_id": provision_id,
            "search_amended": search_amended,
            "size": size,
        }
        return await self._post_list("/amendment/section/search", body, Amendment)

    # ------------------------------------------------------------------
    # Explanatory notes
    # ------------------------------------------------------------------

    async def search_explanatory_notes(
        self,
        *,
        query: str = "",
        legislation_id: str | None = None,
        note_type: list[str] | None = None,
        section_type: list[str] | None = None,
        size: int = 20,
    ) -> list[ExplanatoryNote]:
        """Find explanatory notes by text content."""
        body: dict[str, Any] = {"query": query, "size": size}
        if legislation_id is not None:
            body["legislation_id"] = legislation_id
        if note_type is not None:
            body["note_type"] = note_type
        if section_type is not None:
            body["section_type"] = section_type
        return await self._post_list("/explanatory_note/section/search", body, ExplanatoryNote)

    async def get_explanatory_notes_by_legislation(
        self,
        legislation_id: str,
        *,
        limit: int = 1000,
    ) -> list[ExplanatoryNote]:
        """Get explanatory notes for a specific piece of legislation."""
        body = {"legislation_id": legislation_id, "limit": limit}
        return await self._post_list("/explanatory_note/legislation/lookup", body, ExplanatoryNote)

    async def get_explanatory_note_by_section(
        self,
        legislation_id: str,
        section_number: int,
    ) -> ExplanatoryNote:
        """Get the explanatory note for a specific section."""
        body = {"legislation_id": legislation_id, "section_number": section_number}
        return await self._post("/explanatory_note/section/lookup", body, ExplanatoryNote)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Check the health of the Lex API."""
        return await self._get("/healthcheck")

    async def get_stats(self) -> dict[str, Any]:
        """Get live dataset statistics."""
        return await self._get("/api/stats")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str) -> dict[str, Any]:
        """Make a GET request and return the JSON response."""
        self._log.debug("lex_rest_get", path=path)
        try:
            resp = await self._client.get(path)
        except httpx.ConnectError as exc:
            raise LexConnectionError(str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise LexTimeoutError(str(exc)) from exc
        self._handle_status(resp)
        result: dict[str, Any] = resp.json()
        return result

    async def _post(self, path: str, body: dict[str, Any], model: type[_M]) -> _M:
        """Make a POST request and parse the response into a Pydantic model."""
        self._log.debug("lex_rest_post", path=path)
        try:
            resp = await self._client.post(path, json=body)
        except httpx.ConnectError as exc:
            raise LexConnectionError(str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise LexTimeoutError(str(exc)) from exc
        self._handle_status(resp)
        return model.model_validate(resp.json())

    async def _post_list(self, path: str, body: dict[str, Any], model: type[_M]) -> list[_M]:
        """Make a POST request and parse the response as a list of Pydantic models."""
        self._log.debug("lex_rest_post_list", path=path)
        try:
            resp = await self._client.post(path, json=body)
        except httpx.ConnectError as exc:
            raise LexConnectionError(str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise LexTimeoutError(str(exc)) from exc
        self._handle_status(resp)
        data = resp.json()
        return [model.model_validate(item) for item in data]

    def _handle_status(self, resp: httpx.Response) -> None:
        """Raise appropriate LexError for non-2xx responses."""
        if resp.is_success:
            return
        if resp.status_code == 404:
            raise LexNotFoundError(
                f"Lex API 404: {resp.request.url}",
                detail={"status_code": resp.status_code, "body": resp.text},
            )
        raise LexError(
            f"Lex API error {resp.status_code}: {resp.text}",
            detail={"status_code": resp.status_code, "body": resp.text},
        )
