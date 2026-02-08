"""Celery application factory."""

from celery import Celery

from yourai.core.config import settings

celery_app = Celery(
    "yourai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "knowledge.*": {"queue": "knowledge_ingest"},
        "lex.*": {"queue": "knowledge_ingest"},
    },
)
