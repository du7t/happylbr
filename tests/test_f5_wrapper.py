import pytest
from api_libs.helper import get_ff

import libs.f5_wrapper as f5_wrapper
from conf.static import balancers


f5 = f5_wrapper.F5Manager(
    address=balancers['AMS02']['F5']['address'],
    user=get_ff('BALANCERS')['AMS02']['F5']['user'],
    password=get_ff('BALANCERS')['AMS02']['F5']['password'],
    partition=balancers['AMS02']['F5']['partition']
)


@pytest.mark.parametrize(
    ("value_input", "value_expected"),
    [
        ("127.0.0.1%2", "127.0.0.1"),
        ("1.1.1.1", "1.1.1.1"),
        ("", None),
        (None, None),
    ]
)
def test_clean_value(value_input, value_expected):
    assert f5.clean_value(value_input) == value_expected


def test_node_exists(lbr_data):
    assert not f5.node_exists(name=lbr_data['node1'])


def test_create_node(lbr_data):
    node = f5.create_node(name=lbr_data['node1'], address=lbr_data['address1'])

    assert node
    assert node.attrs['kind'] == 'tm:ltm:node:nodestate'
    assert f5.node_exists(name=lbr_data['node1'])


def test_get_node(lbr_data):
    node = f5.get_node(name=lbr_data['node1'])

    assert node
    assert f5.clean_value(node.attrs['address']) == lbr_data['address1']


def test_get_node_address(lbr_data):
    address = f5.get_node_address(name=lbr_data['node1'])

    assert address == lbr_data['address1']


def test_nodes():
    nodes = f5.nodes

    assert nodes
    assert isinstance(nodes, list)
    assert nodes[0].kind == 'tm:ltm:node:nodestate'


def test_get_node_by_address(lbr_data):
    node = f5.get_node_by_address(address=lbr_data['address1'])

    assert node
    assert node.attrs['name'] == lbr_data['node1']


def test_pool_exists(lbr_data):
    assert not f5.pool_exists(name=lbr_data['pool1'])


def test_create_pool(lbr_data):
    pool = f5.create_pool(name=lbr_data['pool1'], members=[lbr_data['member1']])

    assert pool
    assert pool.kind == 'tm:ltm:pool:poolstate'
    assert f5.pool_exists(name=lbr_data['pool1'])


def test_get_pool(lbr_data):
    pool = f5.get_pool(name=lbr_data['pool1'])

    assert pool
    assert pool.name == lbr_data['pool1']
    assert "tcp" in pool.monitor


def test_get_pool_member(lbr_data):
    member = f5.get_pool_member(pool_name=lbr_data['pool1'], member_name=lbr_data['member1'])

    assert member
    assert member.kind == 'tm:ltm:pool:members:membersstate'


def test_collect_pool_members(lbr_data):
    members = f5.collect_pool_members(name=lbr_data['pool1'])

    assert members
    assert isinstance(members, list)
    assert members[0].kind == 'tm:ltm:pool:members:membersstate'


def test_get_node_references():
    used_in_pools = f5.get_node_references(name='lem01-t01-awp01')
    assert len(used_in_pools) > 0
    assert 'lem01-t01-awp_8080' in used_in_pools


def test_get_pool_members(lbr_data):
    members = f5.get_pool_members(name=lbr_data['pool1'])

    assert members
    assert isinstance(members, list)
    assert isinstance(members[0], dict)
    assert members[0]['name'] == lbr_data['node1']
    assert members[0]['port'] == lbr_data['node1_port1']


def test_add_pool_members(lbr_data):
    added_members = f5.add_pool_members(name=lbr_data['pool1'], members=[lbr_data['member2']])

    assert added_members
    assert isinstance(added_members, list)
    assert added_members[0].name == lbr_data['member2']


def test_pool_member_exists(lbr_data):
    assert f5.pool_member_exists(pool_name=lbr_data['pool1'], member_name=lbr_data['member2'])


def test_pools():
    pools = f5.pools

    assert pools
    assert isinstance(pools, list)
    assert pools[0].kind == 'tm:ltm:pool:poolstate'
    assert 'items' in pools[0].membersReference


def test_virtuals():
    virtuals = f5.virtuals

    assert virtuals
    assert isinstance(virtuals, list)
    assert virtuals[0].kind == 'tm:ltm:virtual:virtualstate'


def test_virtual_server_exists(lbr_data):
    assert not f5.virtual_server_exists(name=lbr_data['virtual1'])


def test_create_virtual_server(lbr_data):
    virtual = f5.create_virtual_server(
        name=lbr_data['virtual1'], destination=lbr_data['destination1'], port=lbr_data['port1'], pool=lbr_data['pool1'],
        http_profile_client=lbr_data['http_profile'], ssl_profile_client=lbr_data['cert']
    )
    assert virtual
    assert virtual.kind == 'tm:ltm:virtual:virtualstate'


def test_virtual_profile_exists(lbr_data):
    assert f5.virtual_profile_exists(virtual_name=lbr_data['virtual1'], profile_name=lbr_data['cert'])


def test_get_virtual_servers_by_ip(lbr_data):
    virtuals = f5.get_virtual_servers_by_ip(ip=lbr_data['destination1'])

    assert virtuals
    assert virtuals[0].kind == 'tm:ltm:virtual:virtualstate'
    assert virtuals[0].name == lbr_data['virtual1']


def test_get_virtual_server_ip(lbr_data):
    ip = f5.get_virtual_server_ip(name=lbr_data['virtual1'])

    assert ip == lbr_data['destination1']


def test_get_pool_references(lbr_data):
    used_in_virtuals = f5.get_pool_references(name=lbr_data['pool1'])
    assert used_in_virtuals
    assert lbr_data['virtual1'] in used_in_virtuals


# @pytest.mark.skip
def test_delete_all_pool_members(lbr_data):
    assert not f5.delete_all_pool_members(name=lbr_data['pool1'])


# @pytest.mark.skip
def test_delete_virtual_server(lbr_data):
    f5.delete_virtual_server(name=lbr_data['virtual1'])

    assert not f5.virtual_server_exists(name=lbr_data['virtual1'])


# @pytest.mark.skip
def test_delete_pool(lbr_data):
    f5.delete_pool(name=lbr_data['pool1'])

    assert not f5.pool_exists(name=lbr_data['pool1'])


# @pytest.mark.skip
def test_delete_node_by_address(lbr_data):
    f5.delete_node_by_address(address=lbr_data['address1'])

    assert not f5.node_exists(name=lbr_data['node1'])


# @pytest.mark.skip
def test_delete_node(lbr_data):
    assert not f5.delete_node(name=lbr_data['node1'])
