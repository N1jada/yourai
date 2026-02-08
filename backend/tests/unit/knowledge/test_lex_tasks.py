"""Unit tests for Lex ingestion tasks."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from yourai.knowledge.models import IngestionJobStatus, IngestionMode


class _AsyncLineIter:
    """Async iterator over a list of bytes lines, mimicking asyncio.StreamReader."""

    def __init__(self, lines: list[bytes]) -> None:
        self._lines = list(lines)
        self._idx = 0

    def __aiter__(self) -> _AsyncLineIter:
        return self

    async def __anext__(self) -> bytes:
        if self._idx >= len(self._lines):
            raise StopAsyncIteration
        line = self._lines[self._idx]
        self._idx += 1
        return line


class TestRunIngestion:
    """Tests for the _run_ingestion async function."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        s = MagicMock()
        s.database_url = "sqlite+aiosqlite://"
        s.lex_pipeline_container = "lex-pipeline"
        s.redis_url = "redis://localhost:6379/0"
        return s

    @pytest.fixture
    def fake_job(self) -> MagicMock:
        job = MagicMock()
        job.id = UUID("01234567-0123-0123-0123-0123456789ab")
        job.mode = IngestionMode.DAILY
        job.status = IngestionJobStatus.PENDING
        job.parameters = {}
        job.started_at = None
        job.completed_at = None
        job.error_message = None
        job.result = None
        return job

    async def test_builds_correct_command_daily(self) -> None:
        """Verify the docker exec command is built correctly for daily mode."""
        from yourai.knowledge.lex_tasks import _run_ingestion

        job_id = "01234567-0123-0123-0123-0123456789ab"
        tenant_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        user_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

        captured_cmd: list[str] = []

        async def mock_subprocess(*args: Any, **kwargs: Any) -> MagicMock:
            captured_cmd.extend(args)
            proc = MagicMock()
            proc.stdout = _AsyncLineIter([])
            proc.wait = AsyncMock(return_value=0)
            return proc

        # Mock everything to avoid real DB/Redis connections
        mock_job = MagicMock()
        mock_job.mode = "daily"
        mock_job.parameters = {}
        mock_job.status = IngestionJobStatus.PENDING
        mock_job.started_at = None
        mock_job.result = None
        mock_job.error_message = None
        mock_job.completed_at = None

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = mock_job
        mock_result.scalar_one_or_none.return_value = mock_job
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()

        mock_session_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        import structlog

        log = structlog.get_logger().bind(tenant_id=tenant_id, user_id=user_id, job_id=job_id)

        with (
            patch(
                "yourai.knowledge.lex_tasks.asyncio.create_subprocess_exec",
                side_effect=mock_subprocess,
            ),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_session_factory),
            patch("yourai.knowledge.lex_tasks._publish_event", new_callable=AsyncMock),
        ):
            await _run_ingestion(job_id, tenant_id, user_id, log)

        # Verify docker exec command was built
        assert "docker" in captured_cmd
        assert "exec" in captured_cmd
        assert "--mode" in captured_cmd
        assert "daily" in captured_cmd

    async def test_job_status_transitions(self) -> None:
        """Verify job status goes pending -> running -> completed on success."""
        from yourai.knowledge.lex_tasks import _run_ingestion

        job_id = "01234567-0123-0123-0123-0123456789ab"
        tenant_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        user_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

        status_transitions: list[str] = []

        class FakeJob:
            def __init__(self) -> None:
                self.mode = "daily"
                self.parameters: dict[str, Any] = {}
                self._status = IngestionJobStatus.PENDING
                self.started_at = None
                self.completed_at = None
                self.error_message = None
                self.result: dict[str, Any] | None = None

            @property
            def status(self) -> str:
                return self._status

            @status.setter
            def status(self, val: str) -> None:
                status_transitions.append(val)
                self._status = val

        fake_job = FakeJob()

        async def fake_subprocess(*args: Any, **kwargs: Any) -> MagicMock:
            proc = MagicMock()
            proc.stdout = _AsyncLineIter([b"Processing...\n", b"Done.\n"])
            proc.wait = AsyncMock(return_value=0)
            return proc

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = fake_job
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_session_factory = MagicMock(return_value=mock_session)
        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        import structlog

        log = structlog.get_logger().bind(tenant_id=tenant_id, user_id=user_id, job_id=job_id)

        with (
            patch(
                "yourai.knowledge.lex_tasks.asyncio.create_subprocess_exec",
                side_effect=fake_subprocess,
            ),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_session_factory),
            patch("yourai.knowledge.lex_tasks._publish_event", new_callable=AsyncMock),
        ):
            await _run_ingestion(job_id, tenant_id, user_id, log)

        assert status_transitions == [IngestionJobStatus.RUNNING, IngestionJobStatus.COMPLETED]
        assert fake_job.started_at is not None
        assert fake_job.completed_at is not None
        assert fake_job.result is not None
        assert fake_job.result["return_code"] == 0

    async def test_failure_sets_error(self) -> None:
        """Verify job status goes to failed on non-zero exit code."""
        from yourai.knowledge.lex_tasks import _run_ingestion

        job_id = "01234567-0123-0123-0123-0123456789ab"
        tenant_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        user_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

        class FakeJob:
            def __init__(self) -> None:
                self.mode = "full"
                self.parameters: dict[str, Any] = {}
                self.status = IngestionJobStatus.PENDING
                self.started_at = None
                self.completed_at = None
                self.error_message: str | None = None
                self.result: dict[str, Any] | None = None

        fake_job = FakeJob()

        async def fake_subprocess(*args: Any, **kwargs: Any) -> MagicMock:
            proc = MagicMock()
            proc.stdout = _AsyncLineIter([b"Error: connection refused\n"])
            proc.wait = AsyncMock(return_value=1)
            return proc

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = fake_job
        mock_session.execute.return_value = mock_result
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_session_factory = MagicMock(return_value=mock_session)
        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        import structlog

        log = structlog.get_logger().bind(tenant_id=tenant_id, user_id=user_id, job_id=job_id)

        with (
            patch(
                "yourai.knowledge.lex_tasks.asyncio.create_subprocess_exec",
                side_effect=fake_subprocess,
            ),
            patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
            patch("sqlalchemy.ext.asyncio.async_sessionmaker", return_value=mock_session_factory),
            patch("yourai.knowledge.lex_tasks._publish_event", new_callable=AsyncMock),
        ):
            await _run_ingestion(job_id, tenant_id, user_id, log)

        assert fake_job.status == IngestionJobStatus.FAILED
        assert fake_job.error_message is not None
        assert "connection refused" in fake_job.error_message
