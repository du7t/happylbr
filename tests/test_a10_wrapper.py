# import pytest
from api_libs.helper import get_ff

import libs.a10_wrapper as a10_wrapper
from conf.static import balancers


a10 = a10_wrapper.A10Manager(
    address=balancers['AMS02']['A10']['address'],
    user=get_ff('BALANCERS')['AMS02']['A10']['user'],
    password=get_ff('BALANCERS')['AMS02']['A10']['password']
)


def test_create_server(lbr_data):
    server = a10.create_server(name=lbr_data['node1'], ip=lbr_data['address1'])

    assert server
    assert isinstance(server, dict)
    assert server['name'] == lbr_data['node1']


# @pytest.mark.skip
def test_servers():
    servers = a10.servers

    assert servers
    assert isinstance(servers, list)
    assert 'name' in servers[0]


# @pytest.mark.skip
def test_virtuals():
    virtuals = a10.virtuals

    assert virtuals
    assert isinstance(virtuals, list)
    assert 'name' in virtuals[0]


# @pytest.mark.skip
def test_groups():
    groups = a10.groups

    assert groups
    assert isinstance(groups, list)
    assert 'name' in groups[0]


def test_get_server(lbr_data):
    server = a10.get_server(name=lbr_data['node1'])

    assert server
    assert isinstance(server, dict)
    assert server['host'] == lbr_data['address1']


# @pytest.mark.skip
def test_get_server_by_ip(lbr_data):
    server = a10.get_server_by_ip(ip=lbr_data['address1'])

    assert server
    assert isinstance(server, dict)
    assert server['name'] == lbr_data['node1']


def test_create_group(lbr_data):
    group = a10.create_group(name=lbr_data['pool1'], members=[{"name": lbr_data['node1'], "port": lbr_data['node1_port1']},
                                                              {"name": lbr_data['node1'], "port": lbr_data['node1_port2']}])

    assert group
    assert isinstance(group, dict)
    assert group['name'] == lbr_data['pool1']


def test_get_group(lbr_data):
    group = a10.get_group(name=lbr_data['pool1'])

    assert group
    assert isinstance(group, dict)
    assert group['name'] == lbr_data['pool1']


# @pytest.mark.skip
def test_create_virtual_server(lbr_data):
    server = a10.create_virtual_server(name=lbr_data['virtual1_a10'], ip=lbr_data['destination1'],
                                       port_list=[{'port-number': lbr_data['port2'], 'service-group': lbr_data['pool1'],
                                                   'protocol': lbr_data['protocol2']}])

    assert server
    assert isinstance(server, dict)
    assert server['name'] == lbr_data['virtual1_a10']


def test_get_virtual_server(lbr_data):
    server = a10.get_virtual_server(name=lbr_data['virtual1_a10'])

    assert server
    assert isinstance(server, dict)
    assert server['ip-address'] == lbr_data['destination1']


def test_get_virtual_server_by_ip(lbr_data):
    server = a10.get_virtual_server_by_ip(ip=lbr_data['destination1'])

    assert server
    assert isinstance(server, dict)
    assert server['name'] == lbr_data['virtual1_a10']


def test_get_virtual_server_ip(lbr_data):
    ip = a10.get_virtual_server_ip(name=lbr_data['virtual1_a10'])

    assert ip == lbr_data['destination1']


def test_create_virtual_port(lbr_data):
    port = a10.create_virtual_port(
        virtual_server=lbr_data['virtual1_a10'], port=lbr_data['port1'], protocol=lbr_data['protocol1'],
        group=lbr_data['pool1'], template_http=lbr_data['http_profile'], client_ssl=lbr_data['cert']
    )
    assert port
    assert isinstance(port, dict)
    assert port['port-number'] == lbr_data['port1']


def test_get_virtual_port(lbr_data):
    port = a10.get_virtual_port(virtual_server=lbr_data['virtual1_a10'], port=lbr_data['port1'],
                                protocol=lbr_data['protocol1'])
    assert port
    assert isinstance(port, dict)
    assert port['protocol'] == lbr_data['protocol1']


def test_get_server_references(lbr_data):
    used_in_groups = a10.get_server_references(name=lbr_data['node1'])
    assert used_in_groups
    assert lbr_data['pool1'] in used_in_groups


def test_get_group_references(lbr_data):
    used_in_virtuals = a10.get_group_references(name=lbr_data['pool1'])
    assert used_in_virtuals
    assert lbr_data['virtual1_a10'] in used_in_virtuals


# @pytest.mark.skip
def test_delete_virtual_port(lbr_data):
    response = a10.delete_virtual_port(virtual_server=lbr_data['virtual1_a10'], port=lbr_data['port2'],
                                       protocol=lbr_data['protocol2'])

    assert response['status'] == 'OK'


# @pytest.mark.skip
def test_delete_virtual_server(lbr_data):
    response = a10.delete_virtual_server(name=lbr_data['virtual1_a10'])

    assert response['status'] == 'OK'


# @pytest.mark.skip
def test_delete_group(lbr_data):
    response = a10.delete_group(name=lbr_data['pool1'])

    assert response['status'] == 'OK'


# @pytest.mark.skip
def test_delete_server(lbr_data):
    response = a10.delete_server(name=lbr_data['node1'])

    assert response['status'] == 'OK'
