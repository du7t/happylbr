import fire
import pytest
from api_libs.ads_mini import MockedEnv

from happyvip import CLI
from libs.entrypoint_manager import EntrypointManager
from libs.lbr_wrapper import MockedLBR


@pytest.fixture
def cli():
    cli = CLI()
    return cli


@pytest.fixture
def em(mocker):
    mocked_env = MockedEnv()
    mocked_lbr = MockedLBR()
    mocker.patch('api_libs.ads_mini.Env', return_value=mocked_env)
    mocker.patch('libs.lbr_wrapper.LBR', return_value=mocked_lbr)
    mocker.patch('api_libs.inventory.Inventory.get_interfaces', return_value=[])
    mocker.patch('libs.lbr_wrapper.LBR.get_vip_address', return_value=None)
    mocker.patch('api_libs.ip_tools.nslookup', return_value={'A': ['1.1.1.1'], 'CNAME': ['cname1.org', 'cname2.org']})
    mocker.patch('libs.entrypoint.Entrypoint.global_patch', return_value={'Entrypoint': {'patched': True}})
    mocker.patch('libs.entrypoint.Entrypoint.global_delete', return_value={'Entrypoint': {'deleted': True}})
    test_em = EntrypointManager(env_name='test_env')
    test_em.entrypoint = 'intapi'
    return test_em


def test_fire_help(capfd):
    try:
        fire.Fire(component=cli, command=['-h'], name='happyvip.py')
    except fire.core.FireExit:
        pass
    out, err = capfd.readouterr()
    assert out == ''
    assert 'Showing help' in err


def test_cli_empty_env_name(cli):
    with pytest.raises(Exception, match='Incorrect env name given'):
        cli.create(name='')


def test_cli_wrong_env_name(cli):
    with pytest.raises(Exception, match='Incorrect env name given'):
        cli.create(name='wrong_env_name')


def test_cli_without_entrypoints(cli):
    pass
    # TODO implement
    # cli.create(name='test_env', entrypoints='', services='', groups='')


def test_cli_with_missing_services(mocker, cli, em):
    mocker.patch('libs.entrypoint_manager.EntrypointManager.get_entrypoints', return_value=['intapi'])
    mocker.patch('libs.entrypoint_manager.EntrypointManager', return_value=em)
    mocker.patch('libs.entrypoint_group.EntrypointGroup.get_endpoints_from_ads', return_value=[])
    with pytest.raises(Exception, match='No hosts'):
        cli.create(name='test_env', entrypoints='intapi')


def test_cli_create(mocker, em, cli):
    mocker.patch('libs.entrypoint_manager.EntrypointManager.get_entrypoints', return_value=['intapi'])
    mocker.patch('libs.entrypoint_manager.EntrypointManager', return_value=em)
    mocker.patch('libs.entrypoint_group.EntrypointGroup.validate_state', return_value=True)
    mocker.patch('libs.entrypoint_group.EntrypointGroup.endpoints', return_value=['lem01-t01-pwr01.mydomain'])
    status = cli.create(name='test_env', all=True)
    assert cli.env_name == 'test_env'
    assert cli.entrypoints == ['intapi']
    assert status == {'intapi': True}


def test_cli_create_uppercase_entrypoint(mocker, em, cli):
    mocker.patch('libs.entrypoint_manager.EntrypointManager', return_value=em)
    mocker.patch('libs.entrypoint_group.EntrypointGroup.endpoints', return_value=['lem01-t01-pwr01.mydomain'])
    cli.create(name='test_env', entrypoints='INTAPI')
    assert cli.entrypoints == ['intapi']


def test_cli_delete(mocker, em, cli):
    mocker.patch('libs.entrypoint_manager.EntrypointManager.get_entrypoints', return_value=['intapi'])
    mocker.patch('libs.entrypoint_manager.EntrypointManager', return_value=em)
    mocker.patch('libs.entrypoint_group.EntrypointGroup.validate_state', return_value=True)
    status = cli.delete(name='test_env', entrypoints='intapi')
    assert cli.env_name == 'test_env'
    assert cli.entrypoints == ['intapi']
    assert status == {'intapi': True}


def test_cli_delete_all(mocker, em, cli):
    mocker.patch('libs.entrypoint_manager.EntrypointManager', return_value=em)
    mocker.patch('libs.entrypoint_group.EntrypointGroup.validate_state', return_value=True)
    cli.delete(name='test_env', all=True)
    assert {'api', 'scp'}.issubset(cli.entrypoints)


def test_cli_delete_empty_env_name(cli):
    with pytest.raises(Exception, match='Incorrect env name given'):
        cli.delete(name='')


def test_cli_delete_without_entrypoints(cli, mocker, em):
    mocker.patch('libs.entrypoint_manager.EntrypointManager', return_value=em)
    mocker.patch('libs.entrypoint_group.EntrypointGroup.validate_state', return_value=True)
    with pytest.raises(Exception, match='No entrypoints provided'):
        cli.delete(name='test_env', entrypoints='', services='')
