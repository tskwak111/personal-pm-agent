"""S3-compatible immutable source byte storage."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from personal_pm_api.settings import ApiSettings


class ObjectStorage(Protocol):
    async def get(self, key: str) -> bytes: ...

    async def put(self, key: str, content: bytes) -> None: ...

    async def delete(self, key: str) -> None: ...


class S3ObjectStorage:
    def __init__(
        self,
        client: Any,
        bucket: str,
        *,
        allow_bucket_creation: bool,
        region: str,
    ) -> None:
        self._client = client
        self._bucket = bucket
        self._allow_bucket_creation = allow_bucket_creation
        self._region = region
        self._bucket_ready = False
        self._bucket_lock = asyncio.Lock()

    @classmethod
    def from_settings(cls, settings: ApiSettings) -> S3ObjectStorage:
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        )
        return cls(
            client,
            settings.s3_bucket,
            allow_bucket_creation=settings.environment in ("local", "test"),
            region=settings.s3_region,
        )

    async def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        async with self._bucket_lock:
            if self._bucket_ready:
                return
            try:
                await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
            except ClientError as error:
                code = str(error.response.get("Error", {}).get("Code", ""))
                if code not in {"404", "NoSuchBucket", "NotFound"}:
                    raise
                if not self._allow_bucket_creation:
                    raise RuntimeError(
                        f"object storage bucket is missing: {self._bucket}"
                    ) from error
                arguments: dict[str, object] = {"Bucket": self._bucket}
                if self._region != "us-east-1":
                    arguments["CreateBucketConfiguration"] = {"LocationConstraint": self._region}
                await asyncio.to_thread(self._client.create_bucket, **arguments)
            self._bucket_ready = True

    async def get(self, key: str) -> bytes:
        await self._ensure_bucket()
        response = await asyncio.to_thread(
            self._client.get_object,
            Bucket=self._bucket,
            Key=key,
        )
        return bytes(await asyncio.to_thread(response["Body"].read))

    async def put(self, key: str, content: bytes) -> None:
        await self._ensure_bucket()
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=content,
        )

    async def delete(self, key: str) -> None:
        await self._ensure_bucket()
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=key,
        )


__all__ = ["ObjectStorage", "S3ObjectStorage"]
