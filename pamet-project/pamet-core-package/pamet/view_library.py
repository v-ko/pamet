from misli import get_logger
log = get_logger(__name__)

_views_by_class_name = {}
_edit_views_by_class_name = {}


def add_view_class(view_type):
    view_class_name = view_type.view_class
    if view_class_name in _views_by_class_name:
        raise Exception('A view with that name is already registered')

    log.info('Adding view %s' % view_class_name)
    _views_by_class_name[view_class_name] = view_type


def add_edit_view_class(view_name, edit_view_type):
    edit_view_class_name = edit_view_type.view_class
    if edit_view_class_name in _edit_views_by_class_name:
        raise Exception('A view with that name is already registered')

    _edit_views_by_class_name[view_name] = edit_view_type


def get_view_class(view_class_name):
    return _views_by_class_name[view_class_name]


def get_edit_view_class(view_class_name):
    return _edit_views_by_class_name[view_class_name]


def edit_view_names():
    return list(_edit_views_by_class_name.keys())
