import time

from api_libs.helper import write_cache
from api_libs.logger import log
from api_libs.logger import Logger
from jsondiff import diff

logger = Logger()


class Base:
    def __init__(self) -> None:
        self._global_state = dict()
        self._global_plan = dict()
        self._siblings = dict()
        self._state = None
        self._plan = None
        self._diff = None
        self._global_diff = None

    @property
    @log(logger)
    def diff(self):
        if not self._diff:
            self._diff = diff(self.state, self.plan, syntax='symmetric')
        return self._diff

    def _get_siblings_data(self, name: str):
        siblings_data = {}
        if self.siblings:
            for k, v in self.siblings.items():
                attribute = getattr(v, f'global_{name}')
                siblings_data[k] = attribute() if callable(attribute) else attribute
        return siblings_data

    def _is_siblings_data_success(self, data: dict, method: str):
        if isinstance(data, dict):
            if method in data and not data[method]:
                return False
            # Recursively check 'siblings' values
            return all(self._is_siblings_data_success(value, method) for value in data.values())
        else:
            return data

    @property
    def global_diff(self):
        if not self._global_diff:
            self._global_diff = {
                self.__class__.__name__: {
                    'diff': self.diff(),
                    'siblings': self._get_siblings_data('diff')
                }
            }
        return self._global_diff

    def validate_state(self):
        # Should be implemented on higher levels
        return False

    def validate_plan(self):
        # Should be implemented on higher levels
        return False

    def create(self):
        # Should be implemented on higher levels
        return False

    def delete(self):
        # Should be implemented on higher levels
        return False

    @log(logger)
    def patch(self) -> bool:
        if not self.are_we_good():
            return False

        if self.diff:
            self.delete() if self.state else None
            self.create()
        else:
            logger.log.info(f"{self.__class__.__name__} - no diff, state: {self.state}")

        return True

    @log(logger)
    def global_patch(self):
        siblings_data = self._get_siblings_data('patch')
        self_patched = self.patch() if self._is_siblings_data_success(siblings_data, 'patched') else False

        return {
            self.__class__.__name__: {
                'patched': self_patched,
                'siblings': siblings_data
            }
        }

    @log(logger)
    def global_delete(self):
        self_deleted = self.delete()
        siblings_data = {} if not self_deleted else self._get_siblings_data('delete')

        return {
            self.__class__.__name__: {
                'deleted': self_deleted,
                'siblings': siblings_data
            }
        }

    @property
    @log(logger)
    def global_plan(self):
        if not self._global_plan:
            self._global_plan = {
                self.__class__.__name__: {
                    'plan': self.plan,
                    'is_valid': self.validate_plan(),
                    'siblings': self._get_siblings_data('plan')
                }
            }
        return self._global_plan

    @property
    @log(logger)
    def global_state(self):
        if not self._global_state:
            self._global_state = {
                self.__class__.__name__: {
                    'state': self.state,
                    'is_valid': self.validate_state(),
                    'siblings': self._get_siblings_data('state')
                }
            }
        return self._global_state

    @property
    def siblings(self):
        # Should be implemented on higher levels
        return self._siblings

    def save(self):
        ts = time.time()
        prefix = f'{self.__class__.__name__}-{self.name}-{ts}'
        write_cache(cache_dir='data', cache_filename=f'State_{prefix}.json', data=self.state)
        write_cache(cache_dir='data', cache_filename=f'Plan_{prefix}.json', data=self.plan)

    @log(logger)
    def are_we_good(self):
        return all([self.validate_plan(), self.validate_state()])
