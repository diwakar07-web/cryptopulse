"""Shared HTTP client with retry, timeout, and request logging."""
import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import APIConfig

logger = logging.getLogger(__name__)


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=APIConfig.max_retries,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_SESSION = _build_session()


def get_json(url: str, params: dict | None = None) -> Any:
    """GET request returning parsed JSON, with timing and error logging."""
    start = time.perf_counter()
    try:
        response = _SESSION.get(url, params=params, timeout=APIConfig.timeout)
        response.raise_for_status()
        elapsed = time.perf_counter() - start
        logger.info("GET %s -> %d (%.2fs)", url, response.status_code, elapsed)
        return response.json()
    except requests.RequestException as exc:
        elapsed = time.perf_counter() - start
        logger.error("GET %s failed after %.2fs: %s", url, elapsed, exc)
        raise
