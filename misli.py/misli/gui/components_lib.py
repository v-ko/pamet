compopnents_by_class = {}
edit_components_for_class = {}


def add(obj_class_name, ComponentClass):
    compopnents_by_class[obj_class_name] = ComponentClass


def get(note_type):
    return compopnents_by_class[note_type]


def map_edit_component(obj_class_name, edit_class_name):
    edit_components_for_class[obj_class_name] = edit_class_name


def get_edit_class_name(obj_class_name):
    return edit_components_for_class[obj_class_name]
