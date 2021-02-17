from misli import get_logger
log = get_logger(__name__)

components_by_class_name = {}
edit_components_by_class_name = {}
edit_components_for_obj_class = {}


def add(obj_class_name: str, ComponentClass):
    log.info('Adding component %s' % obj_class_name)
    components_by_class_name[obj_class_name] = ComponentClass


def get(obj_class_name: str):
    return components_by_class_name[obj_class_name]


def map_edit_component(obj_class_name: str, edit_class_name: str):
    if edit_class_name not in components_by_class_name:
        log.error('Can\'t map edit component %s, it\'s not registered' %
                  edit_class_name)
        return

    ComponentClass = components_by_class_name[edit_class_name]
    edit_components_by_class_name[edit_class_name] = ComponentClass
    edit_components_for_obj_class[obj_class_name] = edit_class_name


def get_edit_class_name(obj_class_name: str):
    return edit_components_for_obj_class[obj_class_name]


def edit_component_names():
    return edit_components_by_class_name.keys()


def create_component(obj_class, *args, **kwargs):
    component_class = get(obj_class)

    if not component_class:
        raise Exception('No such note class: %s' % obj_class)

    return component_class(*args, **kwargs)
