from fusion.entity_library.entity import Entity


class BaseUtilitiesProvider:
    def get_config_dict(self) -> Entity:
        raise NotImplementedError

    def set_config_dict(self, updated_config: Entity):
        raise NotImplementedError
