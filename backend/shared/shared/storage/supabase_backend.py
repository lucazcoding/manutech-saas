import logging

from supabase import Client, create_client

from ..config import get_shared_settings
from .base import StorageBackend

logger = logging.getLogger(__name__)

_supabase_client: Client | None = None


def _get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        settings = get_shared_settings()
        _supabase_client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase_client


class SupabaseStorageBackend(StorageBackend):
    def __init__(self) -> None:
        self._bucket = get_shared_settings().storage_bucket

    async def upload(self, path: str, content: bytes, mime_type: str) -> str:
        _get_supabase().storage.from_(self._bucket).upload(
            path=path,
            file=content,
            file_options={"content-type": mime_type, "upsert": "false"},
        )
        return path

    async def get_download_url(self, file_path: str) -> str:
        response = _get_supabase().storage.from_(self._bucket).create_signed_url(
            path=file_path,
            expires_in=3600,
        )
        return response["signedURL"]

    async def delete(self, file_path: str) -> None:
        _get_supabase().storage.from_(self._bucket).remove([file_path])
