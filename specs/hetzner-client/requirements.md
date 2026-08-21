# Requirements

## Introduction

The `hetzner-client` feature provides a pure-Python REST client for the
Hetzner Cloud API v1, replacing the `hcloud` SDK for the provisioning venue.
The API is plain REST over HTTPS with JSON bodies and a bearer API token, so
the client speaks it directly.

Five collections are covered — servers, volumes, private networks, firewalls
and ssh keys — reached through public attributes on `HetznerRestClient` named
to match the SDK's grouping (`client.servers`, `client.volumes`,
`client.networks`, `client.firewalls`, `client.ssh_keys`). Every group derives
listing, lookup and deletion from `ResourceGroupBase` and adds only the verbs
unique to it.

The package lives at `source/packages/ccai/restclient/hetzner` and its only
runtime dependency is `requests`. It does not import `RestClientBase`, does
not take an `aspects` parameter, and takes the API token as a plain string
rather than a typed credential — all three are recorded as open items in
`tasks.md`.

Two things shape the design more than anything else. Hetzner's JSON is already
snake_case, so no name translation is needed; and consumer code migrating off
`hcloud` is full of `getattr(obj, "field", None)` guards, so an absent field
must read as `None` rather than raise.

---

## Requirements

### Requirement 1: Authenticate With a Bearer API Token

**User Story:** As a provisioner, I want the client to carry the API token on
every request so that authentication is configured once at construction.

#### Acceptance Criteria

1. WHEN a `HetznerRestClient` is constructed with a token THE SYSTEM SHALL set
   `Authorization: Bearer <token>` and `Accept: application/json` as session
   headers, so every request through that session carries them.
2. THE SYSTEM SHALL accept an injected session object, which is both the test
   seam and the way a caller supplies custom transport adapters or proxies,
   and SHALL otherwise build its own `requests.Session`.
3. THE SYSTEM SHALL accept an overridable base URL, defaulting to
   `https://api.hetzner.cloud/v1`, and SHALL strip any trailing slash from it.
4. THE SYSTEM SHALL apply a default per-request timeout, overridable per call.

### Requirement 2: Perform and Decode Requests

**User Story:** As a group author, I want one request method that handles
encoding, error classification and decoding so that each group only composes
paths and bodies.

#### Acceptance Criteria

1. THE SYSTEM SHALL compose the request URL as base URL plus the supplied
   path, and SHALL send `Content-Type: application/json` only when a body is
   present.
2. THE SYSTEM SHALL drop query parameters whose value is `None`, so an unset
   label selector is simply absent from the request rather than sent empty.
3. WHEN the response status is outside 2xx THE SYSTEM SHALL raise
   `HetznerApiRequestError` carrying `status`, `reason` and `body`, with a
   message naming the method, path, status and reason.
4. WHEN the failure body carries `{"error": {"code": ..., "message": ...}}`
   THE SYSTEM SHALL use `"<code>: <message>"` as the reason, falling back to
   the message alone, then the code alone, then the HTTP reason phrase.
5. WHEN a success response carries no body — deletes answer `204` — THE SYSTEM
   SHALL return an empty `HetznerObject` rather than raise.
6. WHEN a success body is present but undecodable THE SYSTEM SHALL return an
   empty `HetznerObject`; WHEN it decodes to something other than an object
   THE SYSTEM SHALL return it wrapped under the key `data`.

### Requirement 3: Present Responses As Attribute-Addressable Objects

**User Story:** As a consumer migrating off the `hcloud` SDK, I want responses
to answer both attribute and item access so that my existing call sites keep
working unchanged.

#### Acceptance Criteria

1. THE SYSTEM SHALL return responses as `HetznerObject`, a `dict` subclass, so
   `server["server_type"]["name"]` and `server.server_type.name` both resolve.
2. WHEN a field is absent THE SYSTEM SHALL return `None` rather than raise, so
   `getattr(obj, "field", None)` guards behave as they did against the SDK.
3. WHEN a field holds a nested object or a list of objects THE SYSTEM SHALL
   wrap it, so a second attribute hop such as `server.server_type.name`
   resolves.
4. WHEN an attribute name begins with `_` THE SYSTEM SHALL raise
   `AttributeError` rather than resolve it as an API field, so copy, pickle
   and inspection machinery does not observe phantom attributes.
5. THE SYSTEM SHALL NOT shadow the inherited mapping methods (`keys`,
   `values`, `items`, `get`); no Hetzner payload uses those names, since
   collections arrive under the resource's plural name and pagination under
   `meta`.
6. THE SYSTEM SHALL expose `as_dict()` returning the plain wire-shaped
   dictionary.
7. Resources SHALL be inert data, NOT active record. Mutations live on the
   api groups (`client.volumes.detach(volume=volume)`), which is the shape the
   SDK used and the shape consumers already call.

### Requirement 4: Accept Whatever Reference the Caller Holds

**User Story:** As a provisioner assembling resources from earlier creates, I
want to pass a live handle, a plain dict, or a bare id interchangeably so that
I do not have to unwrap ids at every call site.

#### Acceptance Criteria

1. WHEN a verb takes a resource THE SYSTEM SHALL accept a `HetznerObject`, a
   plain decoded dict, or a bare id, and SHALL reduce it to the id the wire
   format wants.
2. WHEN a server is created THE SYSTEM SHALL reduce `server_type`, `image` and
   `location` to their names, accepting a string or an object carrying one,
   and falling back to the id when a dict has no name.
3. WHEN a server is created THE SYSTEM SHALL reduce `networks` and `volumes`
   to bare ids, `ssh_keys` to an id when present or a name otherwise, and
   `firewalls` to `{"firewall": <id>}` objects — that endpoint wraps firewall
   ids, unlike its other reference lists.
4. WHEN a creation body is sent THE SYSTEM SHALL omit every field whose value
   is `None` rather than send explicit nulls.
5. THE SYSTEM SHALL accept arbitrary further fields through a keyword catch-all
   on each `create`, passing them into the body unchanged.

### Requirement 5: Cover the Collection Verbs Uniformly

**User Story:** As a provisioner, I want every collection to expose the same
lookup, listing and deletion verbs so that group-specific knowledge is limited
to the verbs that are genuinely group-specific.

#### Acceptance Criteria

1. THE SYSTEM SHALL expose `get_by_name(name)` on every group, filtering the
   collection server-side by exact name, and SHALL return `None` when nothing
   matches — callers use this to decide whether to create, so absence is the
   normal case, not a failure.
2. THE SYSTEM SHALL expose `get_by_id(id)` returning the resource lifted out
   of its singular key, or the whole payload when no singular key is present.
3. THE SYSTEM SHALL expose `get_all(label_selector, name, **filters)`
   returning every matching resource across every page.
4. THE SYSTEM SHALL expose `delete` naming the resource by the group's
   singular keyword — `delete(server=...)`, `delete(volume=...)`,
   `delete(network=...)`, `delete(firewall=...)`, `delete(ssh_key=...)` —
   and SHALL also accept a single positional argument.
5. WHEN `delete` is called with no resource THE SYSTEM SHALL raise
   `TypeError` and issue no request; a silent no-op would leave infrastructure
   running while reporting success.

### Requirement 6: Walk Every Page of a Collection

**User Story:** As a teardown path, I want a listing to return the whole
collection so that I do not leak resources that fell past the first page.

#### Acceptance Criteria

1. THE SYSTEM SHALL request `per_page` at the API's maximum of 50, minimising
   round trips.
2. THE SYSTEM SHALL read `meta.pagination.last_page` and SHALL keep requesting
   successive `page` numbers until the last page is reached.
3. WHEN a response carries no usable pagination block THE SYSTEM SHALL stop
   after that page rather than loop.
4. WHEN a response carries no entry for the collection key THE SYSTEM SHALL
   stop rather than treat it as an empty page and continue.
5. THE SYSTEM SHALL return the concatenated entries from every page.

### Requirement 7: Cover the Server, Volume, Network, Firewall and Key Verbs

**User Story:** As a provisioner, I want the venue-specific operations each
collection needs so that a full host lifecycle can be driven through this
client.

#### Acceptance Criteria

1. `ServerGroup.create` SHALL accept name, server type, image, location, ssh
   keys, networks, firewalls, volumes, user data, labels and
   `start_after_create`, and SHALL return the raw creation response carrying
   `server`, `action` and `root_password` — the shape the SDK's
   `CreateServerResponse` presented, so `result.server` keeps working.
2. `ServerGroup` SHALL expose `power_on`, `power_off` and `reboot`.
3. `VolumeGroup.create` SHALL accept name, size, location, server, labels,
   automount and format, and SHALL return the raw response carrying `volume`
   and `action`. It SHALL NOT default a placement: the API requires exactly
   one of location or server, and inventing a location would silently place
   storage where the caller did not choose.
4. `VolumeGroup` SHALL expose `attach`, `detach` and `resize`. `attach` SHALL
   accept the target as either `server` or `server_id`, because call sites
   hold each, and SHALL raise `TypeError` when neither is supplied.
5. `NetworkGroup.create` SHALL accept name, ip range, subnets, routes and
   labels, and SHALL return the created network itself rather than a response
   envelope, matching the SDK's bound-object return.
6. `NetworkGroup` SHALL expose `add_subnet` and `delete_subnet`, with
   `add_subnet` defaulting the subnet type to `cloud`.
7. `FirewallGroup.create` SHALL return the created firewall itself. That
   endpoint answers with a `firewalls` ARRAY rather than a singular key, so
   THE SYSTEM SHALL lift the single entry out.
8. `FirewallGroup` SHALL expose `set_rules` replacing the complete rule set,
   and `apply_to_resources` translating a list of servers into Hetzner's
   `{"type": "server", "server": {"id": ...}}` target shape.
9. `SshKeyGroup.create` SHALL return the created key itself, and the group
   SHALL additionally expose `get_by_fingerprint` returning `None` on no match.

### Requirement 8: Model Time-Taking Mutations As Actions

**User Story:** As a provisioner, I want mutations that take time to be posted
to Hetzner's action endpoints so that the returned action record is available
to the caller.

#### Acceptance Criteria

1. WHEN a group verb performs a time-taking mutation THE SYSTEM SHALL POST to
   `/{collection}/{id}/actions/{action}` and SHALL return the decoded response
   carrying the `action` record.
2. THE SYSTEM SHALL drop `None` values from an action body, so an unset
   `automount` is absent rather than null.
3. THE SYSTEM SHALL NOT poll the action to completion. Waiting is currently
   the caller's responsibility; see the open item in `tasks.md`.

### Requirement 9: Keep Error Classification Thin

**User Story:** As a consumer with my own typed error hierarchy, I want the
transport to report faithfully rather than interpret so that status-to-meaning
policy stays mine.

#### Acceptance Criteria

1. THE SYSTEM SHALL raise exactly one exception type,
   `HetznerApiRequestError`, for every non-success status.
2. THE SYSTEM SHALL expose `status`, `reason` and `body` on the exception so a
   consumer can classify without re-parsing the message.
3. THE SYSTEM SHALL NOT translate status codes into distinct exception types;
   that is consumer policy, not transport behaviour.
