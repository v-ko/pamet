from fusion.pubsub import Channel

raw_state_changes = Channel('__RAW_STATE_CHANGES__')
state_changes_per_TLA_by_view_id = Channel(
    '__AGGREGATED_STATE_CHANGES_PER_TLA__', lambda x: x.last_state().view_id)
completed_root_actions = Channel('__COMPLETED_ROOT_ACTIONS__')
