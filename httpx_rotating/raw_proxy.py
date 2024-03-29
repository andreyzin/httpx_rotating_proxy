import ssl
from typing import Optional, Tuple, Union

import httpcore
import httpx
from httpcore._async.http_proxy import (
    build_auth_header,
)
from httpcore._models import enforce_bytes, enforce_headers, enforce_url
from httpx._types import HeaderTypes, URLTypes, ProxyTypes


class RawProxy(httpx.Proxy):
    def __init__(
        self,
        url: URLTypes,
        *,
        ssl_context: Optional[ssl.SSLContext] = None,
        auth: Optional[Tuple[str, str]] = None,
        headers: Optional[HeaderTypes] = None,
    ) -> None:
        super().__init__(url=url, ssl_context=ssl_context, auth=auth, headers=headers)

        if self.url.scheme == b"http" and ssl_context is not None:  # pragma: no cover
            raise RuntimeError(
                "The `proxy_ssl_context` argument is not allowed for the http scheme"
            )

        self.enforced_url = enforce_url(
            httpcore.URL(
                scheme=self.url.raw_scheme,
                host=self.url.raw_host,
                port=self.url.port,
                target=self.url.raw_path,
            ),
            name="proxy_url",
        )
        self.enforced_headers = enforce_headers(self.headers.raw, name="proxy_headers")
        self.enforced_auth = None
        if self.auth is not None:
            username, password = self.auth
            username_bytes = enforce_bytes(username, name="proxy_auth")
            password_bytes = enforce_bytes(password, name="proxy_auth")
            authorization = build_auth_header(username_bytes, password_bytes)
            self.enforced_headers = [
                (b"Proxy-Authorization", authorization)
            ] + self.enforced_headers

            self.enforced_auth: Optional[Tuple[bytes, bytes]] = (
                username_bytes,
                password_bytes,
            )

    @classmethod
    def from_httpx(cls, proxy: httpx.Proxy) -> "RawProxy":
        return cls(
            url=proxy.url,
            ssl_context=proxy.ssl_context,
            auth=proxy.auth,
            headers=proxy.headers,
        )

    @classmethod
    def cast(cls, proxy: Union[ProxyTypes, "RawProxy"]) -> "RawProxy":
        if isinstance(proxy, cls):
            return proxy
        if isinstance(proxy, httpx.Proxy):
            return cls.from_httpx(proxy)
        if isinstance(proxy, str):
            return cls(url=proxy)
        raise TypeError(f"Expected RawProxy, httpx.Proxy or str, but got {type(proxy)}")
