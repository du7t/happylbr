import pytest

from libs.service_group import ServiceGroupA10


port_config = {
    "port": 443,
    "target_port": 7000,
    "protocol": "https",
    "template_http": "rc-xffxfp-https"
}

current_ip = '1.1.1.1'
endpoints_a10 = {
    'lem01-t01-pwr01': {
        'interfaces': [('nic0', current_ip), ('api', current_ip), ('intapi', current_ip)],
        'ip': current_ip
    }
}

a10_sg = {
    'name': 'lem01-t01-pwr_9000',
    'health-check': 'http_pwr',
    'protocol': 'tcp',
    'member-list': [{'name': 'lem01-t01-pwr01', 'port': 9000, 'member-state': 'enable'}]
}


@pytest.fixture
def sg(mocker):
    mocker.patch('libs.a10_wrapper.A10Manager.get_group', return_value=a10_sg)
    return ServiceGroupA10(name='lem01-t01-pwr_7000', port_config=port_config,
                           location='ams02', endpoints=endpoints_a10, healthcheck="http_pwr")


def test_state(sg):
    assert sg.state == {'name': 'lem01-t01-pwr_9000', 'health-check': 'http_pwr',
                        'member-list': [{'name': 'lem01-t01-pwr01', 'port': 9000}]}


def test_plan(sg):
    assert sg.plan == {'name': 'lem01-t01-pwr_7000', 'health-check': 'http_pwr',
                       'member-list': [{'name': 'lem01-t01-pwr01', 'port': 7000}]}
