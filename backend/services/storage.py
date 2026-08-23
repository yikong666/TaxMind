"""MinIO 私有对象存储适配。"""
from typing import BinaryIO, Protocol

from minio import Minio

from backend.core.config import get_settings


class ObjectStorage(Protocol):
    def upload(
        self, object_key: str, stream: BinaryIO, length: int, content_type: str
    ) -> None: ...

    def delete(self, object_key: str) -> None: ...


class MinioObjectStorage:
    def __init__(self, client: Minio, bucket: str):
        self.client = client
        self.bucket = bucket

    def upload(self, object_key: str, stream: BinaryIO, length: int, content_type: str) -> None:
        self.client.put_object(self.bucket, object_key, stream, length, content_type=content_type)

    def delete(self, object_key: str) -> None:
        self.client.remove_object(self.bucket, object_key)


def get_object_storage() -> ObjectStorage:
    settings = get_settings()
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key.get_secret_value(),
        secret_key=settings.minio_secret_key.get_secret_value(),
        secure=settings.minio_secure,
    )
    return MinioObjectStorage(client, settings.minio_bucket)
