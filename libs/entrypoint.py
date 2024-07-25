import api_libs.ads_mini as ads
import api_libs.dna as dna_wrapper
import api_libs.ip_tools as ip_tools
from api_libs.helper import get_ff
from api_libs.helper import retry_on_exceptions
from api_libs.inventory import Inventory
from api_libs.logger import log
from api_libs.logger import Logger
from retrying import retry

from conf.static import balancers
from conf.static import entrypoints
from conf.static import shared_entrypoints
from libs.lbr_wrapper import LBR
from libs.model_base import Base
from libs.virtual_server import VirtualServerA10
from libs.virtual_server import VirtualServerF5


logger = Logger()


class Entrypoint(Base):
    def __init__(self, name: str, env: ads.Env, endpoints: dict) -> None:
        super().__init__()
        self.env = env
        self.interface_name = name
        self.name = f'{name}-{self.env.suffix}'
        self.fqdn = f'{self.name}.{self.env.domain}'
        self.endpoints = endpoints
        self._current_dns = None
        self._planned_dns = None
        self._current_nodes = None
        self._shared_env_suffix = None
        self._lbr_wrp = None
        self.dna = dna_wrapper.DNA(url=f"{get_ff('DNA')['DNAURL']}/api/submit", token=get_ff('DNA')['DNATOKEN'])
        self._ip = None
        self.inv = Inventory(mode=get_ff('INVENTORY_MODE'), netbox_api=get_ff('NETBOX_API'),
                             netbox_token=get_ff('NETBOX_TOKEN'), rt_api=get_ff('RT')['DOMAIN'])

    @staticmethod
    def get_shared_env_suffix(entrypoint: str, servers: list[dict]) -> str:
        hostnames = list()
        for server in servers:
            if 'name' in server:
                hostnames.append(server['name'])
            else:
                hostnames.append(server)
        if entrypoint in shared_entrypoints:
            for env_suffix, shared_servers in shared_entrypoints[entrypoint].items():
                if any(hostname in shared_servers for hostname in hostnames):
                    return env_suffix

    @property
    @log(logger)
    def ip(self):
        if not self._ip:
            self._ip = (self.plan['dns']['ips'].get('A', [None]) or [None])[0]
            if self._ip == 'Need to reserve IP':
                logger.log.info(f"There is no IP in inventory for entrypoint: {self.name}")
                self._ip = None
        return self._ip

    @ip.setter
    def ip(self, value):
        self._ip = value

    @property
    @log(logger)
    def current_dns(self):
        if not self._current_dns:
            self._current_dns = self._get_current_dns()
        return self._current_dns

    @property
    @log(logger)
    def current_nodes(self):
        if not self._current_nodes:
            if self.shared_env_suffix:
                nodes = ['Shared nodes']
            else:
                nodes = set()
                # Get nodes assosiated with the IP
                if self.current_dns['A']:
                    for ip in self.current_dns['A']:
                        interfaces = self.inv.get_interfaces(ip=ip)
                        if interfaces:
                            for item in interfaces:
                                if item['name'] != 'nic0':
                                    nodes.add(item['host_name'])

                # Inventory may have node:interface links not assosiated with the IP which we can not just ignore
                for node in self.endpoints.keys():
                    interfaces = self.inv.get_interfaces(hostname=node)
                    if interfaces:
                        for item in interfaces:
                            if item['name'] == self.interface_name:
                                nodes.add(item['host_name'])
            self._current_nodes = sorted(list(nodes))
        return self._current_nodes

    @property
    @log(logger)
    def planned_dns(self):
        if not self._planned_dns:
            self._planned_dns = self._get_planned_dns()
        return self._planned_dns

    @property
    @log(logger)
    def state(self):
        """ State is based on DNS and Inventory information"""
        if not self._state:
            self._state = {
                'name': self.name,
                'dns': {
                    'fqdn': self.fqdn,
                    'ips': self.current_dns
                },
                'inventory': {
                    'nodes': self.current_nodes
                }
            }
        return self._state

    @property
    @log(logger)
    def plan(self):
        """ Plan is based on endpoints structure """
        if not self._plan:
            if self.shared_env_suffix:
                nodes = ['Shared nodes']
            else:
                nodes = sorted([node for node in self.endpoints.keys()])
            self._plan = {
                'name': self.name,
                'dns': {
                    'fqdn': self.fqdn,
                    'ips': self.planned_dns
                },
                'inventory': {
                    'nodes': nodes  # Nodes gathered from ADS and we plan to put them in inventory as interfaces
                }
            }
        return self._plan

    @property
    @log(logger)
    def lbr_wrp(self):
        if not self._lbr_wrp:
            self._lbr_wrp = LBR(location=self.env.location)
        return self._lbr_wrp

    @property
    @log(logger)
    def siblings(self):
        if not self._siblings and not self.shared_env_suffix and self.are_we_good() and self.ip:
            ports_config = self.lbr_wrp.get_ports_config(entrypoint=self.interface_name)
            cert = f"star.{self.env.domain}"
            if entrypoints[self.interface_name]['LB'] == 'A10':
                self._siblings[self.name] = VirtualServerA10(name=self.name, entrypoint=self.interface_name, ip=self.ip,
                                                             location=self.env.location, endpoints=self.endpoints,
                                                             ssl_profile_client=cert)
            if entrypoints[self.interface_name]['LB'] == 'F5':
                for item in ports_config:
                    port = item['port']
                    virtual_name = f"{self.name}_{port}"
                    http_profile_client = item['template_http']
                    ssl_profile_client = cert if item['protocol'] == "https" else None
                    self._siblings[virtual_name] = VirtualServerF5(name=virtual_name, entrypoint=self.interface_name,
                                                                   ip=self.ip, location=self.env.location,
                                                                   endpoints=self.endpoints, port=port,
                                                                   http_profile_client=http_profile_client,
                                                                   ssl_profile_client=ssl_profile_client)
        return self._siblings

    def _get_current_dns(self):
        return ip_tools.nslookup(qname=self.fqdn, resolve_cname=False)

    @property
    @log(logger)
    def shared_env_suffix(self):
        if not self._shared_env_suffix:
            self._shared_env_suffix = Entrypoint.get_shared_env_suffix(entrypoint=self.interface_name,
                                                                       servers=list(self.endpoints.keys()))
        return self._shared_env_suffix

    def _get_planned_dns(self):
        if self.shared_env_suffix:
            return {'A': [], 'CNAME': [f'{self.interface_name}-{self.shared_env_suffix}.{self.env.domain}']}
        else:
            ips = list()
            for data in self.endpoints.values():
                for item in data['interfaces']:
                    if self.interface_name == item[0]:
                        ips.append(item[1])

            if not ips:
                ips = ['Need to reserve IP']
            else:
                ips = sorted(ips)
            return {'A': ips, 'CNAME': []}

    @log(logger)
    def validate_plan(self):
        if len(self.plan['dns']['ips']['A']) > 1:
            logger.log.error(f"Too many DNS A records in plan: {self.fqdn} > {self.plan['dns']['ips']['A']}")
            return False
        if self.plan['dns']['ips']['A'] and len(self.plan['dns']['ips']['CNAME']) > 0:
            logger.log.error(f"DNS CNAME detected in plan: {self.fqdn} > {self.plan['dns']['ips']['CNAME'][0]}")
            return False
        return True

    @log(logger)
    def validate_state(self):
        if len(self.state['dns']['ips']['A']) > 1:
            logger.log.error(f"Too many DNS A records in state: {self.fqdn} > {self.state['dns']['ips']['A']}")
            return False
        if self.state['dns']['ips']['CNAME'] and not self.shared_env_suffix:
            logger.log.error(f"DNS CNAME detected in state: {self.fqdn} > {self.state['dns']['ips']['CNAME'][0]}")
            return False
        return True

    @log(logger)
    def clean(self, dry_mode=True):
        if not self.validate_plan():
            self.save()
            planned_ips = self.plan['dns']['ips']['A']
            current_ips = self.state['dns']['ips']['A']
            wrong_ips = set(planned_ips) - set(current_ips)
            if wrong_ips:
                for node in self.current_nodes:
                    for ip in wrong_ips:
                        logger.log.info(f'Need to remove {node}:{self.interface_name}:{ip}')
                        if not dry_mode:
                            r = self.inv.delete_interface(ip=ip, host_name=node)
                            logger.log.info(r)

    @log(logger)
    def get_network(self) -> str:
        return balancers[self.env.location][entrypoints[self.interface_name]["LB"]]["network"]

    @log(logger)
    def get_prefix(self) -> str:
        return balancers[self.env.location][entrypoints[self.interface_name]["LB"]]["prefix"]

    @log(logger)
    def reserve_ip(self, nodes: list = None) -> str:
        network = self.get_network()
        prefix = self.get_prefix()
        ip = self.inv.reserve_ip_for_nodes(network, prefix, self.interface_name, nodes, self.ip)
        return ip

    def get_planned_value_for_ads_variable(self, name: str) -> str:
        planned_value = entrypoints[self.interface_name]["adsvars"][name]
        return planned_value.replace('{ENV.DNS_PREFIX}', f'-{self.env.suffix}.{self.env.domain}')

    @retry(stop_max_attempt_number=get_ff("RETRY_COUNT"), stop_max_delay=20000, wait_fixed=5000,
           retry_on_exception=retry_on_exceptions)
    @log(logger)
    def update_ads_variables(self) -> bool:
        """
        We expect that Xadmin has LBR compatible configuration in defaults
        Happylbr doesn't touch host/service/pop/pod level overrides
        During happylbr run:
        Remove local variable(if exists) and check resulting value, notify if it doesn’t match with static
        Notify about necessity of deploying config and running happysct --force
        """
        for ads_variable in entrypoints[self.interface_name]["adsvars"]:
            planned_value = self.get_planned_value_for_ads_variable(name=ads_variable)
            if not self.env.does_variable_match(ads_variable, planned_value):
                self.env.set_env_level_variable(name=ads_variable, value='')
                logger.log.warning('ADS variables do not match with the desired configuration')
                logger.log.warning(f'Expected {ads_variable} = {planned_value}')
                logger.log.warning('Deploy configuration and/or update SCT services')
            return self.env.does_variable_match(ads_variable, planned_value)

    @log(logger)
    def create(self) -> bool:
        if not self.are_we_good():
            return False

        if self.shared_env_suffix:
            value = f"{self.interface_name}-{self.shared_env_suffix}.{self.env.domain}"
            logger.log.info(f"Create DNS record: {self.fqdn} > CNAME > {value}")
            return self.dna.add_dns_record(record_type="CNAME", source=self.fqdn, value=value, force=True)
        else:
            self.ip = self.reserve_ip([self.endpoints.keys()])
            logger.log.info(f"Reserved IP in inventory: {self.ip}")
            logger.log.info(f"Create DNS record: {self.fqdn} > A > {self.ip}")
            create_dns_status = self.dna.add_dns_record(record_type="A", source=self.fqdn, value=self.ip, force=True)
            self.update_ads_variables()
            return self.ip and create_dns_status

    @log(logger)
    def delete(self) -> bool:
        if self.shared_env_suffix:
            value = f"{self.interface_name}-{self.shared_env_suffix}.{self.env.domain}"
            logger.log.info(f"Delete DNS record: {self.fqdn} > CNAME > {value}")
            return self.dna.delete_dns_record(record_type="CNAME", source=self.fqdn, value=value)
        else:
            for ip in self.state['dns']['ips']['A']:
                # logger.log.info(f"Delete shared IP from inventory: {ip}")
                # self.inv.remove_shared_ip(ip)
                logger.log.info(f"Delete DNS record: {self.fqdn} > A > {ip}")
                self.dna.delete_dns_record(record_type="A", source=self.fqdn, value=ip)
            for node in self.state['inventory']['nodes']:
                interfaces = self.inv.get_interfaces(hostname=node)
                for interface in interfaces:
                    if interface['name'] == self.interface_name:
                        logger.log.info(f"Delete IP: {interface['ip']} on host: {node} from inventory")
                        self.inv.delete_interface(host_name=node, ip=interface['ip'])
                        self.dna.delete_dns_record(record_type="A", source=self.fqdn, value=interface['ip'])
                        break
            return True

    @log(logger)
    def global_patch(self):
        self_patched = self.patch()
        siblings_data = {} if not self_patched else self._get_siblings_data('patch')

        return {
            self.__class__.__name__: {
                'patched': self_patched,
                'siblings': siblings_data
            }
        }

    def global_delete(self):
        siblings_data = self._get_siblings_data('delete')
        self_deleted = self.delete()

        return {
            self.__class__.__name__: {
                'deleted': self_deleted,
                'siblings': siblings_data
            }
        }

    @log(logger)
    def patch(self) -> bool:
        if not self.are_we_good():
            return False

        if self.diff:
            # We have to deal with possible DNS cache issues
            # Planned IP = "Need to reserve IP", State IP = some old IP (already deleted but still present in the DNS cache)
            if self.plan['dns']['ips']['A'] == ['Need to reserve IP'] and self.state['dns']['ips']['A']:
                logger.log.warning(f"Inventory and DNS diff: {self.plan['dns']['ips']['A']} vs {self.state['dns']['ips']['A']}")
                self.create()
            else:
                self.delete()
                self.create()
        else:
            logger.log.info(f"{self.__class__.__name__} - no diff, state: {self.state}")

        return True
