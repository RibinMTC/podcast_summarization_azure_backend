import datetime
import os
from typing import Protocol,  Any
import uuid

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions


class StorageServiceInterface(Protocol):
    """Protocol for storage services."""

    async def upload_file(self, file: Any, container_name: str) -> str:
        """
        Upload a file to storage.

        Args:
            file_path: Path to the file to upload
            container_name: Name of the container to upload to

        Returns:
            URL to the uploaded file
        """
        ...


class AzureBlobStorageService:
    """Azure Blob Storage implementation."""

    def __init__(self, connection_string: str):
        """
        Initialize with Azure Storage connection string.

        Args:
            connection_string: Azure Storage connection string
        """
        self.connection_string = connection_string

    async def upload_to_blob_storage(self, file, container_name: str, sas_hours_valid: float = 1) -> str:
        # Initialize blob client
        blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string)
        container_client = blob_service_client.get_container_client(
            container_name)

        # Create container if needed
        if not container_client.exists():
            container_client.create_container()

        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        print(unique_filename)
        blob_client = container_client.get_blob_client(unique_filename)

        # Read file and upload in chunks
        CHUNK_SIZE = 4 * 1024 * 1024  # 4MB chunks

        # Create the blob
        blob_client.create_append_blob()

        # Stream upload in chunks to avoid memory issues
        file_stream = file.stream
        chunk = file_stream.read(CHUNK_SIZE)

        while chunk:
            blob_client.append_block(chunk)
            chunk = file_stream.read(CHUNK_SIZE)

        # Generate SAS token
        expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=sas_hours_valid)
        account_name = blob_service_client.account_name
        account_key = blob_service_client.credential.account_key

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container_name,
            blob_name=unique_filename,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry
        )

        # Return the full URL with SAS token (without token, the file cannot be accessed by other apis)
        return f"{blob_client.url}?{sas_token}"

    async def delete_blob_storage(self, container_name: str) -> None:
        # Initialize blob client
        blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string)
        container_client = blob_service_client.get_container_client(
            container_name)
        # Create container if needed
        if not container_client.exists():
            return
        container_client.delete_container()


class LocalFileStorageService:
    """Local file storage implementation for testing."""

    def __init__(self, base_path: str = "/tmp/local_storage"):
        """
        Initialize with base storage path.

        Args:
            base_path: Base path for storing files
        """
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    async def upload_file(self, file_path: str, container_name: str) -> str:
        """Store a copy of the file in a local directory."""
        container_path = os.path.join(self.base_path, container_name)
        os.makedirs(container_path, exist_ok=True)

        destination = os.path.join(container_path, os.path.basename(file_path))

        # Copy the file
        with open(file_path, 'rb') as src, open(destination, 'wb') as dst:
            dst.write(src.read())

        return f"file://{destination}"
