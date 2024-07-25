import pytest
from api_libs.logger import log
from api_libs.logger import Logger

from libs.a10_wrapper import A10Manager
from libs.f5_wrapper import F5Manager
from libs.virtual_server import VirtualServerA10
from libs.virtual_server import VirtualServerF5


logger = Logger()


current_ip = '1.1.1.1'
endpoints_a10 = {
    'lem01-t01-pwr01': {
        'interfaces': [('nic0', current_ip), ('api', current_ip), ('testapi', current_ip)],
        'ip': current_ip
    }
}
a10_all_vs = [
    {
        "name": "testapi-lablemams",
        "ip-address": "10.62.5.127",
        "uuid": "df712658-8902-11ee-a619-001fa01560bc",
        "port-list": [
            {
                "port-number": 80,
                "protocol": "http",
                "uuid": "e035b63a-8902-11ee-a619-001fa01560bc",
                "a10-url": "/axapi/v3/slb/virtual-server/testapi-lablemams/port/80+http"
            },
            {
                "port-number": 443,
                "protocol": "https",
                "uuid": "dfd40ec6-8902-11ee-a619-001fa01560bc",
                "a10-url": "/axapi/v3/slb/virtual-server/testapi-lablemams/port/443+https"
            }
        ],
        "a10-url": "/axapi/v3/slb/virtual-server/testapi-lablemams"
    },
    {
        "name": "garbage-lablemams",
        "ip-address": "10.62.5.127",
        "uuid": "be9101ec-8902-11ee-a619-001fa01560bc",
        "port-list": [
            {
                "port-number": 80,
                "protocol": "http",
                "uuid": "bec450b0-8902-11ee-a619-001fa01560bc",
                "a10-url": "/axapi/v3/slb/virtual-server/extapi-lablemams/port/80+http"
            }
        ],
        "a10-url": "/axapi/v3/slb/virtual-server/extapi-lablemams"
    }
]


@pytest.fixture
def vs_a10(mocker):
    mocker.patch('libs.a10_wrapper.A10Manager.get_virtual_server', return_value=a10_all_vs[0])
    return VirtualServerA10(name='testapi-lablemams', entrypoint='intapi',
                            ip='192.168.253.2', location='ams02', endpoints=endpoints_a10)


endpoints_f5 = {
    'lem01-t01-rap01': {
        'interfaces': [('nic0', current_ip), ('api', current_ip), ('testapi', current_ip)],
        'ip': current_ip
    }
}


@pytest.fixture
def vs_f5(mocker):
    v1 = {'name': 'cp-lablemams_443', 'destination': '/ams-up/10.62.6.194%2:443', 'pool': '/ams-up/lem01-t01-rap_11443',
          'profilesReference': {'items': [{'name': "xfp"}, {'name': "tcp"}]}}
    mocker.patch('libs.virtual_server.VirtualServerF5._get_f5_vs_dict', return_value=v1)
    return VirtualServerF5(name='cp-lablemams_443', entrypoint='cp', ip='10.62.6.194',
                           location='ams02', endpoints=endpoints_f5, port=443)


@log(logger)
def test_a10_lbr_type(vs_a10):
    assert isinstance(vs_a10.lbr, A10Manager)


def test_a10_virtual_server(vs_a10):
    assert vs_a10.virtual_server == {'name': 'testapi-lablemams', 'ip': '10.62.5.127', 'ports': [80, 443]}


def test_a10_plan(vs_a10):
    assert vs_a10.plan == {'ip': '192.168.253.2', 'name': 'testapi-lablemams', 'ports': [80, 443]}


def test_a10_state(vs_a10):
    assert vs_a10.state == {'ip': '10.62.5.127', 'name': 'testapi-lablemams', 'ports': [80, 443]}


def test_a10_validate_plan(vs_a10):
    assert vs_a10.validate_plan()


@log(logger)
def test_f5_lbr_type(vs_f5):
    assert isinstance(vs_f5.lbr, F5Manager)


def test_f5_virtual_server(vs_f5):
    assert vs_f5.virtual_server == {'name': 'cp-lablemams_443', 'destination': '10.62.6.194',
                                    'partition': 'ams-up', 'pool': 'lem01-t01-rap_11443', 'port': '443', 'profiles': {'xfp'}}


def test_f5_plan(vs_f5):
    assert vs_f5.plan == {'name': 'cp-lablemams_443', 'destination': '10.62.6.194',
                          'partition': 'ams-up', 'pool': 'lem01-t01-rap_11443', 'port': '443', 'profiles': set()}


def test_f5_state(vs_f5):
    assert vs_f5.state == {'name': 'cp-lablemams_443', 'destination': '10.62.6.194',
                           'partition': 'ams-up', 'pool': 'lem01-t01-rap_11443', 'port': '443', 'profiles': {'xfp'}}


def test_f5_validate_state(vs_f5):
    assert vs_f5.validate_state()
