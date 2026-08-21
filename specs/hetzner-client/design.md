# Design

## Overview

`codecraftai-restclient-hetzner` is a pure-Python client for the Hetzner Cloud
API v1. It exists to remove the `hcloud` SDK dependency from the provisioning
venue while keeping the call shapes that venue code was written against.

Hetzner is the most uniform API in this fleet: one bearer token, one base URL,
snake_case JSON, `page`/`per_page` pagination on every collection, entries
nested under the resource's plural name, and a single resource nested under
its singular name. That uniformity is what makes `ResourceGroupBase` possible
— nearly all of each group's behaviour is derived from three class attributes.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  codecraftai-provisioning / venues / hetzner             │
└──────────────────────────┬───────────────────────────────┘
                           ▼
            ┌──────────────────────────────┐
            │      HetznerRestClient       │
            │  .servers  .volumes          │
            │  .networks .firewalls        │
            │  .ssh_keys                   │
            │  request() / paginate()      │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │      ResourceGroupBase       │
            │  COLLECTION_PATH             │
            │  COLLECTION_KEY              │
            │  SINGULAR_KEY                │
            └──────────────┬───────────────┘
                           ▼
            ┌──────────────────────────────┐
            │  requests.Session (injected  │
            │  or built) → api.hetzner.cloud│
            └──────────────────────────────┘
```

---

## Module Layout

```
source/packages/ccai/restclient/hetzner/
├── __init__.py
├── hetznerrestclient.py       # HetznerRestClient: transport + pagination
├── hetznerresource.py         # HetznerObject, wrap_hetzner_value, identifier_of
├── hetznerapierror.py         # HetznerApiRequestError
└── apigroups/
    ├── __init__.py
    ├── resourcegroupbase.py   # ResourceGroupBase
    ├── servergroup.py         # ServerGroup
    ├── volumegroup.py         # VolumeGroup
    ├── networkgroup.py        # NetworkGroup
    ├── firewallgroup.py       # FirewallGroup
    └── sshkeygroup.py         # SshKeyGroup
```

---

## Notable Choices

**Three class attributes drive each group.** `ResourceGroupBase` reads
`COLLECTION_PATH`, `COLLECTION_KEY` and `SINGULAR_KEY` and derives from them
`get_by_name`, `get_all`, `get_by_id`, `delete`, the `_create` POST, the
`_unwrap` of a singular response, and the `_action` POST path. `ServerGroup`
declares `/servers`, `servers`, `server` and adds `create`, `power_on`,
`power_off` and `reboot` — nothing else. The uniformity is real, not imposed:
it is how the API is shaped.

**Objects are inert; groups own the verbs.** `HetznerObject` has no client
back-reference and no mutating methods. `client.volumes.detach(volume=volume)`
is the call, not `volume.detach()`. This is the `hcloud` shape and the shape
consumer code already uses. It also keeps the response model trivially
constructible in tests — a bare `HetznerObject({"id": 5})` is a valid handle
anywhere a resource is accepted. This differs deliberately from the Linode
client in this fleet, which is active record.

**Absent fields read as `None`, and that is the migration contract.** Code
written against the SDK guards optional attributes with
`getattr(obj, "field", None)`. Raising `AttributeError` on an absent field
would break every one of those guards silently — they would start taking the
error path instead of the default path. So `__getattr__` returns `None`, and
only underscore-prefixed names raise, which keeps copy, pickle and inspection
machinery from seeing phantom attributes. No wire payload uses the names
`keys`, `values`, `items` or `get`, so the inherited mapping methods are safe
to leave unshadowed.

**`identifier_of` is the reference-reduction primitive.** Every verb that
takes a resource routes through it, and it handles all three shapes a caller
might be holding: a `HetznerObject` or plain dict (read `id`), an object with
an `id` attribute, or a bare id (return as-is). Server creation needs two more
reductions on top: `_name_or_value` for the string-named references (server
type, image, location) and `_key_reference` for ssh keys, which the endpoint
accepts by either id or name.

**The wire format is not quite uniform, and the groups absorb it.** Three
endpoints deviate and each deviation is handled at the group rather than
leaking to callers: server and volume creation answer with an envelope
(`{"server": ..., "action": ..., "root_password": ...}`) which is returned
whole because consumers read `result.server`; network and ssh-key creation
answer with a singular key which is unwrapped, because the SDK handed back a
bound object; and firewall creation answers with a `firewalls` ARRAY whose
single entry is lifted out.

**Pagination is complete, and stops on two conditions.** `paginate` requests
`per_page=50` (the API maximum) and walks `page` up to
`meta.pagination.last_page`. It also stops when the collection key is absent
from a response, which prevents an unexpected payload shape from looping. A
silently truncated first page would under-report owned resources, which on a
teardown path means leaked infrastructure — so completeness here is a
correctness property, not a convenience.

**Errors are thin on purpose.** There is one exception type. The reason is
lifted out of Hetzner's `{"error": {"code", "message"}}` envelope as
`"<code>: <message>"` because the code is what a consumer would branch on and
the message is what a human needs, and the HTTP reason phrase is the fallback
when the body is unhelpful. Translating 404 into a typed `NotFound` is a
policy decision that belongs to the consumer, so `status` is exposed on the
exception and left uninterpreted.

---

## Relationship to `codecraftai-restclient-base`

The client does not subclass `RestClientBase` and does not take an `aspects`
parameter, though `pyproject.toml` declares `codecraftai-restclient-base`,
`codecraftai-credentials` and `codecraftai-errors` as dependencies. Nothing
under `source/packages` imports any of the three; the API token enters
`HetznerRestClient.__init__` as a plain string. Both divergences are open
items in `tasks.md`, recorded here so this design is not read as claiming a
base-class integration that does not exist.

---

## Testing Strategy

Tests live under
`source/testroots/testbase/ccai/tests/restclient/hetzner/` and run under the
testbase runner, not pytest:

```
PYTHONPATH="$PWD/source/packages:$PWD/source/testroots/testbase" \
    .venv/bin/testbase testing run --root source/testroots/testbase/ccai \
    --includes="*" --output=./.output
```

`fakesession.py` provides `FakeSession` and `FakeResponse`. The session is the
only seam: because `HetznerRestClient` accepts one at construction, the tests
drive real request building, reference reduction, pagination and error
classification rather than stubbing the client's own methods. `FakeSession`
matches queued responses by `(METHOD, path-suffix)` and falls through to a
default, so each test declares only the traffic it cares about;
`queue_collection` builds a correctly-shaped paginated page including the
`meta.pagination` block.

The suite is example-based and offline. Coverage concentrates on the contracts
that would regress silently: the `None`-for-absent field contract and nested
wrapping; `identifier_of` across all three reference shapes; `None`-parameter
dropping; the error-envelope reason and its HTTP fallback; multi-page walking
with the correct `per_page` and `page` parameters, plus the no-pagination stop
condition; `delete` under each group's singular keyword, positionally, and the
`TypeError` when no target is given; the three deviating creation response
shapes; and the action-path composition for power, subnet and volume verbs.
