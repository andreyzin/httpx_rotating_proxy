import ssl
from typing import List, Optional, Union

from httpcore import AsyncConnectionPool, AsyncNetworkBackend, Origin
from httpcore._async import AsyncConnectionInterface

from .raw_proxy import RawProxy
from .rotating_proxy_connection import ProxyConnection, ProxyFactoryType


class RotatingProxyPool(AsyncConnectionPool):
    def __init__(
        self,
        proxies: Union[List[RawProxy], ProxyFactoryType],
        always_update: bool = False,
        ssl_context: Optional[ssl.SSLContext] = None,
        max_connections: Optional[int] = 10,
        max_keepalive_connections: Optional[int] = None,
        keepalive_expiry: Optional[float] = None,
        http1: bool = True,
        http2: bool = False,
        retries: int = 0,
        network_backend: Optional[AsyncNetworkBackend] = None,
    ) -> None:
        super().__init__(
            ssl_context=ssl_context,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            http1=http1,
            http2=http2,
            network_backend=network_backend,
            retries=retries,
        )
        self._always_update = always_update
        self._proxies = proxies
        self._ssl_context = ssl_context

    def create_connection(self, origin: Origin) -> AsyncConnectionInterface:
        return ProxyConnection(
            proxies=self._proxies,
            origin=origin,
            retries=self._retries,
            always_update=self._always_update,
        )
