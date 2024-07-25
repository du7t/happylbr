import pytest

from libs.virtual_port import VirtualPortA10


port_config = {
    "port": 777,
    "target_port": 8082,
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

a10_vp = {
    'port-number': 443,
    'protocol': 'https',
    'service-group': 'lem01-t01-pwr_9000',
    'template-http': 'rc-xffxfp-https',
    'template-client-ssl': 'star.mydomain',
    'name': 'intapi-lablemams:443@lem01-t01-pwr_9000'
}


@pytest.fixture
def vp(mocker):
    mocker.patch('libs.a10_wrapper.A10Manager.get_virtual_port', return_value=a10_vp)
    return VirtualPortA10(virtual_server_name='intapi-lablemams', port_config=port_config,
                          location='ams02', endpoints=endpoints_a10, sg_health="http_pwr", client_ssl="star.domain")


def test_state(vp):
    assert vp.state == {'port-number': 443, 'protocol': 'https', 'service-group': 'lem01-t01-pwr_9000',
                        'client-ssl': 'star.mydomain', 'template-http': 'rc-xffxfp-https'}


def test_plan(vp):
    assert vp.plan == {'port-number': 777, 'protocol': 'https', 'service-group': 'lem01-t01-pwr_8082',
                       'client-ssl': 'star.domain', 'template-http': 'rc-xffxfp-https'}
