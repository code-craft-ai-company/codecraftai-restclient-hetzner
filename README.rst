==============================
codecraftai-restclient-hetzner
==============================

A pure-Python REST client for the `Hetzner Cloud API v1
<https://docs.hetzner.cloud/>`_.

The Hetzner Cloud API is plain REST over HTTPS with JSON bodies and a Bearer
API token, so this package speaks it directly rather than depending on the
``hcloud`` SDK.

Shape
=====

The api groups mirror the SDK's grouping, so call sites written against
``hcloud`` keep their shape:

.. code-block:: python

    from ccai.restclient.hetzner.hetznerrestclient import HetznerRestClient

    client = HetznerRestClient(token=token)

    existing = client.servers.get_by_name(name="worker-01")

    result = client.servers.create(
        name="worker-01", server_type="cx22", image="ubuntu-24.04",
        location="nbg1", ssh_keys=[key], networks=[network],
        firewalls=[firewall], labels={"owner": "ccai"})
    server = result.server

    owned = client.servers.get_all(label_selector="owner==ccai")

    client.servers.delete(server=server)

Five collections are exposed — ``servers``, ``volumes``, ``networks``,
``firewalls`` and ``ssh_keys`` — each with ``get_by_name``, ``get_all``,
``get_by_id``, ``create`` and ``delete``.  Volumes additionally carry
``attach``, ``detach`` and ``resize``.

Design notes
============

**Objects are attribute addressable, not active record.** Responses are
``HetznerObject`` — a ``dict`` that also answers attribute access, with
absent fields reading as ``None`` so ``getattr(obj, "field", None)`` guards
written against the SDK keep behaving the same way.  Nested objects are
wrapped too, so ``server.server_type.name`` resolves.  Mutations are NOT
methods on the objects; they live on the api groups
(``client.volumes.detach(volume=volume)``), which is the shape the SDK used
and the shape consumers already call.

**Reference parameters accept whatever the caller holds.** ``create`` and the
action verbs take resource objects, plain dicts or bare ids, and reduce them
to the ids the wire format wants — because consumer code assembles handles
from earlier creates and passes them straight through.

**Pagination is complete.** ``get_all`` walks every page via
``meta.pagination``.  A silently truncated first page would under-report owned
resources, which on a teardown path means leaked infrastructure.

**Errors are thin.** ``HetznerApiRequestError`` carries ``status``,
``reason`` and ``body``; the reason is lifted out of Hetzner's
``{"error": {"code", "message"}}`` envelope.  Translating status codes into a
typed hierarchy is the consumer's policy, not the transport's.
