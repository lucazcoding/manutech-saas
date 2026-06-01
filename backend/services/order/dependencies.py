from fastapi import Depends

from shared.shared.config import SharedSettings, get_shared_settings
from shared.shared.storage.base import StorageBackend


async def get_storage(settings: SharedSettings = Depends(get_shared_settings)) -> StorageBackend:
    from shared.shared.storage.supabase_backend import SupabaseStorageBackend
    return SupabaseStorageBackend()
