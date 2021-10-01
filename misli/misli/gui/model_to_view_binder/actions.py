from typing import List
from misli import gui, Change


@gui.action('update_views_from_entity_changes')
def update_views_from_entity_changes(changes: List[Change]):
    for change in changes:
        entity = change.last_state()

        if change.is_create():
            # Get all views mapped to its parent
            # and create views for the entity
            parent_views = gui.mapping.views_for(entity.parent_gid())

            for parent_view in parent_views:
                gui.create_view(
                    parent_view.id,
                    view_class_metadata_filter=dict(obj_type=entity.obj_type),
                    mapped_entity=entity)

        elif change.is_update():
            _views = gui.mapping.views_for(entity.gid())

            for _view in _views:
                view_state = _view.state
                view_state.mapped_entity = entity
                gui.update_state(view_state)

        elif change.is_delete():
            _views = gui.mapping.views_for(entity.gid())

            for _view in _views:
                gui.remove_view(_view)
