# Implementation Plan — Hetzner Client

## Package Skeleton

- [x] 1. Create `source/packages/ccai/restclient/hetzner/` with an `apigroups/` subpackage.
- [x] 2. Add `requests` as the runtime dependency in `pyproject.toml`.

## Resource Model

- [x] 3. Implement `HetznerObject` as a `dict` subclass answering attribute access, with absent fields reading as `None`.
- [x] 4. Wrap nested objects and lists on read so `server.server_type.name` resolves.
- [x] 5. Refuse underscore-prefixed attribute lookups so copy/pickle/inspect machinery sees no phantom attributes.
- [x] 6. Implement `as_dict()` returning the plain wire-shaped dictionary.
- [x] 7. Implement `identifier_of` accepting a resource object, a plain dict, or a bare id.

## Transport

- [x] 8. Implement `HetznerRestClient` setting bearer and accept headers on the session at construction.
- [x] 9. Accept an injected session as the test seam and the hook for custom adapters or proxies.
- [x] 10. Implement `request()` with `None`-parameter dropping, JSON body encoding and a per-call timeout override.
- [x] 11. Return an empty `HetznerObject` for a bodiless `204` and for an undecodable body; wrap a non-object body under `data`.
- [x] 12. Implement `HetznerApiRequestError` carrying `status`, `reason` and `body`.
- [x] 13. Lift the reason out of the `{"error": {"code", "message"}}` envelope, falling back to the HTTP reason phrase.

## Pagination

- [x] 14. Implement `paginate()` requesting `per_page` at the API maximum of 50.
- [x] 15. Walk `page` up to `meta.pagination.last_page`, stopping when pagination is absent or the collection key is missing.
- [x] 16. Return the concatenated entries from every page.

## Api Group Base

- [x] 17. Implement `ResourceGroupBase` deriving behaviour from `COLLECTION_PATH`, `COLLECTION_KEY` and `SINGULAR_KEY`.
- [x] 18. Implement `get_by_name` filtering server-side and returning `None` on no match.
- [x] 19. Implement `get_all` over `paginate`, accepting `label_selector`, `name` and arbitrary further filters.
- [x] 20. Implement `get_by_id` unwrapping the singular key.
- [x] 21. Implement `delete` accepting the group's singular keyword or a positional, raising `TypeError` when neither is given.
- [x] 22. Implement `_create` dropping `None` body values, and `_action` posting to `/{collection}/{id}/actions/{action}`.

## Api Groups

- [x] 23. Implement `ServerGroup.create` reducing object references to wire references, including the `{"firewall": id}` wrapping that endpoint requires.
- [x] 24. Implement `_name_or_value` and `_key_reference` for the name-valued and id-or-name-valued references.
- [x] 25. Implement `ServerGroup.power_on`, `.power_off` and `.reboot`.
- [x] 26. Implement `VolumeGroup.create` without defaulting a placement, so the API's own error surfaces rather than storage landing somewhere unchosen.
- [x] 27. Implement `VolumeGroup.attach` accepting `server` or `server_id` and raising `TypeError` when neither is given, plus `.detach` and `.resize`.
- [x] 28. Implement `NetworkGroup.create` returning the network itself, plus `.add_subnet` and `.delete_subnet`.
- [x] 29. Implement `FirewallGroup.create` lifting the single entry out of the `firewalls` array, plus `.set_rules` and `.apply_to_resources`.
- [x] 30. Implement `SshKeyGroup.create` returning the key itself, plus `.get_by_fingerprint`.

## Tests

- [x] 31. Build `FakeSession` and `FakeResponse` with per-`(METHOD, path)` queueing and a `queue_collection` helper that emits a correct `meta.pagination` block.
- [x] 32. Cover the `HetznerObject` contract: attribute and item access, `None` for absent, nested wrapping, private-lookup refusal, unshadowed mapping methods.
- [x] 33. Cover `identifier_of` across object, dict and bare-id references.
- [x] 34. Cover bearer headers, `None`-parameter dropping, and the bodiless `204` response.
- [x] 35. Cover the error-envelope reason and the HTTP reason fallback.
- [x] 36. Cover `get_by_name` hit and miss, `get_by_id` unwrapping, multi-page `get_all`, and the no-pagination stop.
- [x] 37. Cover `delete` under every group's singular keyword via `@testbase.parametrize`, positionally, and the missing-target `TypeError`.
- [x] 38. Cover server creation: response envelope, handle reduction, name reduction, and omission of unset fields.
- [x] 39. Cover volume creation, attach by either keyword, the missing-target `TypeError`, detach and resize.
- [x] 40. Cover the network, firewall-array and ssh-key creation response shapes, and `get_by_fingerprint`.

## Open Items

- [ ] 41. No action waiter. Server creation, volume attach/detach/resize, subnet edits and firewall application all return an `action` record, but nothing polls it to completion. Callers currently have to wait themselves, and there is no `/actions` group to poll against.
- [ ] 42. Reconcile with `codecraftai-restclient-base`. `pyproject.toml` declares it alongside `codecraftai-credentials` and `codecraftai-errors`, but nothing under `source/packages` imports any of the three. Either build on `RestClientBase` or drop the unused dependencies.
- [ ] 43. Accept a typed credential object. `HetznerRestClient` takes `token` as a plain string, which the repository coding standard in `AGENTS.md` forbids on the API surface.
- [ ] 44. Add the `aspects` parameter. No method takes one, so retry, backoff and logging policy is not caller-controlled; `timeout_seconds` at construction and per call is the only lever.
- [ ] 45. No retry on transient HTTP failures, and no handling of Hetzner's rate-limit response — a 429 raises like any other non-success status.
- [ ] 46. Add property-based tests using `ccai.testbase.properties`. All 36 tests are example-based; page-walking totality and reference reduction are the natural candidates.
- [ ] 47. Add a gated live-API smoke test. Nothing currently exercises a real Hetzner endpoint.
- [ ] 48. No images, locations, server-types or load-balancer groups. Only servers, volumes, networks, firewalls and ssh keys are covered; image and server-type references are passed through as caller-supplied names without a lookup path.
