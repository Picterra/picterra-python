from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections.abc import Callable

if sys.version_info >= (3, 8):
    from typing import Literal, TypedDict
else:
    from typing_extensions import Literal, TypedDict

from typing import Any, Generic, Iterator, TypeVar
from urllib.parse import urlencode, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger()

CHUNK_SIZE_BYTES = 8192  # 8 KiB


class APIError(Exception):
    """Generic API error exception"""

    pass


class _RequestsSession(requests.Session):
    """
    Override requests session to to implement a global session timeout
    """

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop("timeout")
        super().__init__(*args, **kwargs)
        self.headers.update(
            {"User-Agent": "picterra-python %s" % self.headers["User-Agent"]}
        )

    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return super().request(*args, **kwargs)


def _download_to_file(url: str, filename: str):
    # Given we do not use self.sess the timeout is disabled (requests default), and this
    # is good as file download can take a long time
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb+") as f:
            logger.debug("Downloading to file %s.." % filename)
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE_BYTES):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)


def _upload_file_to_blobstore(upload_url: str, filename: str):
    if not (os.path.exists(filename) and os.path.isfile(filename)):
        raise ValueError("Invalid file: " + filename)
    with open(
        filename, "rb"
    ) as f:  # binary recommended by requests stream upload (see link below)
        logger.debug("Opening and streaming to upload file %s" % filename)
        # Given we do not use self.sess the timeout is disabled (requests default), and this
        # is good as file upload can take a long time. Also we use requests streaming upload
        # (https://requests.readthedocs.io/en/latest/user/advanced/#streaming-uploads) to avoid
        # reading the (potentially large) layer GeoJSON in memory
        resp = requests.put(upload_url, data=f)
    if not resp.ok:
        logger.error("Error when uploading to blobstore %s" % upload_url)
        raise APIError(resp.text)


def multipolygon_to_polygon_feature_collection(mp):
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": p
            }
        } for p in mp["coordinates"]]
    }

T = TypeVar("T")


class ResultsPage(Generic[T]):
    """
    Interface for a paginated response from the API

    Typically the endpoint returning list of objects return them splitted
    in pages (page 1, page 2, etc..) of a fixed dimension (eg 20). Thus
    each `list_XX` function returns a ResultsPage (by default the first one);
    once you have a ResultsPage for a given list of objects, you can:
    * check its length with `len()` (eg `len(page)`)
    * access a single element with the index operator `[]` (eg `page[5]`)
    * turn it into a list of dictionaries with  `list()` (eg `list(page)`)
    * get the next page with `.next()` (eg `page.next()`); this could return
    None if the list is finished
    You can also get a specific page passing the page number to the `list_XX` function
    """

    def __init__(self, url: str, fetch: Callable[[str], requests.Response]):
        resp = fetch(url)
        if not resp.ok:
            raise APIError(resp.text)
        r: dict[str, Any] = resp.json()
        next_url: str | None = r["next"]
        results: list[T] = r["results"]

        self._fetch = fetch
        self._next_url = next_url
        self._results = results
        self._url = url

    def next(self):
        return ResultsPage(self._next_url, self._fetch) if self._next_url else None

    def __len__(self) -> int:
        return len(self._results)

    def __getitem__(self, key: int) -> T:
        return self._results[key]

    def __iter__(self) -> Iterator[T]:
        return iter([self._results[i] for i in range(len(self._results))])

    def __str__(self) -> str:
        return f"{len(self._results)} results from {self._url}"


class Feature(TypedDict):
    type: Literal["Feature"]
    properties: dict[str, Any]
    geometry: dict[str, Any]


class FeatureCollection(TypedDict):
    type: Literal["FeatureCollection"]
    features: list[Feature]


class BaseAPIClient:
    """
    Base class for Picterra API clients.

    This is subclassed for the different products we have.
    """

    def __init__(
        self, api_url: str, timeout: int = 30, max_retries: int = 3, backoff_factor: int = 10
    ):
        """
        Args:
            api_url: the api's base url. This is different based on the Picterra product used
                and is typically defined by implementations of this client
            timeout: number of seconds before the request times out
            max_retries: max attempts when ecountering gateway issues or throttles; see
                retry_strategy comment below
            backoff_factor: factor used nin the backoff algorithm; see retry_strategy comment below
        """
        base_url = os.environ.get(
            "PICTERRA_BASE_URL", "https://app.picterra.ch/"
        )
        api_key = os.environ.get("PICTERRA_API_KEY", None)
        if not api_key:
            raise APIError("PICTERRA_API_KEY environment variable is not defined")
        logger.info(
            "Using base_url=%s, api_url=%s; %d max retries, %d backoff and %s timeout.",
            base_url,
            api_url,
            max_retries,
            backoff_factor,
            timeout,
        )
        self.base_url = urljoin(base_url, api_url)
        # Create the session with a default timeout (30 sec), that we can then
        # override on a per-endpoint basis (will be disabled for file uploads and downloads)
        self.sess = _RequestsSession(timeout=timeout)
        # Retry: we set the HTTP codes for our throttle (429) plus possible gateway problems (50*),
        # and for polling methods (GET), as non-idempotent ones should be addressed via idempotency
        # key mechanism; given the algorithm is {<backoff_factor> * (2 **<retries-1>}, and we
        # default to 30s for polling and max 30 req/min, the default 5-10-20 sequence should
        # provide enough room for recovery
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 502, 503, 504],
            backoff_factor=backoff_factor,
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.sess.mount("https://", adapter)
        self.sess.mount("http://", adapter)
        # Authentication
        self.sess.headers.update({"X-Api-Key": api_key})

    def _full_url(self, path: str, params: dict[str, Any] | None = None):
        url = urljoin(self.base_url, path)
        if not params:
            return url
        else:
            qstr = urlencode(params)
            return "%s?%s" % (url, qstr)

    def _wait_until_operation_completes(
        self, operation_response: dict[str, Any]
    ) -> dict[str, Any]:
        """Polls an operation an returns its data"""
        operation_id = operation_response["operation_id"]
        poll_interval = operation_response["poll_interval"]
        # Just sleep for a short while the first time
        time.sleep(poll_interval * 0.1)
        while True:
            logger.info("Polling operation id %s" % operation_id)
            resp = self.sess.get(
                self._full_url("operations/%s/" % operation_id),
            )
            if not resp.ok:
                raise APIError(resp.text)
            status = resp.json()["status"]
            logger.info("status=%s" % status)
            if status == "success":
                break
            if status == "failed":
                errors = resp.json()["errors"]
                raise APIError(
                    "Operation %s failed: %s" % (operation_id, json.dumps(errors))
                )
            time.sleep(poll_interval)
        return resp.json()

    def _return_results_page(
        self, resource_endpoint: str, params: dict[str, Any] | None = None
    ) -> ResultsPage:
        if params is None:
            params = {}
        if "page_number" not in params:
            params["page_number"] = 1

        url = self._full_url("%s/" % resource_endpoint, params=params)
        return ResultsPage(url, self.sess.get)

    def get_operation_results(self, operation_id: str) -> dict[str, Any]:
        """
        Return the 'results' dict of an operation

        This a **beta** function, subject to change.

        Args:
            operation_id: The id of the operation
        """
        resp = self.sess.get(
            self._full_url("operations/%s/" % operation_id),
        )
        return resp.json()["results"]
