from __future__ import annotations
from copy import copy

from dataclasses import field
from pathlib import Path
from fusion.libs.entity import entity_type, Entity
from fusion.logging import get_logger

log = get_logger(__name__)


@entity_type
class PametSettings(Entity):
    _dict_on_load: dict = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def load(cls: PametSettings, config_dict: dict):
        dict_on_load = copy(config_dict)
        id = config_dict.pop('id', None)
        config = cls(id=id) if id else cls()
        config._dict_on_load = dict_on_load
        leftovers = config.replace_silent(**config_dict)
        if leftovers:
            log.error(f'Unrecognized keys found in the config: {leftovers}')

        return config

    def changes_present(self) -> bool:
        """Returns true if the config has been changed since it has been
        loaded.

        Can return True directly after load since there may have been some
        incompatible manual edit or missing default. The class applies those
        at load time.
        """
        return self._dict_on_load != self.asdict()

    def asdict(self) -> dict:
        self_dict = super().asdict()
        for key, val in self_dict.items():
            if isinstance(val, Path):
                self_dict[key] = str(val)

        return self_dict
