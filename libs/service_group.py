from acos_client.errors import Exists as A10Exists
from api_libs.logger import log
from api_libs.logger import Logger

from libs.lbr_wrapper import LBR
from libs.model_base import Base
from libs.server import ServerA10


logger = Logger()


class ServiceGroup(Base):
    def __init__(self, name: str, port_config: dict, location: str, endpoints: dict, healthcheck: str) -> None:
        super().__init__()
        self.name = name
        self.port_config = port_config
        self.location = location.upper()
        self.endpoints = endpoints
        self.healthcheck = healthcheck
        self._lbr = None
        self._lbr_wrp = None
        self._service_group = dict()

    @property
    def lbr_wrp(self):
        if not self._lbr_wrp:
            self._lbr_wrp = LBR(location=self.location)
        return self._lbr_wrp


class ServiceGroupA10(ServiceGroup):

    @property
    def lbr(self):
        if not self._lbr:
            self._lbr = self.lbr_wrp.a10
        return self._lbr

    @property
    @log(logger)
    def service_group(self):
        if not self._service_group:
            item = self.lbr.get_group(name=self.name)
            if item:
                self._service_group = {
                    'name': item['name'],
                    'health-check': item['health-check'],
                    'member-list': [{
                        'name': member['name'],
                        'port': member['port']
                    } for member in item.get('member-list', [])]
                }
        return self._service_group

    def validate_plan(self):
        if not self.plan['name']:
            logger.log.error('No name in Service group plan')
            return False
        return True

    def validate_state(self):
        return True

    def create(self) -> bool:
        logger.log.info(f"Create service group: {self.plan}")
        try:
            return bool(self.lbr.create_group(name=self.plan['name'], members=self.plan['member-list'],
                                              health_check=self.plan['health-check']))
        except A10Exists:
            return False

    def delete(self) -> bool:
        logger.log.info(f"Delete service group: {self.name}")
        response = self.lbr.delete_group(name=self.name)
        return True if response['status'] == "OK" else False

    @property
    def plan(self):
        if not self._plan:
            self._plan = {
                'name': self.name,
                'health-check': self.healthcheck,
                'member-list': [{
                    'name': endpoint,
                    'port': self.port_config['target_port']
                } for endpoint in self.endpoints]
            }
        return self._plan

    @property
    def state(self):
        if not self._state:
            self._state = self.service_group
        return self._state

    @property
    def siblings(self):
        if not self._siblings:
            for endpoint, value in self.endpoints.items():
                self._siblings[endpoint] = ServerA10(
                    name=endpoint, ip=value['ip'],
                    location=self.location
                )
        return self._siblings
