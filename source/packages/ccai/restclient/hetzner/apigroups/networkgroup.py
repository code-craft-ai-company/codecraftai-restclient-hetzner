"""
    .. module:: networkgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`NetworkGroup` — the ``/networks`` api group.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, List, Optional

from ccai.restclient.hetzner.apigroups.resourcegroupbase import (
    ResourceGroupBase
)
from ccai.restclient.hetzner.hetznerresource import HetznerObject


class NetworkGroup(ResourceGroupBase):
    """
        The Hetzner Cloud private-networks collection.
    """

    COLLECTION_PATH = "/networks"
    COLLECTION_KEY = "networks"
    SINGULAR_KEY = "network"

    def create(self, *, name: str, ip_range: str,
               subnets: Optional[List[Dict[str, Any]]] = None,
               routes: Optional[List[Dict[str, Any]]] = None,
               labels: Optional[Dict[str, str]] = None,
               **fields: Any) -> HetznerObject:
        """
            Create a private network.

            :param name: The network name.
            :param ip_range: The network CIDR.
            :param subnets: Optional subnets to create with the network.
            :param routes: Optional routes.
            :param labels: Optional labels.
            :param fields: Any further network fields.

            :returns: The created network itself, not a response envelope —
                matching the SDK, whose ``networks.create`` handed back a
                bound network, so callers reading ``network.id`` keep working.
        """
        body: Dict[str, Any] = {
            "name": name,
            "ip_range": ip_range,
            "subnets": subnets,
            "routes": routes,
            "labels": labels,
        }
        for key, value in fields.items():
            body[key] = value

        payload = self._create(body=body)
        rtnval = self._unwrap(payload=payload)
        return rtnval

    def add_subnet(self, *, network: Any, ip_range: str,
                   network_zone: str,
                   subnet_type: str = "cloud") -> HetznerObject:
        """
            Add a subnet to a network.

            :param network: The network, an object or a bare id.
            :param ip_range: The subnet CIDR, within the network's range.
            :param network_zone: The network zone, e.g. ``eu-central``.
            :param subnet_type: The subnet type; ``cloud`` by default.

            :returns: The action response.
        """
        rtnval = self._action(resource=network, action="add_subnet",
                              body={"ip_range": ip_range,
                                    "network_zone": network_zone,
                                    "type": subnet_type})
        return rtnval

    def delete_subnet(self, *, network: Any,
                      ip_range: str) -> HetznerObject:
        """
            Remove a subnet from a network.

            :param network: The network, an object or a bare id.
            :param ip_range: The subnet CIDR to remove.

            :returns: The action response.
        """
        rtnval = self._action(resource=network, action="delete_subnet",
                              body={"ip_range": ip_range})
        return rtnval
