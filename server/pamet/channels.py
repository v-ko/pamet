from fusion.libs.channel import Channel

# Entity changeset per top-level action (TLA), meaning the channel transmits
# change-set objects (lists or sets) containing the changes made in a TLA
# Note: A TLA is a non-nested action.
entity_change_sets_per_TLA = Channel('__ENTITY_CHANGESETS_PER_TLA__')

entity_changes_by_id = Channel('__ENTITY_CHANGES_BY_ID__',
                               index_key=lambda x: x.last_state().id)
entity_changes_by_parent_gid = Channel(
    '__ENTITY_CHANGE_BY_PARENT_GID__',
    index_key=lambda x: x.last_state().parent_gid())
# page_changes = Channel('__PAGE_CHANGES__',
#                        filter_key=lambda c: isinstance(c.last_state(), Page))
