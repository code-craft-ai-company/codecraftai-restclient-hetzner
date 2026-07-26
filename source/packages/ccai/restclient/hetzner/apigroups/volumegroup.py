"""
    .. module:: volumegroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`VolumeGroup` — the ``/volumes`` api group.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, Optional

from ccai.restclient.hetzner.apigroups.resourcegroupbase import (
    ResourceGroupBase
)
from ccai.restclient.hetzner.hetznerresource import (
    HetznerObject, identifier_of
)


class VolumeGroup(ResourceGroupBase):
    """
        The Hetzner Cloud volumes collection.

        Attach, detach and resize live here rather than on the resource
        objects, mirroring how the ``hcloud`` SDK's client exposed them and
        how consumer code already calls them.
    """

    COLLECTION_PATH = "/volumes"
    COLLECTION_KEY = "volumes"
    SINGULAR_KEY = "volume"

    def create(self, *, name: str, size: int,
               location: Optional[Any] = None,
               server: Optional[Any] = None,
               labels: Optional[Dict[str, str]] = None,
               automount: Optional[bool] = None,
               format: Optional[str] = None,
               **fields: Any) -> HetznerObject:
        """
            Create a volume.

            The API requires exactly one placement — either a ``location`` or
            a ``server`` to create it next to.  Neither is defaulted here:
            inventing a location would silently place storage somewhere the
            caller did not choose, so the API's own error is the better
            outcome.

            :param name: The volume name.
            :param size: The size in GB.
            :param location: Optional location name, or an object carrying
                one.
            :param server: Optional server to create the volume beside and
                attach to — an object or a bare id.
            :param labels: Optional labels.
            :param automount: Whether the API should mount the volume on
                attach.
            :param format: Optional filesystem to create, e.g. ``ext4``.
            :param fields: Any further volume fields.

            :returns: The raw creation response, carrying ``volume`` and
                ``action`` — the shape the SDK's ``CreateVolumeResponse``
                presented, so callers reading ``result.volume`` keep working.
        """
        body: Dict[str, Any] = {
            "name": name,
            "size": size,
            "labels": labels,
            "automount": automount,
            "format": format,
        }

        if location is not None:
            location_name = location
            if isinstance(location, str) is False:
                location_name = getattr(location, "name", location)
            body["location"] = location_name

        if server is not None:
            body["server"] = identifier_of(server)

        for key, value in fields.items():
            body[key] = value

        rtnval = self._create(body=body)
        return rtnval

    def attach(self, *, volume: Any, server: Optional[Any] = None,
               server_id: Optional[Any] = None,
               automount: Optional[bool] = None) -> HetznerObject:
        """
            Attach a volume to a server.

            Both ``server`` and ``server_id`` are accepted because consumer
            call sites hold each — an object freshly created, or an id read
            back out of recorded state.

            :param volume: The volume, an object or a bare id.
            :param server: The target server, an object or a bare id.
            :param server_id: The target server id.
            :param automount: Whether the API should mount the volume.

            :returns: The action response.

            :raises: :class:`TypeError` when no target server was supplied.
        """
        target = server
        if target is None:
            target = server_id

        if target is None:
            err_msg = ("A target server must be supplied, as either "
                       "'server' or 'server_id'.")
            raise TypeError(err_msg)

        rtnval = self._action(resource=volume, action="attach",
                              body={"server": identifier_of(target),
                                    "automount": automount})
        return rtnval

    def detach(self, *, volume: Any) -> HetznerObject:
        """
            Detach a volume from whatever server holds it.

            :param volume: The volume, an object or a bare id.

            :returns: The action response.
        """
        rtnval = self._action(resource=volume, action="detach")
        return rtnval

    def resize(self, *, volume: Any, size: int) -> HetznerObject:
        """
            Grow a volume.

            :param volume: The volume, an object or a bare id.
            :param size: The new size in GB.

            :returns: The action response.
        """
        rtnval = self._action(resource=volume, action="resize",
                              body={"size": size})
        return rtnval
