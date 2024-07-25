import pytest
from api_libs.ads_mini import MockedEnv

from libs.entrypoint_manager import EntrypointManager
from libs.lbr_wrapper import MockedLBR


entrypoint = 'intapi'
success = {
    entrypoint: {
        'success': True,
        'ads_variables': True,
        'dns_records': True,
        'ip': True,
        'lbr_vip': True,
        'comment': []
    }
}


@pytest.fixture
def em(mocker):
    mocked_env = MockedEnv()
    mocked_lbr = MockedLBR()
    mocker.patch('api_libs.ads_mini.Env', return_value=mocked_env)
    mocker.patch('libs.lbr_wrapper.LBR', return_value=mocked_lbr)
    mocker.patch('api_libs.ip_tools.nslookup', return_value={'A': ['1.1.1.1'], 'CNAME': ['cname1.org', 'cname2.org']})
    test_em = EntrypointManager(env_name='test_env')
    test_em.entrypoint = entrypoint
    return test_em


def test_create_entrypoint(mocker, em):
    mocker.patch('libs.entrypoint.Entrypoint.global_patch', return_value=None)
    em.create_entrypoint(entrypoint=entrypoint)
    assert len(em.eg_store) == 1


def test_delete_entrypoint(mocker, em):
    mocker.patch('libs.entrypoint.Entrypoint.global_delete', return_value=None)
    em.delete_entrypoint(entrypoint=entrypoint)
    assert len(em.eg_store) == 1


def test_get_entrypoints():
    vips = EntrypointManager.get_entrypoints()
    assert vips == []

    entrypoints = ['intapi', 'extapi']
    vips = EntrypointManager.get_entrypoints(entrypoints=entrypoints)
    assert vips == entrypoints

    services = ['pwr']
    vips = EntrypointManager.get_entrypoints(entrypoints=entrypoints, services=services)
    assert vips == entrypoints

    vips = EntrypointManager.get_entrypoints(services=services)
    assert 'intapi' in vips

    vips = EntrypointManager.get_entrypoints(mandatory=True)
    assert {'intapi', 'api', 'service'}.issubset(vips)
