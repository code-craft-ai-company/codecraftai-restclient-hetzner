"""
    .. module:: hetznerresource
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Attribute-addressable objects returned by the Hetzner Cloud
               REST client.

    The Hetzner Cloud API returns JSON objects whose fields are already
    snake_case (``server_type``, ``ip_range``, ``primary_disk_size``), which
    is the spelling Python callers want.  A :class:`HetznerObject` is
    therefore a ``dict`` that is additionally attribute addressable —
    ``server.server_type.name`` and ``server["server_type"]["name"]`` both
    work, and an absent field reads as ``None`` rather than raising.

    Reading absent fields as ``None`` matters for migration: consumer code
    written against the ``hcloud`` SDK is full of
    ``getattr(obj, "field", None)`` guards over optional attributes, and
    those guards must keep behaving the same way.

    Unlike the Linode client, resources here are NOT active record.  Hetzner
    consumers mutate through the api groups — ``client.volumes.detach(
    volume=volume)``, ``client.servers.delete(server=server)`` — which is the
    shape the ``hcloud`` SDK used, so the objects stay inert data and the
    groups own the verbs.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict


class HetznerObject(dict):
    """
        A ``dict`` of Hetzner Cloud API JSON that is also attribute
        addressable.

        A missing field reads as ``None`` so ``getattr(obj, "field", None)``
        guards in consumer code behave as they did against the SDK's object
        model.

        The inherited mapping methods (``keys`` / ``values`` / ``items`` /
        ``get`` ...) are NOT shadowed by fields, because no Hetzner payload
        uses those names — collections arrive under the resource's plural
        name (``servers``, ``volumes``) and pagination under ``meta``.
    """

    def __getattr__(self, name: str) -> Any:
        """
            Resolve a field by attribute access.

            :param name: The field name.

            :returns: The wrapped field value, or ``None`` when absent.
        """
        if name.startswith("_") is True:
            # Never resolve private/dunder lookups as API fields; that would
            # make copy/pickle/inspect machinery see phantom attributes.
            raise AttributeError(name)

        if name in self:
            rtnval = wrap_hetzner_value(self[name])
            return rtnval

        rtnval = None
        return rtnval

    def __setattr__(self, name: str, value: Any) -> None:
        """
            Set a field by attribute assignment.

            :param name: The field name.
            :param value: The value to store.

            :returns: ``None``
        """
        if name.startswith("_") is True:
            object.__setattr__(self, name, value)
            return
        self[name] = value
        return

    def as_dict(self) -> Dict[str, Any]:
        """
            Return the underlying plain dictionary.

            :returns: The wire-shaped dictionary.
        """
        rtnval = dict(self)
        return rtnval


def wrap_hetzner_value(value: Any) -> Any:
    """
        Wrap a decoded JSON value so nested objects stay attribute
        addressable.

        Nesting matters here: a server's type arrives as an embedded object,
        and consumers read ``server.server_type.name``.  Without wrapping the
        nested dict that second hop would raise.

        :param value: The decoded JSON value.

        :returns: A :class:`HetznerObject` for dicts, a list of wrapped
            values for lists, or the value unchanged.
    """
    if isinstance(value, HetznerObject) is True:
        rtnval = value
        return rtnval
    if isinstance(value, dict) is True:
        rtnval = HetznerObject(value)
        return rtnval
    if isinstance(value, list) is True:
        rtnval = [wrap_hetzner_value(item) for item in value]
        return rtnval
    rtnval = value
    return rtnval


def identifier_of(obj: Any) -> Any:
    """
        Read the Hetzner id off an object, an id, or a plain dict.

        The api groups accept whatever the caller is holding — the object
        returned from a create, a bare integer id read back out of recorded
        state, or a plain decoded dict — because consumer call sites do all
        three.

        :param obj: A :class:`HetznerObject`, a mapping, or a bare id.

        :returns: The resolved identifier.
    """
    if isinstance(obj, dict) is True:
        rtnval = obj.get("id", None)
        return rtnval

    identifier = getattr(obj, "id", None)
    if identifier is not None:
        rtnval = identifier
        return rtnval

    rtnval = obj
    return rtnval
