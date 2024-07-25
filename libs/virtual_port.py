from api_libs.logger import log
from api_libs.logger import Logger

from libs.lbr_wrapper import LBR
from libs.model_base import Base
from libs.service_group import ServiceGroupA10


logger = Logger()


class VirtualPort(Base):
    def __init__(self, virtual_server_name: str, port_config: dict, location: str,
                 endpoints: dict, sg_health: str, client_ssl: str) -> None:
        super().__init__()
        self.virtual_server_name = virtual_server_name
        self.port_config = port_config
        self.client_ssl = client_ssl
        self.location = location.upper()
        self.endpoints = endpoints
        self.sg_healthcheck = sg_health
        self._lbr = None
        self._lbr_wrp = None
        self._virtual_port = dict()

    @property
    def lbr_wrp(self):
        if not self._lbr_wrp:
            self._lbr_wrp = LBR(location=self.location)
        return self._lbr_wrp


class VirtualPortA10(VirtualPort):

    @property
    def lbr(self):
        if not self._lbr:
            self._lbr = self.lbr_wrp.a10
        return self._lbr

    @property
    @log(logger)
    def virtual_port(self):
        if not self._virtual_port:
            item = self.lbr.get_virtual_port(
                virtual_server=self.virtual_server_name,
                port=self.port_config['port'],
                protocol=self.port_config['protocol']
            )
            if item:
                self._virtual_port = {
                    'port-number': item['port-number'],
                    'protocol': item['protocol'],
                    'service-group': item.get('service-group'),
                    'client-ssl': item.get('template-client-ssl'),
                    'template-http': item.get('template-http'),
                }
        return self._virtual_port

    def validate_plan(self):
        if not self.plan['port-number']:
            logger.log.error('No port number in Virtual port plan')
            return False
        if not self.plan['service-group']:
            logger.log.error('No service group in Virtual port plan')
            return False
        return True

    def validate_state(self):
        return True

    def create(self) -> bool:
        logger.log.info(f"Create virtual port: {self.plan}")
        return bool(self.lbr.create_virtual_port(
            virtual_server=self.virtual_server_name,
            port=self.plan['port-number'],
            protocol=self.plan['protocol'],
            group=self.plan['service-group'],
            client_ssl=self.plan['client-ssl'],
            template_http=self.plan['template-http']
        ))

    def delete(self) -> bool:
        logger.log.info(f"Delete virtual port: {self.plan['port-number']}")
        response = self.lbr.delete_virtual_port(
            virtual_server=self.virtual_server_name,
            port=self.plan['port-number'],
            protocol=self.plan['protocol']
        )
        return True if response['status'] == "OK" else False

    @property
    def plan(self):
        if not self._plan:
            self._plan = {
                'port-number': self.port_config['port'],
                'protocol': self.port_config['protocol'],
                'service-group': self.lbr_wrp.get_pool_name_with_port(
                    nodes=[{'name': name} for name in self.endpoints], port=self.port_config
                )[0],
                'client-ssl': self.client_ssl if self.port_config['protocol'] == "https" else None,
                'template-http': self.port_config['template_http']
            }
        return self._plan

    @property
    def state(self):
        if not self._state:
            self._state = self.virtual_port
        return self._state

    @property
    def siblings(self):
        if not self._siblings:
            service_group_name = self.plan['service-group']
            self._siblings[service_group_name] = ServiceGroupA10(
                name=service_group_name, port_config=self.port_config,
                location=self.location, endpoints=self.endpoints, healthcheck=self.sg_healthcheck
            )
        return self._siblings
