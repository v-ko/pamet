from misli import logging
log = logging.getLogger(__name__)

components_by_class_name = {}
edit_components_by_class_name = {}
edit_components_for_obj_class = {}


def add(obj_class_name, ComponentClass):
    components_by_class_name[obj_class_name] = ComponentClass


def get(note_type):
    return components_by_class_name[note_type]


def map_edit_component(obj_class_name, edit_class_name):
    if edit_class_name not in components_by_class_name:
        log.error('Can\'t map edit component %s, it\'s not registered' %
                  edit_class_name)
        return

    ComponentClass = components_by_class_name[edit_class_name]
    edit_components_by_class_name[edit_class_name] = ComponentClass
    edit_components_for_obj_class[obj_class_name] = edit_class_name


def get_edit_class_name(obj_class_name):
    return edit_components_for_obj_class[obj_class_name]


def edit_component_names():
    return edit_components_by_class_name.keys()
