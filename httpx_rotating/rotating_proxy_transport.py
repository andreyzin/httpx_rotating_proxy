from typing import Iterable, Optional, Union

import httpx
from httpx._config import DEFAULT_LIMITS, Limits, create_ssl_context
from httpx._types import CertTypes, ProxyTypes, VerifyTypes

from .raw_proxy import RawProxy
from .rotating_proxy_connection import ProxyFactoryType
from .rotating_proxy_pool import RotatingProxyPool


class RotatingProxyTransport(httpx.AsyncHTTPTransport):
    def __init__(
        self,
        proxies: Union[Iterable[ProxyTypes], ProxyFactoryType],
        always_update: bool = False,
        verify: VerifyTypes = True,
        cert: Optional[CertTypes] = None,
        http1: bool = True,
        http2: bool = False,
        limits: Limits = DEFAULT_LIMITS,
        trust_env: bool = True,
        retries: int = 0,
    ):
        """
        Initialize the proxy manager with the given proxies, SSL verification settings, and connection limits.

        Parameters:
            proxies (Union[Iterable[ProxyTypes], ProxyFactoryType]): The proxies to be used.
                if passed as a function, it will be called with the origin and should return a proxy to use.
            always_update (bool): Whether to always change proxy, not only when an error occurs.
            verify (VerifyTypes): Whether to verify the SSL certificate.
            cert (Optional[CertTypes]): The SSL certificate to be used.
            http1 (bool): Whether to use HTTP/1.1.
            http2 (bool): Whether to use HTTP/2.
            limits (Limits): The connection limits.
            trust_env (bool): Whether to trust the environment settings.
            retries (int): The number of retries in case of connection failure.
        """
        ssl_context = create_ssl_context(verify=verify, cert=cert, trust_env=trust_env)

        if callable(proxies):
            self._proxies = proxies
        else:
            self._proxies = list(map(RawProxy.cast, proxies))

        if not isinstance(self._proxies, list) or all(
            [proxy.url.scheme in ("http", "https", "socks5") for proxy in self._proxies]
        ):
            self._pool = RotatingProxyPool(
                proxies=self._proxies,
                always_update=always_update,
                ssl_context=ssl_context,
                max_connections=limits.max_connections,
                max_keepalive_connections=limits.max_keepalive_connections,
                keepalive_expiry=limits.keepalive_expiry,
                http1=http1,
                http2=http2,
                retries=retries,
            )
        else:  # pragma: no cover
            raise ValueError(
                "Proxy protocol must be either 'http', 'https', or 'socks5',"
                " but got {proxy.url.scheme!r}."
            )
