import pytest

from libs.pool import PoolF5


class MockedF5Pool:
    def __init__(self, name: str, monitor: str, members: list[str]) -> None:
        self.name = name
        self.monitor = f'/Common/{monitor}'
        self.members = members

    @property
    def attrs(self):
        return {
            'name': self.name,
            'monitor': self.monitor,
            'membersReference': {'items': [{'name': name for name in self.members}]}
        }


port_config = {
    "port": 443,
    "target_port": 11443,
    "protocol": "https",
    "template_http": "rc-xffxfp-https"
}

current_ip = '1.1.1.2'
endpoints_f5 = {
    'lem01-t01-rap01': {
        'interfaces': [('nic0', current_ip), ('admin', current_ip)],
        'ip': current_ip
    },
    'lem01-t01-rap02': {
        'interfaces': [('nic0', current_ip), ('admin', current_ip)],
        'ip': current_ip
    }
}


@pytest.fixture
def pool(mocker):
    mocker.patch('libs.f5_wrapper.F5Manager.get_pool', return_value=MockedF5Pool(
        name='lem01-t01-rap_11443',
        monitor='tcp',
        members=['lem01-t01-rap01:11443']
    ))
    return PoolF5(name='lem01-t01-rap_11443', location='ams02', endpoints=endpoints_f5,
                  monitor='tcp', port_config=port_config)


def test_state(pool):
    assert pool.state == {'name': 'lem01-t01-rap_11443', 'monitor': 'tcp',
                          'members': ['lem01-t01-rap01:11443']}


def test_plan(pool):
    assert pool.plan == {'name': 'lem01-t01-rap_11443', 'monitor': 'tcp',
                         'members': ['lem01-t01-rap01:11443', 'lem01-t01-rap02:11443']}
