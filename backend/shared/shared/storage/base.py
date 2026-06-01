from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, path: str, content: bytes, mime_type: str) -> str:
        """Faz upload do arquivo e retorna o file_path para salvar no banco."""
        ...

    @abstractmethod
    async def get_download_url(self, file_path: str) -> str:
        """Retorna URL assinada ou stream para download."""
        ...

    @abstractmethod
    async def delete(self, file_path: str) -> None:
        """Remove o arquivo do storage."""
        ...
