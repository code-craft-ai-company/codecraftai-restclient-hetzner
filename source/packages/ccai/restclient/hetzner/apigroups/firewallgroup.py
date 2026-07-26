"""
    .. module:: firewallgroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`FirewallGroup` — the ``/firewalls`` api group.

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
    HetznerObject, identifier_of, wrap_hetzner_value
)


class FirewallGroup(ResourceGroupBase):
    """
        The Hetzner Cloud firewalls collection.
    """

    COLLECTION_PATH = "/firewalls"
    COLLECTION_KEY = "firewalls"
    SINGULAR_KEY = "firewall"

    def create(self, *, name: str,
               rules: Optional[List[Dict[str, Any]]] = None,
               labels: Optional[Dict[str, str]] = None,
               apply_to: Optional[List[Dict[str, Any]]] = None,
               **fields: Any) -> HetznerObject:
        """
            Create a firewall.

            :param name: The firewall name.
            :param rules: The firewall rules, already in Hetzner's rule shape.
            :param labels: Optional labels.
            :param apply_to: Optional immediate application targets.
            :param fields: Any further firewall fields.

            :returns: The created firewall itself.  This endpoint answers
                with a ``firewalls`` ARRAY rather than a singular key, so the
                single entry is lifted out — callers hold the firewall as a
                handle and read its id, exactly as they did with the SDK's
                bound object.
        """
        body: Dict[str, Any] = {
            "name": name,
            "rules": rules,
            "labels": labels,
            "apply_to": apply_to,
        }
        for key, value in fields.items():
            body[key] = value

        payload = self._create(body=body)

        entries = payload.get(self.COLLECTION_KEY, None)
        if entries is not None and len(entries) > 0:
            rtnval = wrap_hetzner_value(entries[0])
            return rtnval

        rtnval = self._unwrap(payload=payload)
        return rtnval

    def set_rules(self, *, firewall: Any,
                  rules: List[Dict[str, Any]]) -> HetznerObject:
        """
            Replace a firewall's rule set.

            :param firewall: The firewall, an object or a bare id.
            :param rules: The complete replacement rule set.

            :returns: The action response.
        """
        rtnval = self._action(resource=firewall, action="set_rules",
                              body={"rules": rules})
        return rtnval

    def apply_to_resources(self, *, firewall: Any,
                           servers: List[Any]) -> HetznerObject:
        """
            Apply a firewall to servers.

            :param firewall: The firewall, an object or a bare id.
            :param servers: The servers to protect — objects or bare ids.

            :returns: The action response.
        """
        targets = [{"type": "server",
                    "server": {"id": identifier_of(entry)}}
                   for entry in servers]
        rtnval = self._action(resource=firewall,
                              action="apply_to_resources",
                              body={"apply_to": targets})
        return rtnval
