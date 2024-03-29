import random
import ssl
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, List, Optional, Union

from httpcore import URL, AsyncNetworkBackend, Origin, Request, Response
from httpcore._async import AsyncConnectionInterface
from httpcore._async.http_proxy import (
    AsyncForwardHTTPConnection,
    AsyncTunnelHTTPConnection,
)
from httpcore._async.socks_proxy import AsyncSocks5Connection
from httpcore._exceptions import ConnectError, ConnectTimeout
from httpcore._models import Extensions
from httpcore._models import HeaderTypes as HttpcoreHeaderTypes
from httpx._types import ProxyTypes

from .raw_proxy import RawProxy

_CONNECTION_TYPES = Union[
    AsyncForwardHTTPConnection, AsyncTunnelHTTPConnection, AsyncSocks5Connection
]
ProxyFactoryType = Callable[[Origin], Union[ProxyTypes, RawProxy]]


class ProxyConnection(AsyncConnectionInterface):
    def __init__(
        self,
        proxies: Union[List[RawProxy], ProxyFactoryType],
        origin: Origin,
        retries: int = 0,
        always_update: bool = False,
        ssl_context: Optional[ssl.SSLContext] = None,
        keepalive_expiry: Optional[float] = None,
        http1: bool = True,
        http2: bool = False,
        network_backend: Optional[AsyncNetworkBackend] = None,
    ):
        assert retries >= 0, "retries must be >= 0"
        self._proxies = proxies
        self._origin = origin
        self._retries = retries
        self._always_update = always_update
        self._ssl_context = ssl_context
        self._keepalive_expiry = keepalive_expiry
        self._http1 = http1
        self._http2 = http2
        self._network_backend = network_backend

        self._conn = self.update_connection()

    def _get_proxy(self) -> RawProxy:
        if callable(self._proxies):
            return RawProxy.cast(self._proxies(self._origin))
        return random.choice(self._proxies)

    def _get_connection(self, origin: Origin, raw_proxy: RawProxy) -> _CONNECTION_TYPES:
        if raw_proxy.url.scheme == "http":
            return AsyncForwardHTTPConnection(
                proxy_origin=raw_proxy.enforced_url.origin,
                proxy_headers=raw_proxy.enforced_headers,
                proxy_ssl_context=raw_proxy.ssl_context,
                remote_origin=origin,
                keepalive_expiry=self._keepalive_expiry,
                network_backend=self._network_backend,
            )

        if raw_proxy.url.scheme == "https":
            return AsyncTunnelHTTPConnection(
                proxy_origin=raw_proxy.enforced_url.origin,
                proxy_headers=raw_proxy.enforced_headers,
                proxy_ssl_context=raw_proxy.ssl_context,
                remote_origin=origin,
                keepalive_expiry=self._keepalive_expiry,
                ssl_context=self._ssl_context,
                http1=self._http1,
                http2=self._http2,
                network_backend=self._network_backend,
            )

        try:
            import socksio  # type: ignore
            from httpcore._async.socks_proxy import AsyncSocks5Connection
        except (ImportError, ModuleNotFoundError):  # pragma: no cover
            raise ImportError(
                "Using SOCKS proxy, but the 'socksio' package is not installed. "
                "Make sure to install httpx using `pip install httpx[socks]`."
            ) from None

        return AsyncSocks5Connection(
            proxy_origin=raw_proxy.enforced_url.origin,
            remote_origin=origin,
            proxy_auth=raw_proxy.enforced_auth,
            ssl_context=self._ssl_context,
            keepalive_expiry=self._keepalive_expiry,
            http1=self._http1,
            http2=self._http2,
            network_backend=self._network_backend,
        )

    def update_connection(self):
        raw_proxy = self._get_proxy()
        self._conn = self._get_connection(self._origin, raw_proxy)
        return self._conn

    def __getattr__(self, __name: str) -> Any:
        return getattr(self._conn, __name)

    async def aclose(self) -> None:
        return await self._conn.aclose()

    def info(self) -> str:
        return self._conn.info()

    def can_handle_request(self, origin: Origin) -> bool:
        return self._conn.can_handle_request(origin)

    def is_available(self) -> bool:
        return self._conn.is_available()

    def has_expired(self) -> bool:
        return self._conn.has_expired()

    def is_idle(self) -> bool:
        return self._conn.is_idle()

    def is_closed(self) -> bool:
        return self._conn.is_closed()

    async def request(
        self,
        method: Union[bytes, str],
        url: Union[URL, bytes, str],
        *,
        headers: HttpcoreHeaderTypes = None,
        content: Union[bytes, AsyncIterator[bytes], None] = None,
        extensions: Optional[Extensions] = None,
    ) -> Response:
        return await self._conn.request(
            method, url, headers=headers, content=content, extensions=extensions
        )

    @asynccontextmanager
    async def stream(
        self,
        method: Union[bytes, str],
        url: Union[URL, bytes, str],
        *,
        headers: HttpcoreHeaderTypes = None,
        content: Union[bytes, AsyncIterator[bytes], None] = None,
        extensions: Optional[Extensions] = None,
    ) -> AsyncIterator[Response]:
        async with self._conn.stream(
            method, url, headers=headers, content=content, extensions=extensions
        ) as e:
            yield e

    async def handle_async_request(self, request: Request) -> Optional[Response]:
        retries_left = self._retries
        if self._always_update:
            self.update_connection()

        while retries_left >= 0:
            try:
                return await self._conn.handle_async_request(request)
            except (ConnectError, ConnectTimeout):
                if retries_left <= 0:
                    raise
                retries_left -= 1
                self.update_connection()
