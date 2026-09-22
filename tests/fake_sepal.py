"""In-memory SEPAL user-files API, served to the real pysepal_api endpoint.

Only the network is faked: requests are built, sent and error-mapped by
``pysepal_api``'s own ``UserFilesEndpoint``, so module code that calls a method
the real client does not have fails here exactly as it would on SEPAL.
"""

from email.parser import BytesParser
from email.policy import HTTP
from types import SimpleNamespace

import httpx
from pysepal_api.endpoints.user_files import UserFilesEndpoint


class FakeUserFiles:
    """The three user-files routes the module uses, keyed by the path the client sends."""

    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.folders: set[str] = set()

    def handle(self, request: httpx.Request) -> httpx.Response:
        route, path = request.url.path, request.url.params.get("path")

        if route == "/api/user-files/createFolder":
            self.folders.add(path)
            return httpx.Response(200, json={})

        if route == "/api/user-files/setFile":
            if path in self.files and request.url.params["overwrite"] != "true":
                return httpx.Response(409, json={"message": "file exists"})
            self.files[path] = _uploaded_file(request)
            return httpx.Response(200, json={})

        if route == "/api/user-files/download":
            if path not in self.files:
                return httpx.Response(404, json={"message": "not found"})
            return httpx.Response(200, content=self.files[path])

        return httpx.Response(501, json={"message": f"{route} is not faked"})


def _uploaded_file(request: httpx.Request) -> bytes:
    head = f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode()
    message = BytesParser(policy=HTTP).parsebytes(head + request.content)
    part = next(
        p
        for p in message.iter_parts()
        if p.get_param("name", header="content-disposition") == "file"
    )
    return part.get_payload(decode=True)


def fake_sepal_client():
    """Return ``(client, server)``: a client exposing the real ``files`` API, and its store."""
    server = FakeUserFiles()
    http = httpx.Client(
        base_url="https://sepal.test", transport=httpx.MockTransport(server.handle)
    )
    return SimpleNamespace(files=UserFilesEndpoint(http)), server
