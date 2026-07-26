"""
    .. module:: servergroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`ServerGroup` — the ``/servers`` api group.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional

from ccai.restclient.hetzner.apigroups.resourcegroupbase import (
    ResourceGroupBase
)
from ccai.restclient.hetzner.hetznerresource import (
    HetznerObject, identifier_of
)


class ServerGroup(ResourceGroupBase):
    """
        The Hetzner Cloud servers collection.
    """

    COLLECTION_PATH = "/servers"
    COLLECTION_KEY = "servers"
    SINGULAR_KEY = "server"

    def create(self, *, name: str, server_type: Any, image: Any,
               location: Optional[Any] = None,
               ssh_keys: Optional[List[Any]] = None,
               networks: Optional[List[Any]] = None,
               firewalls: Optional[List[Any]] = None,
               volumes: Optional[List[Any]] = None,
               user_data: Optional[str] = None,
               labels: Optional[Dict[str, str]] = None,
               start_after_create: Optional[bool] = None,
               **fields: Any) -> HetznerObject:
        """
            Create a server.

            The object-valued parameters accept what the caller is holding —
            the resource objects returned from earlier creates — and are
            reduced to the ids the wire format wants.  That is deliberate:
            consumer code assembles handles (a live network, a live firewall)
            and passes them straight through, exactly as it did against the
            SDK.

            :param name: The server name.
            :param server_type: The server type name, or an object carrying
                one.
            :param image: The image name or id, or an object carrying one.
            :param location: Optional location name, or an object carrying
                one.
            :param ssh_keys: Optional ssh keys to inject — objects, ids or
                names.
            :param networks: Optional private networks to join — objects or
                ids.
            :param firewalls: Optional firewalls to apply — objects or ids.
            :param volumes: Optional volumes to attach — objects or ids.
            :param user_data: Optional cloud-init user data.
            :param labels: Optional labels.
            :param start_after_create: Whether the API should boot the server
                once built.
            :param fields: Any further server fields.

            :returns: The raw creation response, carrying ``server``,
                ``action`` and ``root_password`` — the same shape the SDK's
                ``CreateServerResponse`` presented, so callers reading
                ``result.server`` keep working.
        """
        body: Dict[str, Any] = {
            "name": name,
            "server_type": _name_or_value(server_type),
            "image": _name_or_value(image),
            "location": _name_or_value(location),
            "user_data": user_data,
            "labels": labels,
            "start_after_create": start_after_create,
        }

        if ssh_keys is not None:
            body["ssh_keys"] = [_key_reference(entry) for entry in ssh_keys]
        if networks is not None:
            body["networks"] = [identifier_of(entry) for entry in networks]
        if volumes is not None:
            body["volumes"] = [identifier_of(entry) for entry in volumes]
        if firewalls is not None:
            # The wire format wraps each id in an object, unlike the other
            # reference lists on this endpoint.
            body["firewalls"] = [{"firewall": identifier_of(entry)}
                                 for entry in firewalls]

        for key, value in fields.items():
            body[key] = value

        rtnval = self._create(body=body)
        return rtnval

    def power_on(self, *, server: Any) -> HetznerObject:
        """
            Power a server on.

            :param server: The server, an object or a bare id.

            :returns: The action response.
        """
        rtnval = self._action(resource=server, action="poweron")
        return rtnval

    def power_off(self, *, server: Any) -> HetznerObject:
        """
            Power a server off.

            :param server: The server, an object or a bare id.

            :returns: The action response.
        """
        rtnval = self._action(resource=server, action="poweroff")
        return rtnval

    def reboot(self, *, server: Any) -> HetznerObject:
        """
            Reboot a server.

            :param server: The server, an object or a bare id.

            :returns: The action response.
        """
        rtnval = self._action(resource=server, action="reboot")
        return rtnval


def _name_or_value(value: Any) -> Any:
    """
        Reduce a possibly-object reference to the name the wire wants.

        Server type, image and location are named by string on the wire, but
        callers may hold an object carrying that name.

        :param value: A string, an object with a ``name``, or ``None``.

        :returns: The name, the value unchanged, or ``None``.
    """
    if value is None:
        rtnval = None
        return rtnval

    if isinstance(value, str) is True:
        rtnval = value
        return rtnval

    if isinstance(value, dict) is True:
        name = value.get("name", None)
        if name is not None:
            rtnval = name
            return rtnval
        rtnval = value.get("id", None)
        return rtnval

    name = getattr(value, "name", None)
    if name is not None:
        rtnval = name
        return rtnval

    rtnval = value
    return rtnval


def _key_reference(value: Any) -> Any:
    """
        Reduce an ssh-key reference to an id or name.

        The endpoint accepts either, so an id is preferred when present and a
        name is used otherwise.

        :param value: An ssh-key object, id or name.

        :returns: The id or name.
    """
    if isinstance(value, str) is True:
        rtnval = value
        return rtnval

    if isinstance(value, dict) is True:
        identifier = value.get("id", None)
        if identifier is not None:
            rtnval = identifier
            return rtnval
        rtnval = value.get("name", None)
        return rtnval

    identifier = getattr(value, "id", None)
    if identifier is not None:
        rtnval = identifier
        return rtnval

    rtnval = getattr(value, "name", value)
    return rtnval
