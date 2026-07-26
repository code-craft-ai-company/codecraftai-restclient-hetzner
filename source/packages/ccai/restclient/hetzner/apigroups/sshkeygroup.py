"""
    .. module:: sshkeygroup
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: :class:`SshKeyGroup` — the ``/ssh_keys`` api group.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from typing import Any, Dict, Optional

from ccai.restclient.hetzner.apigroups.resourcegroupbase import (
    ResourceGroupBase
)
from ccai.restclient.hetzner.hetznerresource import HetznerObject


class SshKeyGroup(ResourceGroupBase):
    """
        The Hetzner Cloud ssh-keys collection.
    """

    COLLECTION_PATH = "/ssh_keys"
    COLLECTION_KEY = "ssh_keys"
    SINGULAR_KEY = "ssh_key"

    def create(self, *, name: str, public_key: str,
               labels: Optional[Dict[str, str]] = None,
               **fields: Any) -> HetznerObject:
        """
            Register an ssh public key.

            :param name: The key name.
            :param public_key: The public key material, in OpenSSH format.
            :param labels: Optional labels.
            :param fields: Any further key fields.

            :returns: The created key itself, not a response envelope —
                matching the SDK, whose ``ssh_keys.create`` handed back a
                bound key, so callers holding it as a handle keep working.
        """
        body: Dict[str, Any] = {
            "name": name,
            "public_key": public_key,
            "labels": labels,
        }
        for key, value in fields.items():
            body[key] = value

        payload = self._create(body=body)
        rtnval = self._unwrap(payload=payload)
        return rtnval

    def get_by_fingerprint(self, *,
                           fingerprint: str) -> Optional[HetznerObject]:
        """
            Look an ssh key up by its fingerprint.

            :param fingerprint: The key fingerprint.

            :returns: The key, or ``None`` when no key carries that
                fingerprint.
        """
        payload = self._client.request(
            method="GET", path=self.COLLECTION_PATH,
            params={"fingerprint": fingerprint})

        entries = payload.get(self.COLLECTION_KEY, None)
        if entries is None or len(entries) == 0:
            rtnval = None
            return rtnval

        from ccai.restclient.hetzner.hetznerresource import (
            wrap_hetzner_value
        )
        rtnval = wrap_hetzner_value(entries[0])
        return rtnval
