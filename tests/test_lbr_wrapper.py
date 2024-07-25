import libs.lbr_wrapper as lbr_wrapper


lbr = lbr_wrapper.LBR(location="AMS02")


entrypoint = "pas"
entrypoint_f5 = "pas2"
ip = "10.62.10.125"
nodes = [{"name": "lem01-t01-pas03", "ip": "10.61.16.27"},
         {"name": "lem01-t01-pas01", "ip": "10.61.144.156"}]
env_suffix = "lablemams"
env_domain = "mydomain"


def test_get_lbr_type():
    assert lbr.get_lbr_type(entrypoint="pas2") == "F5"
    assert lbr.get_lbr_type(entrypoint="pas") == "A10"


def test_get_healthcheck_by_entrypoint():
    assert lbr.get_healthcheck_by_entrypoint('intapi') == "http_pwr"
    assert lbr.get_healthcheck_by_entrypoint('yp') == "tcp"


def test_create_vip_a10():
    assert lbr.create_vip(entrypoint=entrypoint, ip=ip, nodes=nodes, env_suffix=env_suffix, env_domain=env_domain)


def test_get_vip_a10():
    vips = lbr.get_vip(entrypoint, env_suffix)
    assert vips
    assert vips[0]['name'] == f'{entrypoint}-{env_suffix}'
    assert vips[0]['address'] == ip
    assert len(vips[0]['ports']) == 2
    assert "lem01-t01-pas" in vips[0]['ports'][0]['pool']['name']


def test_delete_vip_a10():
    assert lbr.delete_vip(entrypoint=entrypoint, env_suffix=env_suffix)


def test_create_vip_f5():
    assert lbr.create_vip(entrypoint=entrypoint_f5, ip=ip, nodes=nodes, env_suffix=env_suffix, env_domain=env_domain)


def test_get_vip_f5():
    vips = lbr.get_vip(entrypoint_f5, env_suffix)
    assert vips
    assert vips[0]['address'] == ip
    assert len(vips[0]['ports']) == 1
    assert "lem01-t01-pas" in vips[0]['ports'][0]['pool']['name']


def test_delete_vip_f5():
    assert lbr.delete_vip(entrypoint=entrypoint_f5, env_suffix=env_suffix)
