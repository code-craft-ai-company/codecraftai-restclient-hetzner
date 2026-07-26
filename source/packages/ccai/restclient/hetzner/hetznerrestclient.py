"""
    .. module:: hetznerrestclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`HetznerRestClient` — a pure-Python client for the
               Hetzner Cloud API v1.

    The Hetzner Cloud API is plain REST over HTTPS with JSON bodies and a
    Bearer API token, so this client speaks it directly rather than depending
    on the ``hcloud`` SDK.

    The api groups mirror the SDK's grouping — ``servers``, ``volumes``,
    ``networks``, ``firewalls``, ``ssh_keys`` — so call sites written against
    the SDK keep their shape.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


import json
import os

from typing import Any, Dict, List, Optional

import requests

from ccai.restclient.hetzner.hetznerapierror import HetznerApiRequestError
from ccai.restclient.hetzner.hetznerresource import (
    HetznerObject, wrap_hetzner_value
)


HETZNER_API_BASE = "https://api.hetzner.cloud/v1"

DEFAULT_TIMEOUT_SECONDS = 60.0

# The API caps page size at 50; asking for the maximum minimises the number
# of round trips when walking a collection.
MAX_PAGE_SIZE = 50


class HetznerRestClient:
    """
        REST client for the Hetzner Cloud API v1.

        The api groups are reached through public attributes named to match
        the SDK's: ``servers``, ``volumes``, ``networks``, ``firewalls``,
        ``ssh_keys``.
    """

    def __init__(self, *, token: str, base_url: str = HETZNER_API_BASE,
                 session: Optional[Any] = None,
                 timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """
            Construct a HetznerRestClient.

            :param token: The Hetzner Cloud API token.
            :param base_url: The API base URL.
            :param session: Optional pre-built ``requests.Session`` — the
                test seam and the way a caller supplies custom transport
                adapters or proxies.
            :param timeout_seconds: The default per-request timeout.
        """
        self._token: str = token
        self._base_url: str = base_url.rstrip("/")
        self._timeout_seconds: float = timeout_seconds

        if session is not None:
            self._session = session
        else:
            self._session = requests.Session()

        self._session.headers.update({
            "Authorization": "Bearer {}".format(token),
            "Accept": "application/json",
        })

        from ccai.restclient.hetzner.apigroups.servergroup import ServerGroup
        from ccai.restclient.hetzner.apigroups.volumegroup import VolumeGroup
        from ccai.restclient.hetzner.apigroups.networkgroup import (
            NetworkGroup
        )
        from ccai.restclient.hetzner.apigroups.firewallgroup import (
            FirewallGroup
        )
        from ccai.restclient.hetzner.apigroups.sshkeygroup import SshKeyGroup

        self.servers: ServerGroup = ServerGroup(client=self)
        self.volumes: VolumeGroup = VolumeGroup(client=self)
        self.networks: NetworkGroup = NetworkGroup(client=self)
        self.firewalls: FirewallGroup = FirewallGroup(client=self)
        self.ssh_keys: SshKeyGroup = SshKeyGroup(client=self)
        return

    @property
    def base_url(self) -> str:
        """
            Return the API base URL.

            :returns: The base URL.
        """
        rtnval = self._base_url
        return rtnval

    def request(self, *, method: str, path: str,
                params: Optional[Dict[str, Any]] = None,
                body: Optional[Dict[str, Any]] = None,
                timeout_seconds: Optional[float] = None) -> HetznerObject:
        """
            Perform one API request and return the decoded body.

            :param method: The HTTP method.
            :param path: The API path, beginning with ``/``.
            :param params: Optional query parameters; ``None`` values are
                dropped so an unset label selector is simply absent.
            :param body: Optional JSON request body.
            :param timeout_seconds: Optional per-request timeout override.

            :returns: The decoded response as a :class:`HetznerObject`; an
                empty one when the response carries no body (deletes return
                ``204``).

            :raises: :class:`HetznerApiRequestError` on a non-success status.
        """
        url = "{}{}".format(self._base_url, path)

        query: Dict[str, Any] = {}
        if params is not None:
            for key, value in params.items():
                if value is not None:
                    query[key] = value

        headers: Dict[str, str] = {}
        payload = None
        if body is not None:
            payload = json.dumps(body)
            headers["Content-Type"] = "application/json"

        timeout = timeout_seconds
        if timeout is None:
            timeout = self._timeout_seconds

        response = self._session.request(method, url, params=query,
                                         data=payload, headers=headers,
                                         timeout=timeout)

        status = getattr(response, "status_code", 0)

        if status < 200 or status >= 300:
            text = getattr(response, "text", "")
            reason = self._extract_error_reason(
                response=response, fallback=getattr(response, "reason", ""))
            err_msg_lines = ["The Hetzner Cloud API request failed."]
            err_msg_lines.append("METHOD: {}".format(method))
            err_msg_lines.append("PATH: {}".format(path))
            err_msg_lines.append("STATUS: {}".format(status))
            err_msg_lines.append("REASON: {}".format(reason))
            err_msg = os.linesep.join(err_msg_lines)
            raise HetznerApiRequestError(err_msg, status=status,
                                         reason=reason, body=text)

        text = getattr(response, "text", "")
        if text is None or len(text.strip()) == 0:
            rtnval = HetznerObject()
            return rtnval

        try:
            decoded = response.json()
        except Exception:
            rtnval = HetznerObject()
            return rtnval

        wrapped = wrap_hetzner_value(decoded)
        if isinstance(wrapped, HetznerObject) is True:
            rtnval = wrapped
            return rtnval

        rtnval = HetznerObject({"data": wrapped})
        return rtnval

    def _extract_error_reason(self, *, response: Any,
                              fallback: str) -> str:
        """
            Pull a human-readable reason out of a Hetzner error body.

            Hetzner reports failures as ``{"error": {"code": ...,
            "message": ...}}``; the code and message together are far more
            useful than the bare HTTP phrase.

            :param response: The failed response.
            :param fallback: The reason to use when the body is unhelpful.

            :returns: The extracted reason.
        """
        try:
            decoded = response.json()
        except Exception:
            rtnval = fallback
            return rtnval

        if isinstance(decoded, dict) is False:
            rtnval = fallback
            return rtnval

        error = decoded.get("error", None)
        if isinstance(error, dict) is False:
            rtnval = fallback
            return rtnval

        code = error.get("code", None)
        message = error.get("message", None)

        if code is not None and message is not None:
            rtnval = "{}: {}".format(code, message)
            return rtnval
        if message is not None:
            rtnval = str(message)
            return rtnval
        if code is not None:
            rtnval = str(code)
            return rtnval

        rtnval = fallback
        return rtnval

    def paginate(self, *, path: str, collection_key: str,
                 params: Optional[Dict[str, Any]] = None,
                 timeout_seconds: Optional[float] = None
                 ) -> List[Dict[str, Any]]:
        """
            Walk every page of a collection and return the concatenated
            entries.

            Hetzner paginates with ``meta.pagination``, carrying ``page`` and
            ``last_page``, and nests entries under the resource's plural name.
            Callers listing a collection expect ALL of it — a silently
            truncated first page would under-report owned resources, which on
            a teardown path means leaked infrastructure.

            :param path: The collection path, e.g. ``/servers``.
            :param collection_key: The plural key the entries arrive under.
            :param params: Optional query parameters.
            :param timeout_seconds: Optional per-request timeout override.

            :returns: The concatenated raw entries from every page.
        """
        collected: List[Dict[str, Any]] = []

        page_params: Dict[str, Any] = {}
        if params is not None:
            page_params.update(params)
        page_params["per_page"] = MAX_PAGE_SIZE

        page_number = 1
        while True:
            page_params["page"] = page_number
            payload = self.request(method="GET", path=path,
                                   params=page_params,
                                   timeout_seconds=timeout_seconds)

            entries = payload.get(collection_key, None)
            if entries is None:
                break
            collected.extend(entries)

            last_page = self._last_page_of(payload=payload)
            if last_page is None or page_number >= last_page:
                break
            page_number = page_number + 1

        rtnval = collected
        return rtnval

    def _last_page_of(self, *, payload: HetznerObject) -> Optional[int]:
        """
            Read the last page number out of a paginated response.

            :param payload: The decoded response body.

            :returns: The last page number, or ``None`` when the response
                carried no usable pagination block.
        """
        meta = payload.get("meta", None)
        if isinstance(meta, dict) is False:
            rtnval = None
            return rtnval

        pagination = meta.get("pagination", None)
        if isinstance(pagination, dict) is False:
            rtnval = None
            return rtnval

        last_page = pagination.get("last_page", None)
        if last_page is None:
            rtnval = None
            return rtnval

        try:
            rtnval = int(last_page)
        except (TypeError, ValueError):
            rtnval = None
        return rtnval
