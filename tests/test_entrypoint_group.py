import pytest
from api_libs.ads_mini import MockedEnv

from libs.entrypoint_group import EntrypointGroup


entrypoints = ['api', 'intapi']
planned_ip = 'Need to reserve IP'
planned_config = {
    'name': 'pwr',
    'interfaces': ['lem01-t01-pwr01:api', 'lem01-t01-pwr01:intapi', 'lem01-t01-pwr02:api', 'lem01-t01-pwr02:intapi']
}
current_ip = '1.1.1.1'
planned_global_config = {
    'pwr': {
        'api': {
            'fqdn': 'api-testenv.mydomain',
            'ips': {'A': [current_ip], 'CNAME': []},
            'name': 'api-testenv',
            'nodes': ['lem01-t01-pwr01']
        },
        'intapi': {
            'fqdn': 'intapi-testenv.mydomain',
            'ips': {'A': [current_ip], 'CNAME': []},
            'name': 'intapi-testenv',
            'nodes': ['lem01-t01-pwr01']
        }
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
current_state = {
    'name': 'pwr',
    'interfaces': ['lem01-t01-pwr01:api', 'lem01-t01-pwr01:intapi', 'lem01-t01-pwr02:api', 'lem01-t01-pwr02:intapi']
}
endpoints = {
    'lem01-t01-pwr01': {
        'interfaces': [('api', current_ip), ('intapi', current_ip), ('nic0', 'lem01-t01-pwr01_ip')],
        'ip': 'lem01-t01-pwr01_ip'
    },
    'lem01-t01-pwr02': {
        'interfaces': [('api', current_ip), ('intapi', current_ip), ('nic0', 'lem01-t01-pwr02_ip')],
        'ip': 'lem01-t01-pwr02_ip'
    }
}


@pytest.fixture
def eg(mocker):
    mocked_env = MockedEnv()
    mocked_env.prepare()
    mocker.patch('api_libs.ads_mini.Env', return_value=mocked_env)
    mocker.patch('libs.entrypoint_manager.EntrypointManager.get_entrypoints', return_value=entrypoints)
    hosts = ['lem01-t01-pwr01.mydomain', 'lem01-t01-pwr02.mydomain']
    mocker.patch('api_libs.ads_mini.MockedEnv.get_hosts_by_service', return_value=hosts)
    return EntrypointGroup(service_name='PWR', env_name='test_env', env=mocked_env, entrypoints=entrypoints)


def test_init(eg):
    assert isinstance(eg, EntrypointGroup)
    assert eg.name == 'pwr'
    assert eg.entrypoints == entrypoints


def test_get_endpoints_from_ads(eg, mocker):
    mocker.patch('api_libs.ip_tools.nslookup', return_value={"A": [current_ip], "CNAME": []})
    assert eg.get_endpoints_from_ads() == [
        {'ip': current_ip, 'name': 'lem01-t01-pwr01'},
        {'ip': current_ip, 'name': 'lem01-t01-pwr02'}
    ]


def test_endpoints(eg, mocker):
    dns = [{"A": ['lem01-t01-pwr01_ip'], "CNAME": []}, {"A": ['lem01-t01-pwr02_ip'], "CNAME": []}]
    mocker.patch('api_libs.ip_tools.nslookup', side_effect=dns)
    mocker.patch('api_libs.inventory.Inventory.get_interfaces', side_effect=[interfaces_data_01, interfaces_data_02])
    assert eg.endpoints == endpoints


def test_plan(eg, mocker):
    dns = [{"A": ['lem01-t01-pwr01_ip'], "CNAME": []}, {"A": ['lem01-t01-pwr02_ip'], "CNAME": []}]
    mocker.patch('api_libs.ip_tools.nslookup', side_effect=dns)
    mocker.patch('api_libs.inventory.Inventory.get_interfaces', side_effect=[interfaces_data_01, interfaces_data_02])
    assert eg.plan == planned_config


def test_state(eg, mocker):
    dns = [{"A": ['lem01-t01-pwr01_ip'], "CNAME": []}, {"A": ['lem01-t01-pwr02_ip'], "CNAME": []}]
    mocker.patch('api_libs.ip_tools.nslookup', side_effect=dns)
    mocker.patch('api_libs.inventory.Inventory.get_interfaces', side_effect=[interfaces_data_01, interfaces_data_02])
    assert eg.state == current_state


def test_diff(eg, mocker):
    mocker.patch('api_libs.ip_tools.nslookup', return_value={"A": [current_ip], "CNAME": []})
    mocker.patch('api_libs.inventory.Inventory.get_interfaces', return_value=interfaces_data_01)
    assert eg.diff == {}


def test_validate_state(eg, mocker):
    invalid_interfaces_data = [
        {'host_name': 'lem01-t01-pwr01', 'ip': current_ip, 'name': 'nic0'},
        {'host_name': 'lem01-t01-pwr01', 'ip': current_ip, 'name': 'api'},
        {'host_name': 'lem01-t01-pwr01', 'ip': current_ip, 'name': 'garbage'}
    ]
    mocker.patch('api_libs.inventory.Inventory.get_interfaces', return_value=invalid_interfaces_data)
    assert not eg.validate_state()


def test_get_resolvable_servers(mocker):
    mocker.patch('api_libs.ip_tools.nslookup', return_value={"A": [], "CNAME": []})
    servers = EntrypointGroup.get_resolvable_servers(['some_unresolvable_server'])
    assert servers == []


def test_get_nodes(mocker):
    mocker.patch('api_libs.ip_tools.nslookup', return_value={'A': [current_ip], 'CNAME': ['cname1.org', 'cname2.org']})
    hostnames = EntrypointGroup.get_resolvable_servers(['lem01-t01-pwr01.mydomain'])
    assert hostnames == [{'name': 'lem01-t01-pwr01', 'ip': current_ip}]
