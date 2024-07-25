import pytest

from libs.node import NodeF5


class MockedF5Node:
    def __init__(self, name: str, address: str) -> None:
        self.name = name
        self.address = f'{address}%2'

    @property
    def attrs(self):
        return {
            'name': self.name,
            'address': self.address
        }


host = 'lem01-t01-pwr08'
current_ip = '1.1.1.1'
endpoints_f5 = {
    host: {
        'interfaces': [('nic0', current_ip), ('api', current_ip), ('intapi', current_ip)],
        'ip': current_ip
    }
}


@pytest.fixture
def node(mocker):
    mocker.patch('libs.f5_wrapper.F5Manager.get_node', return_value=MockedF5Node(name=host, address=current_ip))
    return NodeF5(name=host, ip="192.168.253.2", location='ams02')


def test_state(node):
    assert node.state == {'name': host, 'ip': current_ip}


def test_plan(node):
    assert node.plan == {'name': host, 'ip': '192.168.253.2'}
