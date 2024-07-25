import pytest
from api_libs.ads_mini import MockedEnv

from libs.entrypoint import Entrypoint


planned_ip = 'Need to reserve IP'
current_ip = '1.1.1.1'
endpoints = {
    'lem01-t01-pwr01': {
        'interfaces': [('nic0', current_ip), ('api', current_ip), ('intapi', current_ip)],
        'ip': current_ip
    }
}
interfaces_data_01 = [
    {'host_name': 'lem01-t01-pwr01', 'ip': current_ip, 'name': 'api'},
    {'host_name': 'lem01-t01-pwr01', 'ip': 'lem01-t01-pwr01_ip', 'name': 'nic0'},
    {'host_name': 'lem01-t01-pwr01', 'ip': current_ip, 'name': 'intapi'}
]
interfaces_data_02 = [
    {'host_name': 'lem01-t01-pwr02', 'ip': current_ip, 'name': 'api'},
    {'host_name': 'lem01-t01-pwr02', 'ip': 'lem01-t01-pwr02_ip', 'name': 'nic0'},
    {'host_name': 'lem01-t01-pwr02', 'ip': current_ip, 'name': 'intapi'}
]


@pytest.fixture
def ep(mocker):
    mocked_env = MockedEnv()
    mocked_env.prepare()
    mocker.patch('api_libs.ip_tools.nslookup', return_value={"A": [current_ip], "CNAME": []})
    return Entrypoint(name='intapi', env=mocked_env, endpoints=endpoints)


def test_entrypoint_init(ep):
    assert ep.name == 'intapi-testenv'
    assert ep.fqdn == 'intapi-testenv.mydomain'
    assert ep.current_dns == {'A': [current_ip], 'CNAME': []}
    assert ep.planned_dns == {'A': [current_ip], 'CNAME': []}


def test_entrypoint_get_planned_ips(ep):
    assert ep._get_planned_dns() == {'A': [current_ip], 'CNAME': []}


def test_entrypoint_get_current_dns(mocker, ep):
    mocker.patch('api_libs.ip_tools.nslookup', return_value={"A": [current_ip], "CNAME": []})
    assert ep._get_current_dns() == {'A': [current_ip], 'CNAME': []}


def test_plan(ep):
    assert ep.plan == {
        'name': 'intapi-testenv',
        'dns': {
            'fqdn': 'intapi-testenv.mydomain',
            'ips': {'A': [current_ip], 'CNAME': []}
        },
        'inventory': {
            'nodes': ['lem01-t01-pwr01']
        }
    }


def test_state(ep, mocker):
    mocker.patch('api_libs.ip_tools.nslookup', return_value={"A": [current_ip], "CNAME": []})
    mocker.patch('api_libs.inventory.Inventory.get_interfaces', return_value=interfaces_data_01)
    assert ep.state == {
        'name': 'intapi-testenv',
        'dns': {
            'fqdn': 'intapi-testenv.mydomain',
            'ips': {'A': [current_ip], 'CNAME': []}
        },
        'inventory': {
            'nodes': ['lem01-t01-pwr01']
        }
    }


def test_entrypoint_validate_plan(ep, mocker):
    mocker.patch('api_libs.ip_tools.nslookup', return_value={"A": [current_ip], "CNAME": []})
    mocker.patch('api_libs.inventory.Inventory.get_interfaces', side_effect=[interfaces_data_01, interfaces_data_02])
    assert ep.validate_plan()


def test_current_nodes(ep, mocker):
    mocker.patch('api_libs.ip_tools.nslookup', return_value={"A": [current_ip], "CNAME": []})
    mocker.patch('api_libs.inventory.Inventory.get_interfaces', return_value=interfaces_data_01)
    assert ep.current_nodes == ['lem01-t01-pwr01']


def test_delete(ep, mocker):
    mocker.patch('api_libs.dna.DNA.delete_dns_record', return_value=True)
    mocker.patch('api_libs.inventory.Inventory.remove_shared_ip', return_value=True)
    assert ep.delete()


def test_create(ep, mocker):
    mocker.patch('api_libs.dna.DNA.add_dns_record', return_value=True)
    mocker.patch('api_libs.inventory.Inventory.reserve_ip_for_nodes', return_value=True)
    mocker.patch('libs.entrypoint.Entrypoint.update_ads_variables', return_value=True)
    assert ep.create()


def test_reserve_ip(mocker, ep):
    mocker.patch('api_libs.ip_tools.nslookup', return_value={'A': ['1.1.1.1'], 'CNAME': ['cname1.org', 'cname2.org']})
    mocker.patch('api_libs.inventory.Inventory.reserve_ip_for_nodes', return_value='10.62.1.144')
    ip = ep.reserve_ip(['lem01-t01-pwr01'])
    assert ip == '10.62.1.144'


def test_update_ads_variables(mocker, ep):
    status = ep.update_ads_variables()
    assert status

    mocker.patch('api_libs.ads_mini.MockedEnv.does_variable_match', return_value=False)
    status = ep.update_ads_variables()
    assert not status


def test_get_planned_value_for_ads_variable(ep):
    assert ep.get_planned_value_for_ads_variable(name='ENV.PLATFORM.IntApiURL') == 'http://intapi-testenv.mydomain'


def test_get_shared_env_suffix():
    env_name = Entrypoint.get_shared_env_suffix(
        entrypoint="service",
        servers=[{"name": "local_server"}, {"name": "mbs01-t01-scr02"}])
    assert env_name == "mbshrams"
