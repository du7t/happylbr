from typing import Union

import fire
from api_libs.gitup import gitup_wrapper
from api_libs.helper import arg_to_list
from api_libs.helper import stats_collector
from api_libs.logger import Logger
from beartype import beartype

from libs.entrypoint_manager import EntrypointManager as EM

logger = Logger()


class CLI(object):
    """CLI for entrypoints management

    Run 'happyvip.py COMMAND --help' for more information on a command.
    """

    def _prepare_EM(self, env_name) -> None:
        if not env_name or not (isinstance(env_name, str)):
            raise ValueError("Incorrect env name given")
        self.env_name = env_name

        self.em = EM(env_name=self.env_name)
        if not self.em.env:
            raise ValueError("Incorrect env name given")

        if not EM.have_balancers(self.em.env.location):
            raise Exception(f'No balancers for {self.em.env.location}')

        self.overall_status = dict()

    def _lower(items: list) -> list:
        return [str(item).lower() for item in items]

    def _upper(items: list) -> list:
        return [str(item).upper() for item in items]

    def _convert_to_entrypoints(self, **kwargs):
        if kwargs['all']:
            services = self.em.env.get_all_services()
            entrypoints = ''
        else:
            entrypoints = arg_to_list(kwargs['entrypoints'], uniq=True)
            entrypoints = CLI._lower(entrypoints)
            services = arg_to_list(kwargs['services'], uniq=True)
            services = CLI._lower(services)
        mandatory = kwargs.get('mandatory', False)
        if not entrypoints and not services and not mandatory:
            raise ValueError('No entrypoints provided')
        self.entrypoints = EM.get_entrypoints(entrypoints=entrypoints, services=services, mandatory=mandatory)
        log_message = f"Entrypoints to process: {self.entrypoints} \n" if self.entrypoints else "No entrypoints to process."
        logger.log.info(log_message)

    @beartype
    def create(self, name: str,
               entrypoints: Union[str, tuple] = '',
               services: Union[str, tuple] = '',
               all: bool = False) -> dict:
        """
        Create LBR VIPS and related DNS records and ADS variables (sometimes) for given entrypoints

        Args:
            name: Name of the target ADS environment
            entrypoints: One or more entrypoints, for example 'intapi' or 'intapi,api'
            services: One or more services, for example 'pwr,psr'
            all: Create all entrypoints related to given ADS environment name
        """
        self._prepare_EM(name)
        self._convert_to_entrypoints(entrypoints=entrypoints, services=services, all=all, mandatory=True)

        for entrypoint in self.entrypoints:
            status = self.em.create_entrypoint(entrypoint)
            logger.log.info(f"'{entrypoint}' - created: {status['Entrypoint']['patched']}\n")
            self.overall_status[entrypoint] = status['Entrypoint']['patched']

        return self.overall_status

    @beartype
    def delete(self, name: str,
               entrypoints: Union[str, tuple] = '',
               services: Union[str, tuple] = '',
               all: bool = False) -> dict:
        """
        Delete LBR VIPS and related DNS records for given entrypoints

        Args:
            name: Name of the target ADS environment
            entrypoints: One or more entrypoints, for example 'intapi' or 'intapi,api'
            services: One or more services, for example 'pwr,psr'
            all: Delete all entrypoints related to given ADS environment name
        """
        self._prepare_EM(name)
        self._convert_to_entrypoints(entrypoints=entrypoints, services=services, all=all)

        for entrypoint in self.entrypoints:
            status = self.em.delete_entrypoint(entrypoint)
            logger.log.info(f"'{entrypoint}' - deleted: {status['Entrypoint']['deleted']}\n")
            self.overall_status[entrypoint] = status['Entrypoint']['deleted']

        return self.overall_status


@stats_collector
@gitup_wrapper
def main() -> None:
    cli = CLI()
    fire.Fire(cli, serialize=lambda _: [])


if __name__ == "__main__":
    main()
