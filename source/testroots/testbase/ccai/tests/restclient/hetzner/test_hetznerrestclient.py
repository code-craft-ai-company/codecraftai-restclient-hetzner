"""
    .. module:: test_hetznerrestclient
    :platform: Darwin, Linux, Unix, Windows
    :synopsis: Tests for the Hetzner Cloud REST client.

    These tests drive the client through a fake transport rather than
    stubbing the client's own methods, so request building, reference
    reduction, pagination and error classification are all really exercised.

    .. moduleauthor:: Myron Walker <myron.walker@gmail.com>
"""

__author__ = "Myron Walker"
__copyright__ = "Copyright 2026, Code Craft AI LLC"
__credits__ = []


from ccai import testbase

from ccai.restclient.hetzner.hetznerapierror import HetznerApiRequestError
from ccai.restclient.hetzner.hetznerresource import (
    HetznerObject, identifier_of, wrap_hetzner_value
)
from ccai.restclient.hetzner.hetznerrestclient import HetznerRestClient

from ccai.tests.restclient.hetzner.fakesession import (
    FakeResponse, FakeSession
)


def _build_client():
    """
        Build a client over a fake session.

        :returns: A ``(client, session)`` pair.
    """
    session = FakeSession()
    client = HetznerRestClient(token="tok-abc", session=session)
    return client, session


# ----------------------------------------------------------------------
# HetznerObject
# ----------------------------------------------------------------------

def test_object_resolves_fields_by_attribute():
    obj = HetznerObject({"id": 42, "name": "worker-01"})

    assert obj.id == 42
    assert obj.name == "worker-01"
    assert obj["name"] == "worker-01"
    return


def test_object_reads_absent_field_as_none():
    obj = HetznerObject({"id": 42})

    # SDK-era consumer code guards optional attributes with getattr(...,
    # None); an absent field must not raise or those guards break.
    assert obj.labels is None
    assert getattr(obj, "public_net", None) is None
    return


def test_object_wraps_nested_objects():
    obj = HetznerObject({"server_type": {"name": "cx22", "cores": 2}})

    assert obj.server_type.name == "cx22"
    assert obj.server_type.cores == 2
    return


def test_object_wraps_objects_nested_in_lists():
    obj = HetznerObject({"volumes": [{"id": 1}, {"id": 2}]})

    assert [entry.id for entry in obj.volumes] == [1, 2]
    return


def test_object_refuses_private_attribute_lookups():
    obj = HetznerObject({"id": 42})

    # Resolving dunder lookups as API fields would make copy/pickle/inspect
    # machinery see phantom attributes.
    with testbase.raises(AttributeError):
        getattr(obj, "_ipython_canary")
    return


def test_object_does_not_shadow_mapping_methods():
    obj = HetznerObject({"id": 42, "name": "n"})

    assert callable(obj.keys) is True
    assert sorted(obj.keys()) == ["id", "name"]
    return


def test_object_setattr_writes_a_field():
    obj = HetznerObject({"id": 42})
    obj.name = "renamed"

    assert obj["name"] == "renamed"
    return


def test_identifier_of_accepts_object_dict_and_bare_id():
    assert identifier_of(HetznerObject({"id": 7})) == 7
    assert identifier_of({"id": 8}) == 8
    assert identifier_of(9) == 9
    return


def test_wrap_leaves_scalars_alone():
    assert wrap_hetzner_value("text") == "text"
    assert wrap_hetzner_value(5) == 5
    assert wrap_hetzner_value(None) is None
    return


# ----------------------------------------------------------------------
# transport
# ----------------------------------------------------------------------

def test_client_sends_bearer_token():
    client, session = _build_client()

    assert session.headers["Authorization"] == "Bearer tok-abc"
    assert session.headers["Accept"] == "application/json"
    return


def test_request_drops_none_query_parameters():
    client, session = _build_client()

    client.servers.get_by_name(name="worker-01")

    params = session.calls[0]["params"]
    assert params == {"name": "worker-01"}
    return


def test_request_returns_empty_object_for_a_bodiless_response():
    client, session = _build_client()
    session.queue(method="DELETE", path="/servers/5",
                  response=FakeResponse(status_code=204, text=""))

    client.servers.delete(server=HetznerObject({"id": 5}))

    assert session.calls[0]["method"] == "DELETE"
    return


def test_error_reason_comes_from_the_hetzner_error_envelope():
    client, session = _build_client()
    session.queue(method="GET", path="/servers",
                  response=FakeResponse(
                      status_code=404, reason="Not Found",
                      payload={"error": {"code": "not_found",
                                         "message": "server not found"}}))

    with testbase.raises(HetznerApiRequestError) as caught:
        client.servers.get_by_name(name="missing")

    assert caught.value.status == 404
    assert caught.value.reason == "not_found: server not found"
    return


def test_error_falls_back_to_the_http_reason():
    client, session = _build_client()
    session.queue(method="GET", path="/servers",
                  response=FakeResponse(status_code=500,
                                        reason="Server Error", text="oops"))

    with testbase.raises(HetznerApiRequestError) as caught:
        client.servers.get_by_name(name="worker-01")

    assert caught.value.status == 500
    assert caught.value.reason == "Server Error"
    assert caught.value.body == "oops"
    return


# ----------------------------------------------------------------------
# lookup and listing
# ----------------------------------------------------------------------

def test_get_by_name_returns_the_first_match():
    client, session = _build_client()
    session.queue(method="GET", path="/servers",
                  response=FakeResponse(
                      payload={"servers": [{"id": 1, "name": "worker-01"}]}))

    found = client.servers.get_by_name(name="worker-01")

    assert found.id == 1
    assert found.name == "worker-01"
    return


def test_get_by_name_returns_none_when_absent():
    client, session = _build_client()
    session.queue(method="GET", path="/servers",
                  response=FakeResponse(payload={"servers": []}))

    # Callers use this to decide whether to create; an absent resource is
    # the normal case, not a failure.
    assert client.servers.get_by_name(name="missing") is None
    return


def test_get_all_walks_every_page():
    client, session = _build_client()
    session.queue_collection(path="/servers", collection_key="servers",
                             entries=[{"id": 1}, {"id": 2}],
                             page=1, last_page=3)
    session.queue_collection(path="/servers", collection_key="servers",
                             entries=[{"id": 3}], page=2, last_page=3)
    session.queue_collection(path="/servers", collection_key="servers",
                             entries=[{"id": 4}], page=3, last_page=3)

    found = client.servers.get_all(label_selector="owner==ccai")

    # A truncated listing under-reports owned resources, which on a teardown
    # path means leaked infrastructure.
    assert [entry.id for entry in found] == [1, 2, 3, 4]
    assert len(session.calls) == 3
    assert session.calls[0]["params"]["label_selector"] == "owner==ccai"
    assert session.calls[0]["params"]["per_page"] == 50
    assert session.calls[2]["params"]["page"] == 3
    return


def test_get_all_stops_when_pagination_is_absent():
    client, session = _build_client()
    session.queue(method="GET", path="/volumes",
                  response=FakeResponse(payload={"volumes": [{"id": 1}]}))

    found = client.volumes.get_all()

    assert len(found) == 1
    assert len(session.calls) == 1
    return


def test_get_by_id_unwraps_the_singular_key():
    client, session = _build_client()
    session.queue(method="GET", path="/servers/11",
                  response=FakeResponse(
                      payload={"server": {"id": 11, "name": "worker-11"}}))

    found = client.servers.get_by_id(id=11)

    assert found.name == "worker-11"
    return


# ----------------------------------------------------------------------
# deletion
# ----------------------------------------------------------------------

@testbase.parametrize("group_name,singular,path", [
    ("servers", "server", "/servers/3"),
    ("volumes", "volume", "/volumes/3"),
    ("networks", "network", "/networks/3"),
    ("firewalls", "firewall", "/firewalls/3"),
    ("ssh_keys", "ssh_key", "/ssh_keys/3"),
])
def test_delete_accepts_the_groups_singular_keyword(group_name, singular,
                                                    path):
    client, session = _build_client()
    group = getattr(client, group_name)

    group.delete(**{singular: HetznerObject({"id": 3})})

    assert session.calls[0]["method"] == "DELETE"
    assert session.calls[0]["url"].endswith(path)
    return


def test_delete_accepts_a_bare_id_and_a_positional():
    client, session = _build_client()

    client.servers.delete(4)
    client.volumes.delete(volume=5)

    assert session.calls[0]["url"].endswith("/servers/4")
    assert session.calls[1]["url"].endswith("/volumes/5")
    return


def test_delete_without_a_target_raises():
    client, session = _build_client()

    # A silent no-op here would leave infrastructure running while
    # reporting success.
    with testbase.raises(TypeError):
        client.servers.delete()

    assert len(session.calls) == 0
    return


# ----------------------------------------------------------------------
# server creation
# ----------------------------------------------------------------------

def test_server_create_returns_a_response_carrying_the_server():
    client, session = _build_client()
    session.queue(method="POST", path="/servers",
                  response=FakeResponse(
                      status_code=201,
                      payload={"server": {"id": 21, "name": "worker-01"},
                               "action": {"id": 99},
                               "root_password": "pw"}))

    result = client.servers.create(name="worker-01", server_type="cx22",
                                   image="ubuntu-24.04")

    # Consumers unwrap with getattr(result, "server", None), the shape the
    # SDK's CreateServerResponse presented.
    assert result.server.id == 21
    assert result.action.id == 99
    return


def test_server_create_reduces_handles_to_wire_references():
    client, session = _build_client()
    network = HetznerObject({"id": 31, "name": "net-a"})
    firewall = HetznerObject({"id": 41, "name": "fw-a"})
    key = HetznerObject({"id": 51, "name": "key-a"})

    client.servers.create(name="worker-01", server_type="cx22",
                          image="ubuntu-24.04", location="nbg1",
                          ssh_keys=[key], networks=[network],
                          firewalls=[firewall], user_data="#cloud-config",
                          labels={"owner": "ccai"})

    body = session.calls[0]["body"]
    assert body["networks"] == [31]
    assert body["ssh_keys"] == [51]
    # This endpoint wraps each firewall id in an object, unlike its other
    # reference lists.
    assert body["firewalls"] == [{"firewall": 41}]
    assert body["location"] == "nbg1"
    assert body["labels"] == {"owner": "ccai"}
    return


def test_server_create_reduces_typed_objects_to_names():
    client, session = _build_client()
    server_type = HetznerObject({"name": "cx22", "cores": 2})
    image = HetznerObject({"name": "ubuntu-24.04", "id": 7})
    location = HetznerObject({"name": "nbg1"})

    client.servers.create(name="worker-01", server_type=server_type,
                          image=image, location=location)

    body = session.calls[0]["body"]
    assert body["server_type"] == "cx22"
    assert body["image"] == "ubuntu-24.04"
    assert body["location"] == "nbg1"
    return


def test_server_create_omits_unset_fields():
    client, session = _build_client()

    client.servers.create(name="worker-01", server_type="cx22",
                          image="ubuntu-24.04")

    body = session.calls[0]["body"]
    assert "location" not in body
    assert "user_data" not in body
    assert "labels" not in body
    assert "firewalls" not in body
    return


def test_server_power_actions_post_to_the_action_path():
    client, session = _build_client()

    client.servers.power_on(server=HetznerObject({"id": 61}))

    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"].endswith("/servers/61/actions/poweron")
    return


# ----------------------------------------------------------------------
# volumes
# ----------------------------------------------------------------------

def test_volume_create_returns_a_response_carrying_the_volume():
    client, session = _build_client()
    session.queue(method="POST", path="/volumes",
                  response=FakeResponse(
                      status_code=201,
                      payload={"volume": {"id": 71, "name": "data-01"},
                               "action": {"id": 98}}))

    result = client.volumes.create(name="data-01", size=32,
                                   location="nbg1",
                                   labels={"owner": "ccai"})

    assert result.volume.id == 71
    body = session.calls[0]["body"]
    assert body["size"] == 32
    assert body["location"] == "nbg1"
    return


def test_volume_attach_accepts_server_id_or_server():
    client, session = _build_client()
    volume = HetznerObject({"id": 71})

    client.volumes.attach(volume=volume, server_id=81)
    client.volumes.attach(volume=volume, server=HetznerObject({"id": 82}))

    first = session.calls[0]
    assert first["url"].endswith("/volumes/71/actions/attach")
    assert first["body"] == {"server": 81}
    assert session.calls[1]["body"] == {"server": 82}
    return


def test_volume_attach_without_a_target_raises():
    client, session = _build_client()

    with testbase.raises(TypeError):
        client.volumes.attach(volume=HetznerObject({"id": 71}))

    assert len(session.calls) == 0
    return


def test_volume_detach_and_resize_post_to_action_paths():
    client, session = _build_client()
    volume = HetznerObject({"id": 71})

    client.volumes.detach(volume=volume)
    client.volumes.resize(volume=volume, size=64)

    assert session.calls[0]["url"].endswith("/volumes/71/actions/detach")
    assert session.calls[0]["body"] is None
    assert session.calls[1]["url"].endswith("/volumes/71/actions/resize")
    assert session.calls[1]["body"] == {"size": 64}
    return


# ----------------------------------------------------------------------
# networks, firewalls, ssh keys
# ----------------------------------------------------------------------

def test_network_create_returns_the_network_itself():
    client, session = _build_client()
    session.queue(method="POST", path="/networks",
                  response=FakeResponse(
                      status_code=201,
                      payload={"network": {"id": 91, "name": "net-a",
                                           "ip_range": "10.0.0.0/16"}}))

    network = client.networks.create(name="net-a", ip_range="10.0.0.0/16",
                                     labels={"owner": "ccai"})

    # The SDK handed back a bound network, and consumers read network.id
    # straight off the result.
    assert network.id == 91
    assert network.ip_range == "10.0.0.0/16"
    return


def test_network_subnet_actions_post_to_action_paths():
    client, session = _build_client()

    client.networks.add_subnet(network=HetznerObject({"id": 91}),
                               ip_range="10.0.1.0/24",
                               network_zone="eu-central")

    call = session.calls[0]
    assert call["url"].endswith("/networks/91/actions/add_subnet")
    assert call["body"]["type"] == "cloud"
    assert call["body"]["network_zone"] == "eu-central"
    return


def test_firewall_create_lifts_the_single_entry_out_of_the_array():
    client, session = _build_client()
    session.queue(method="POST", path="/firewalls",
                  response=FakeResponse(
                      status_code=201,
                      payload={"firewalls": [{"id": 101, "name": "fw-a"}],
                               "actions": [{"id": 97}]}))

    firewall = client.firewalls.create(
        name="fw-a", rules=[{"direction": "in", "protocol": "tcp",
                             "port": "22",
                             "source_ips": ["0.0.0.0/0"]}])

    # This endpoint answers with a plural array; consumers hold the firewall
    # as a handle and read its id.
    assert firewall.id == 101
    assert firewall.name == "fw-a"
    return


def test_ssh_key_create_returns_the_key_itself():
    client, session = _build_client()
    session.queue(method="POST", path="/ssh_keys",
                  response=FakeResponse(
                      status_code=201,
                      payload={"ssh_key": {"id": 111, "name": "key-a"}}))

    key = client.ssh_keys.create(name="key-a", public_key="ssh-ed25519 AAA")

    assert key.id == 111
    assert session.calls[0]["body"]["public_key"] == "ssh-ed25519 AAA"
    return


def test_ssh_key_get_by_fingerprint():
    client, session = _build_client()
    session.queue(method="GET", path="/ssh_keys",
                  response=FakeResponse(
                      payload={"ssh_keys": [{"id": 111, "name": "key-a"}]}))

    key = client.ssh_keys.get_by_fingerprint(fingerprint="aa:bb")

    assert key.id == 111
    assert session.calls[0]["params"] == {"fingerprint": "aa:bb"}
    return
