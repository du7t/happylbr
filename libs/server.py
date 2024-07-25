from acos_client.errors import Exists as A10Exists
from api_libs.logger import log
from api_libs.logger import Logger

from libs.lbr_wrapper import LBR
from libs.model_base import Base


logger = Logger()


class Server(Base):
    def __init__(self, name: str, ip: str, location: str) -> None:
        super().__init__()
        self.name = name
        self.ip = ip
        self.location = location.upper()
        self._lbr = None
        self._lbr_wrp = None
        self._server = dict()

    @property
    def lbr_wrp(self):
        if not self._lbr_wrp:
            self._lbr_wrp = LBR(location=self.location)
        return self._lbr_wrp


class ServerA10(Server):

    @property
    def lbr(self):
        if not self._lbr:
            self._lbr = self.lbr_wrp.a10
        return self._lbr

    @property
    @log(logger)
    def server(self):
        if not self._server:
            item = self.lbr.get_server(name=self.name)
            if item:
                self._server = {
                    'name': item['name'],
                    'ip': item['host']
                }
        return self._server

    def validate_plan(self):
        if not self.plan['ip']:
            logger.log.error('No IP in Server plan')
            return False
        return True

    def validate_state(self):
        return True

    def create(self) -> bool:
        logger.log.info(f"Create server: {self.plan}")
        try:
            return bool(self.lbr.create_server(name=self.plan['name'], ip=self.plan['ip']))
        except A10Exists:
            return False

    def delete(self) -> bool:
        logger.log.info(f"Delete server: {self.name}")
        response = self.lbr.delete_server(name=self.name)
        return True if response['status'] == "OK" else False

    @property
    def plan(self):
        if not self._plan:
            self._plan = {
                'name': self.name,
                'ip': self.ip
            }
        return self._plan

    @property
    def state(self):
        if not self._state:
            self._state = self.server
        return self._state
