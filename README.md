# Httpx Rotating Proxy

Python Library to use a list of proxy in `httpx.AsyncClient`

## Getting Started

### Dependencies

* python >= 3
* [httpx](https://github.com/encode/httpx/) >= 0.22.0

### Installing

* `python -m pip -U install git+https://github.com/andreyzin/httpx_rotating_proxy.git`
* **Not available on PyPi now**

### Usage

* List of proxies
  
```python
from httpx_rotating import RotatingProxyTransport

proxy_list = [
    "socks5://127.0.0.1:8000",
    "https://127.0.0.1:80"
]
transport = RotatingProxyTransport(proxy_list)

client = httpx.AsyncClient(transport=transport)
```

* Factory

```python
from httpx_rotating import RotatingProxyTransport

proxy_list = [
    "socks5://127.0.0.1:8000",
    "https://127.0.0.1:80"
]
transport = RotatingProxyTransport(lambda x: random.choice(proxy_list))

client = httpx.AsyncClient(transport=transport)
```

 - factory signature: `Callable[[httpcore.Origin], Union[ProxyTypes, RawProxy]]`


## License

This project is licensed under the MIT License - see the LICENSE file for details