"""
    .. module:: resourcegroupbase
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`ResourceGroupBase` — the shared behaviour of the
               Hetzner Cloud api groups.

    Every Hetzner Cloud resource collection follows the same shape: a
    collection path (``/servers``), entries nested under the plural name
    (``servers``), a singular key on single-resource responses (``server``),
    filtering by ``name`` and ``label_selector``, and deletion by id.  That
    uniformity lives here so each concrete group only declares its names and
    adds the verbs unique to it.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional

from ccai.restclient.hetzner.hetznerresource import (
    HetznerObject, identifier_of, wrap_hetzner_value
)


class ResourceGroupBase:
    """
        Shared behaviour for a Hetzner Cloud resource collection.

        :cvar COLLECTION_PATH: The collection path, e.g. ``/servers``.
        :cvar COLLECTION_KEY: The plural key entries arrive under.
        :cvar SINGULAR_KEY: The singular key a single-resource response
            nests the resource under, and the keyword name
            :meth:`delete` accepts.
    """

    COLLECTION_PATH: str = ""
    COLLECTION_KEY: str = ""
    SINGULAR_KEY: str = ""

    def __init__(self, *, client: Any) -> None:
        """
            Construct a resource group bound to a client.

            :param client: The owning :class:`HetznerRestClient`.
        """
        self._client = client
        return

    def get_by_name(self, *, name: str) -> Optional[HetznerObject]:
        """
            Look a resource up by its name.

            The API filters the collection by an exact ``name`` query
            parameter and answers with a (possibly empty) list.

            :param name: The resource name.

            :returns: The resource, or ``None`` when no resource carries that
                name.  ``None`` rather than an error because callers use this
                to decide whether to create — an absent resource is the
                normal case, not a failure.
        """
        payload = self._client.request(method="GET",
                                       path=self.COLLECTION_PATH,
                                       params={"name": name})

        entries = payload.get(self.COLLECTION_KEY, None)
        if entries is None or len(entries) == 0:
            rtnval = None
            return rtnval

        rtnval = wrap_hetzner_value(entries[0])
        return rtnval

    def get_all(self, *, label_selector: Optional[str] = None,
                name: Optional[str] = None,
                **filters: Any) -> List[HetznerObject]:
        """
            List every resource in the collection, across all pages.

            :param label_selector: Optional Hetzner label selector, e.g.
                ``owner==ccai``.
            :param name: Optional exact-name filter.
            :param filters: Any further query parameters the endpoint
                accepts.

            :returns: The matching resources.
        """
        params: Dict[str, Any] = {"label_selector": label_selector,
                                  "name": name}
        for key, value in filters.items():
            params[key] = value

        entries = self._client.paginate(path=self.COLLECTION_PATH,
                                        collection_key=self.COLLECTION_KEY,
                                        params=params)

        rtnval = [wrap_hetzner_value(entry) for entry in entries]
        return rtnval

    def get_by_id(self, *, id: Any) -> HetznerObject:
        """
            Fetch one resource by its id.

            :param id: The resource id.

            :returns: The resource.
        """
        payload = self._client.request(
            method="GET",
            path="{}/{}".format(self.COLLECTION_PATH, id))
        rtnval = self._unwrap(payload=payload)
        return rtnval

    def delete(self, *args: Any, **kwargs: Any) -> None:
        """
            Delete a resource.

            The resource is named by the group's singular keyword —
            ``delete(server=server)``, ``delete(volume=volume)`` — matching
            the ``hcloud`` SDK's spelling.  A single positional argument is
            accepted too.  The value may be a resource object, a plain
            decoded dict, or a bare id.

            :param args: Optionally the resource, positionally.
            :param kwargs: The resource, under the group's singular keyword.

            :returns: ``None``

            :raises: :class:`TypeError` when no resource was supplied.
        """
        target = self._resolve_target(args=args, kwargs=kwargs)
        identifier = identifier_of(target)

        self._client.request(
            method="DELETE",
            path="{}/{}".format(self.COLLECTION_PATH, identifier))
        return

    def _resolve_target(self, *, args: Any, kwargs: Any) -> Any:
        """
            Resolve the resource a verb was invoked against.

            :param args: The positional arguments.
            :param kwargs: The keyword arguments.

            :returns: The resource.

            :raises: :class:`TypeError` when no resource was supplied — a
                silent no-op here would leave infrastructure running while
                reporting success.
        """
        if len(args) > 0:
            rtnval = args[0]
            return rtnval

        if self.SINGULAR_KEY in kwargs:
            rtnval = kwargs[self.SINGULAR_KEY]
            return rtnval

        err_msg = ("A {} must be supplied, either positionally or as the "
                   "'{}' keyword.".format(self.SINGULAR_KEY,
                                          self.SINGULAR_KEY))
        raise TypeError(err_msg)

    def _create(self, *, body: Dict[str, Any]) -> HetznerObject:
        """
            POST a creation body to the collection.

            :param body: The request body, with ``None`` values dropped.

            :returns: The raw decoded response.
        """
        payload: Dict[str, Any] = {}
        for key, value in body.items():
            if value is not None:
                payload[key] = value

        rtnval = self._client.request(method="POST",
                                      path=self.COLLECTION_PATH,
                                      body=payload)
        return rtnval

    def _unwrap(self, *, payload: HetznerObject) -> HetznerObject:
        """
            Pull the resource out of a single-resource response.

            :param payload: The decoded response.

            :returns: The nested resource, or the payload itself when it
                carries no singular key.
        """
        entry = payload.get(self.SINGULAR_KEY, None)
        if entry is None:
            rtnval = payload
            return rtnval

        rtnval = wrap_hetzner_value(entry)
        return rtnval

    def _action(self, *, resource: Any, action: str,
                body: Optional[Dict[str, Any]] = None) -> HetznerObject:
        """
            POST an action against one resource.

            Hetzner models mutations that take time — attach, detach, resize
            — as actions under ``/{collection}/{id}/actions/{action}``.

            :param resource: The resource, an object or a bare id.
            :param action: The action name.
            :param body: Optional action body, with ``None`` values dropped.

            :returns: The decoded response, carrying the ``action`` record.
        """
        identifier = identifier_of(resource)

        payload: Optional[Dict[str, Any]] = None
        if body is not None:
            payload = {}
            for key, value in body.items():
                if value is not None:
                    payload[key] = value

        rtnval = self._client.request(
            method="POST",
            path="{}/{}/actions/{}".format(self.COLLECTION_PATH, identifier,
                                           action),
            body=payload)
        return rtnval
