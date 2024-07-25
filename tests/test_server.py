import pytest

from libs.server import ServerA10


current_ip = '1.1.1.1'
endpoints_a10 = {
    'lem01-t01-pwr09': {
        'interfaces': [('nic0', current_ip), ('api', current_ip), ('intapi', current_ip)],
        'ip': current_ip
    }
}

a10_server = {
    'name': 'lem01-t01-pwr09',
    'host': current_ip,
    'action': 'enable'
}


@pytest.fixture
def server(mocker):
    mocker.patch('libs.a10_wrapper.A10Manager.get_server', return_value=a10_server)
    return ServerA10(name='lem01-t01-pwr09', ip="192.168.253.1", location='ams02')


def test_state(server):
    assert server.state == {'name': a10_server['name'], 'ip': a10_server['host']}


def test_plan(server):
    assert server.plan == {'name': 'lem01-t01-pwr09', 'ip': '192.168.253.1'}
