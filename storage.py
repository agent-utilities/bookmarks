#!/usr/bin/env python3

from abc import ABC, abstractmethod
import os
import requests
import click

class StorageBackend(ABC):
    """Base class for storage backends"""

    @abstractmethod
    def create_object(self, collection_id: str, data: dict, name: str = None) -> dict:
        """Create a new object in the specified collection"""
        pass

    @abstractmethod
    def read_object(self, collection_id: str, object_id: str) -> dict:
        """Read an object from the specified collection"""
        pass

    @abstractmethod
    def update_object(self, collection_id: str, object_id: str, data: dict) -> dict:
        """Update an object in the specified collection"""
        pass

    @abstractmethod
    def delete_object(self, collection_id: str, object_id: str) -> dict:
        """Delete an object from the specified collection"""
        pass

    @abstractmethod
    def list_objects(self, collection_id: str, ascending: bool = False, last_id: str = None) -> list:
        """List objects in the specified collection"""
        pass

class JsonBinBackend(StorageBackend):
    """JsonBin.io storage backend implementation"""

    def __init__(self, api_key: str, access_key: str, base_url: str = "https://api.jsonbin.io/v3"):
        self.api_key = api_key
        self.access_key = access_key
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'X-Master-Key': self.api_key,
            'X-Access-Key': self.access_key
        }

    def create_object(self, collection_id: str, data: dict, name: str = None) -> dict:
        headers = self.headers.copy()
        if name:
            if len(name) > 128:
                raise click.ClickException("Name must be 128 characters or less")
            headers['X-Bin-Name'] = name

        headers['X-Bin-Private'] = 'true'
        headers['X-Collection-Id'] = collection_id

        response = requests.post(
            f"{self.base_url}/b",
            json=data,
            headers=headers
        )

        if response.status_code == 200:
            return response.json()
        raise click.ClickException(f"Failed to create object: {response.text}")

    def read_object(self, collection_id: str, object_id: str) -> dict:
        response = requests.get(
            f"{self.base_url}/b/{object_id}/latest",
            headers=self.headers
        )

        if response.status_code == 200:
            return response.json()
        raise click.ClickException(f"Failed to read object: {response.text}")

    def update_object(self, collection_id: str, object_id: str, data: dict) -> dict:
        response = requests.put(
            f"{self.base_url}/b/{object_id}",
            json=data,
            headers=self.headers
        )

        if response.status_code == 200:
            return response.json()
        raise click.ClickException(f"Failed to update object: {response.text}")

    def delete_object(self, collection_id: str, object_id: str) -> dict:
        response = requests.delete(
            f"{self.base_url}/b/{object_id}",
            headers=self.headers
        )

        if response.status_code == 200:
            return response.json()
        raise click.ClickException(f"Failed to delete object: {response.text}")

    def list_objects(self, collection_id: str, ascending: bool = False, last_id: str = None) -> list:
        headers = self.headers.copy()
        if ascending:
            headers['X-Sort-Order'] = 'ascending'

        url = f"{self.base_url}/c/{collection_id}/bins"
        if last_id:
            url = f"{url}/{last_id}"

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        raise click.ClickException(f"Failed to list objects: {response.text}")

class SupabaseBackend(StorageBackend):
    """Supabase storage backend implementation"""

    def __init__(self, anon_key: str, url: str):
        from supabase import create_client
        self.client = create_client(url, anon_key)

    def create_object(self, collection_id: str, data: dict, name: str = None) -> dict:
        if name:
            data['name'] = name

        data['collection_id'] = collection_id
        response = self.client.table('bookmarks').insert(data).execute()

        if len(response.data) > 0:
            return response.data[0]
        raise click.ClickException("Failed to create bookmark")

    def read_object(self, collection_id: str, object_id: str) -> dict:
        response = self.client.table('bookmarks')\
            .select('*')\
            .eq('id', object_id)\
            .eq('collection_id', collection_id)\
            .execute()

        if len(response.data) > 0:
            return response.data[0]
        raise click.ClickException("Bookmark not found")

    def update_object(self, collection_id: str, object_id: str, data: dict) -> dict:
        response = self.client.table('bookmarks')\
            .update(data)\
            .eq('id', object_id)\
            .eq('collection_id', collection_id)\
            .execute()

        if len(response.data) > 0:
            return response.data[0]
        raise click.ClickException("Failed to update bookmark")

    def delete_object(self, collection_id: str, object_id: str) -> dict:
        response = self.client.table('bookmarks')\
            .delete()\
            .eq('id', object_id)\
            .eq('collection_id', collection_id)\
            .execute()

        if len(response.data) > 0:
            return response.data[0]
        raise click.ClickException("Failed to delete bookmark")

    def list_objects(self, collection_id: str, ascending: bool = False, last_id: str = None) -> list:
        query = self.client.table('bookmarks')\
            .select('*')\
            .eq('collection_id', collection_id)

        if ascending:
            query = query.order('created_at', desc=False)
        else:
            query = query.order('created_at', desc=True)

        if last_id:
            if ascending:
                query = query.gt('id', last_id)
            else:
                query = query.lt('id', last_id)

        response = query.execute()
        return response.data

class StorageManager:
    """Storage manager that handles different backend implementations"""

    BACKENDS = {
        'jsonbin': JsonBinBackend,
        'supabase': SupabaseBackend
    }

    def __init__(self, config: dict):
        self.config = config
        self.backends = {}

        # Initialize backends based on collection configs
        for collection_name, collection_config in config['collections'].items():
            backend_type = collection_config.get('backend', 'supabase')
            if backend_type not in self.BACKENDS:
                raise click.ClickException(f"Unsupported backend type: {backend_type}")

            if backend_type not in self.backends:
                if backend_type == 'jsonbin':
                    api_key = os.getenv('JSONBIN_API_KEY')
                    access_key = os.getenv('JSONBIN_ACCESS_KEY')
                    if not api_key or not access_key:
                        raise click.ClickException("JSONBIN_API_KEY and JSONBIN_ACCESS_KEY required")
                    self.backends[backend_type] = JsonBinBackend(api_key, access_key)
                elif backend_type == 'supabase':
                    anon_key = os.getenv('SUPABASE_ANON_PASSWORD')
                    url = os.getenv('SUPABASE_URL')
                    if not anon_key or not url:
                        raise click.ClickException("SUPABASE_ANON_PASSWORD and SUPABASE_URL required")
                    self.backends[backend_type] = SupabaseBackend(anon_key, url)

    def get_backend(self, collection_name: str) -> StorageBackend:
        """Get the appropriate backend for a collection"""
        collection_config = self.config['collections'].get(collection_name)
        if not collection_config:
            raise click.ClickException(f"Collection not found: {collection_name}")

        backend_type = collection_config.get('backend', 'jsonbin')
        return self.backends[backend_type]
