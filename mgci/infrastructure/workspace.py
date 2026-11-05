"""Workspace boundary for installed pysepal versions without a filesystem facade."""

import logging
import asyncio

from mgci.errors import LocalizedError

log = logging.getLogger('MGCI.infrastructure.workspace')


class ClientWorkspace:
    def __init__(self, client):
        if client is None:
            raise LocalizedError('workspace_required')
        self.client = client

    async def read_bytes_async(self, path: str) -> bytes:
        log.debug('Workspace read %s', path)
        return await asyncio.to_thread(self.client.files.read_bytes, path)

    async def write_async(self, path: str, content, *, overwrite=False):
        log.debug('Workspace write %s', path)
        return await asyncio.to_thread(self.client.files.write, path, content, overwrite=overwrite)

    async def mkdir_async(self, path: str, *, parents=False):
        log.debug('Workspace mkdir %s', path)
        return await asyncio.to_thread(self.client.files.mkdir, path, parents=parents)

