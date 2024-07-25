from acos_client.errors import AddressSpecifiedIsInUse as A10AddressSpecifiedIsInUse
from acos_client.errors import Exists as A10Exists
from api_libs.helper import get_ff
from api_libs.logger import log
from api_libs.logger import Logger

import libs.a10_wrapper as a10_wrapper
import libs.f5_wrapper as f5_wrapper
from conf.static import balancers
from conf.static import entrypoints
from conf.static import healthchecks
from libs.f5_wrapper import AddressSpecifiedIsInUse as F5AddressSpecifiedIsInUse
from libs.f5_wrapper import Exists as F5Exists


logger = Logger()


class LBR:
    def __init__(self, location: str) -> None:
        self.location = location
        self._a10 = None
        self._f5 = None
        self.healthchecks = healthchecks
        self.entrypoints = entrypoints

    @property
    def a10(self):
        if not self._a10:
            self._a10 = a10_wrapper.A10Manager(
                address=balancers[self.location]["A10"]["address"],
                user=get_ff("BALANCERS")[self.location]["A10"]["user"],
                password=get_ff("BALANCERS")[self.location]["A10"]["password"],
            )
        return self._a10

    @property
    def f5(self):
        if not self._f5:
            self._f5 = f5_wrapper.F5Manager(
                address=balancers[self.location]["F5"]["address"],
                user=get_ff("BALANCERS")[self.location]["F5"]["user"],
                password=get_ff("BALANCERS")[self.location]["F5"]["password"],
                partition=balancers[self.location]["F5"]["partition"],
            )
        return self._f5

    @log(logger)
    def get_vip(self, entrypoint: str, env_suffix: str) -> list:
        lbr_type = self.get_lbr_type(entrypoint)
        vips = []
        if lbr_type == "A10":
            vip_name = self.get_vip_name(lbr_type, entrypoint, env_suffix, {})
            virtual = self.a10.get_virtual_server(name=vip_name)
            if not virtual:
                return vips
            vip = {"name": vip_name, "address": virtual.get("ip-address"), "ports": []}
            for p in virtual.get("port-list", []):
                port_number = p.get("port-number")
                pool = p.get("service-group")
                port = {
                    "port_number": port_number,
                    "pool": {"name": pool} if pool else None,
                }
                if pool:
                    members = self.a10.get_group(name=pool).get("member-list", [])
                    port["pool"]["members"] = [
                        {
                            "name": m["name"],
                            "address": self.a10.get_server(name=m["name"])["host"],
                            "port": m["port"],
                        }
                        for m in members
                    ]
                vip["ports"].append(port)
            vips.append(vip)
        elif lbr_type == "F5":
            ports = self.get_ports_config(entrypoint)
            for p in ports:
                vip_name = self.get_vip_name(lbr_type, entrypoint, env_suffix, p)
                virtual = self.f5.get_virtual_server(name=vip_name)
                if not virtual:
                    continue
                destination = virtual.attrs.get("destination")
                port_number = int(destination.rsplit(":", 1)[-1])
                pool = self.f5.clean_value(virtual.attrs.get("pool"))
                vip = {
                    "name": vip_name,
                    "address": self.f5.clean_value(destination),
                    "ports": [
                        {
                            "port_number": port_number,
                            "pool": {"name": pool} if pool else None,
                        }
                    ],
                }
                if pool:
                    vip["ports"][0]["pool"]["members"] = self.f5.get_pool_members(
                        name=pool
                    )
                vips.append(vip)
        return vips

    @log(logger)
    def create_vip(
        self,
        entrypoint: str,
        ip: str,
        nodes: list[dict],
        env_suffix: str,
        env_domain: str,
    ) -> bool:
        lbr_type = self.get_lbr_type(entrypoint=entrypoint)
        self.create_nodes(lbr_type, nodes)
        # exit()
        ports = self.get_ports_config(entrypoint)
        processed_pools = []
        for port in ports:
            pool_name, target_port = self.get_pool_name_with_port(nodes, port)
            if pool_name not in processed_pools:
                self.create_pool_with_members(lbr_type, pool_name, nodes, target_port)
                processed_pools.append(pool_name)
            vip_name = self.get_vip_name(lbr_type, entrypoint, env_suffix, port)
            self.create_virtual(lbr_type, vip_name, ip, port, pool_name, env_domain)
        return True

    @log(logger)
    def delete_vip(self, entrypoint: str, env_suffix: str) -> bool:
        lbr_type = self.get_lbr_type(entrypoint=entrypoint)
        ports = self.get_ports_config(entrypoint)
        pools = self.get_virtual_server_pools(lbr_type, entrypoint, ports, env_suffix)
        nodes = self.get_pool_members_names(lbr_type, pools[0]) if pools else []
        for port in ports:
            vip_name = self.get_vip_name(lbr_type, entrypoint, env_suffix, port)
            self.delete_virtual(lbr_type, vip_name)
        deleted_pools = []
        for pool in pools:
            if self.delete_pool(lbr_type, pool):
                deleted_pools.append(pool)
        # no need to delete nodes if no pools were deleted
        if deleted_pools:
            self.delete_nodes(lbr_type, nodes)
        return True

    @log(logger)
    def get_vip_address(self, entrypoint: str, env_suffix: str) -> str:
        lbr_type = self.get_lbr_type(entrypoint=entrypoint)
        ports = self.get_ports_config(entrypoint)
        vip_name = self.get_vip_name(lbr_type, entrypoint, env_suffix, ports[0])
        if lbr_type == "A10":
            ip = self.a10.get_virtual_server_ip(name=vip_name)
        elif lbr_type == "F5":
            ip = self.f5.get_virtual_server_ip(name=vip_name)
        return ip

    @log(logger)
    def get_pool_members_names(self, lbr_type: str, name: str) -> list:
        if lbr_type == "A10":
            return self.a10.get_group_members_names(name=name)
        elif lbr_type == "F5":
            return self.f5.get_pool_members_names(name=name)

    @log(logger)
    def get_virtual_server_pools(
        self, lbr_type: str, entrypoint: str, ports: list, env_suffix: str
    ) -> list:
        if lbr_type == "A10":
            vip_name = self.get_vip_name(lbr_type, entrypoint, env_suffix, {})
            return self.a10.get_virtual_server_groups(name=vip_name)
        elif lbr_type == "F5":
            pools = set()
            for port in ports:
                vip_name = self.get_vip_name(lbr_type, entrypoint, env_suffix, port)
                if pool := self.f5.get_virtual_server_pool(name=vip_name):
                    pools.add(pool)
            return list(pools)

    def get_lbr_type(self, entrypoint: str) -> str:
        return entrypoints[entrypoint]["LB"].upper()

    @log(logger)
    def create_nodes(self, lbr_type: str, nodes: list[dict]):
        for node in nodes:
            self.create_node(lbr_type=lbr_type, node=node)

    @log(logger)
    def create_node(self, lbr_type: str, node: dict):
        created = False
        if lbr_type == "A10":
            try:
                created = self.a10.create_server(name=node["name"], ip=node["ip"])
            except A10Exists as e:
                logger.log.warning(f"{lbr_type}.node.create - {node}: {e}")
                ip = self.a10.get_server_ip(name=node["name"])
                logger.log.info(f"{lbr_type}.node.create - {node}: name already exists with ip: {ip}")
                if ip != node["ip"]:
                    if self.delete_node(lbr_type=lbr_type, node=node["name"]):
                        self.create_node(lbr_type=lbr_type, node=node)
                else:
                    created = True
            except A10AddressSpecifiedIsInUse as e:
                logger.log.warning(f"{lbr_type}.node.create - {node}: {e}")
                if conflict_node := self.a10.get_server_by_ip(ip=node["ip"]).get("name"):
                    logger.log.info(f"{lbr_type}.node.create - {node}: ip already exists with node: {conflict_node}")
                    if self.delete_node(lbr_type=lbr_type, node=conflict_node):
                        self.create_node(lbr_type=lbr_type, node=node)
        elif lbr_type == "F5":
            try:
                created = self.f5.create_node(name=node["name"], address=node["ip"])
            except F5Exists as e:
                logger.log.warning(f"{lbr_type}.node.create - {node}: {e}")
                ip = self.f5.get_node_address(name=node["name"])
                logger.log.info(f"{lbr_type}.node.create - {node}: name already exists with ip: {ip}")
                if ip != node["ip"]:
                    if self.delete_node(lbr_type=lbr_type, node=node["name"]):
                        self.create_node(lbr_type=lbr_type, node=node)
                else:
                    created = True
            except F5AddressSpecifiedIsInUse as e:
                logger.log.warning(f"{lbr_type}.node.create - {node}: {e}")
                if conflict_node := self.f5.get_node_by_address(address=node["ip"]).attrs.get("name"):
                    logger.log.info(f"{lbr_type}.node.create - {node}: ip already exists with node: {conflict_node}")
                    if self.delete_node(lbr_type=lbr_type, node=conflict_node):
                        self.create_node(lbr_type=lbr_type, node=node)
        return created

    @log(logger)
    def get_vip_name(
        self, lbr_type: str, entrypoint: str, env_suffix: str, port: dict
    ) -> str:
        if lbr_type == "A10":
            return f"{entrypoint}-{env_suffix}"
        elif lbr_type == "F5":
            return f"{entrypoint}-{env_suffix}_{port['port']}"

    def get_ports_config(self, entrypoint: str) -> list[dict]:
        return entrypoints[entrypoint]["ports"]

    def get_port_config(self, entrypoint: str, port: int) -> dict:
        for port_config in entrypoints[entrypoint]["ports"]:
            if port_config['port'] == port:
                return port_config

    def get_healthcheck_by_entrypoint(self, entrypoint: str):
        lb: str = self.entrypoints[entrypoint]['LB']
        service: str = self.entrypoints[entrypoint]['service']
        return self.healthchecks[lb].get(service) or self.healthchecks[lb]['default']

    @log(logger)
    def get_pool_name_with_port(self, nodes: list, port: dict) -> tuple:
        target_port = port["target_port"]
        pool_name = f"{nodes[0]['name'][:-2]}_{target_port}"
        return pool_name, target_port

    @log(logger)
    def get_pool_name(self, nodes: list, ports: list, port: int) -> str:
        for port_config in ports:
            if port_config['port'] == port:
                return f"{nodes[0]['name'][:-2]}_{port_config['target_port']}"

    @log(logger)
    def create_pool_with_members(
        self, lbr_type: str, pool_name: str, nodes: list, target_port: int
    ):
        try:
            if lbr_type == "A10":
                members = [
                    {"name": node["name"], "port": target_port} for node in nodes
                ]
                created = self.a10.create_group(name=pool_name, members=members)
            elif lbr_type == "F5":
                members = [f"{node['name']}:{target_port}" for node in nodes]
                created = self.f5.create_pool(name=pool_name, members=members)
            return created
        except (A10Exists, F5Exists) as e:
            logger.log.warning(f"{lbr_type}.pool.create - {pool_name}: {e}")

    @log(logger)
    def create_virtual(
        self,
        lbr_type: str,
        vip_name: str,
        ip: str,
        port: dict,
        pool_name: str,
        env_domain: str,
    ):
        cert = f"star.{env_domain}"
        protocol = port["protocol"]
        client_ssl = cert if protocol == "https" else None
        vip_port = port["port"]
        created = False
        if lbr_type == "A10":
            if not hasattr(self.a10, "virtual_server_created"):
                created = self.a10.create_virtual_server(name=vip_name, ip=ip)
                self.a10.virtual_server_created = True
            port_created = self.a10.create_virtual_port(
                virtual_server=vip_name,
                port=vip_port,
                protocol=protocol,
                group=pool_name,
                template_http=port["template_http"],
                client_ssl=client_ssl,
            )
            logger.log.debug(
                f"{lbr_type}.virtual_port.create - {vip_name} - {vip_port}: {port_created}"
            )
        elif lbr_type == "F5":
            created = self.f5.create_virtual_server(
                name=vip_name,
                destination=ip,
                port=vip_port,
                pool=pool_name,
                http_profile_client=port["template_http"],
                ssl_profile_client=client_ssl,
            )
        return created

    @log(logger)
    def delete_virtual(self, lbr_type: str, vip_name: str):
        deleted = False
        if lbr_type == "A10":
            if not hasattr(self.a10, "virtual_server_deleted"):
                deleted = self.a10.delete_virtual_server(name=vip_name)
                self.a10.virtual_server_deleted = True
        elif lbr_type == "F5":
            deleted = self.f5.delete_virtual_server(name=vip_name)
        return deleted

    @log(logger)
    def delete_pool(self, lbr_type: str, pool_name: str):
        deleted = False
        if lbr_type == "A10":
            used_in_virtuals = self.a10.get_group_references(name=pool_name)
            if not used_in_virtuals:
                deleted = self.a10.delete_group(name=pool_name)
            else:
                logger.log.warning(
                    f"{lbr_type}.pool.delete - {pool_name}: used in {used_in_virtuals}"
                )
        elif lbr_type == "F5":
            used_in_virtuals = self.f5.get_pool_references(name=pool_name)
            if not used_in_virtuals:
                deleted = self.f5.delete_pool(name=pool_name)
            else:
                logger.log.warning(
                    f"{lbr_type}.pool.delete - {pool_name}: used in {used_in_virtuals}"
                )
        return deleted

    @log(logger)
    def delete_nodes(self, lbr_type: str, nodes: list[str]):
        for node in nodes:
            self.delete_node(lbr_type=lbr_type, node=node)

    @log(logger)
    def delete_node(self, lbr_type: str, node: str):
        deleted = False
        if lbr_type == "A10":
            used_in_groups = self.a10.get_server_references(name=node)
            if not used_in_groups:
                deleted = self.a10.delete_server(name=node)
            else:
                logger.log.warning(
                    f"{lbr_type}.node.delete - {node}: used in {used_in_groups}"
                )
        elif lbr_type == "F5":
            used_in_groups = self.f5.get_node_references(name=node)
            if not used_in_groups:
                deleted = self.f5.delete_node(name=node)
            else:
                logger.log.warning(
                    f"{lbr_type}.node.delete - {node}: used in {used_in_groups}"
                )
        return deleted


class MockedLBR:
    def get_vip_address(*args, **kwargs):
        return None

    def create_vip(*args, **kwargs):
        return True

    def delete_vip(*args, **kwargs):
        return True
