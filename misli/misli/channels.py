from misli.pubsub import Channel

entity_changes = Channel('__ENTITY_CHANGES__')
entity_changes_by_id = Channel('__ENTITY_CHANGES_BY_ID__',
                               lambda x: x.last_state().id)
entity_changes_by_parent_gid = Channel('__ENTITY_CHANGE_BY_PARENT_GID__',
                                       lambda x: x.last_state().parent_gid())
