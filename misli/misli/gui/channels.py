from misli.pubsub import Channel


raw_state_changes = Channel('__RAW_STATE_CHANGES__')
state_changes_by_id = Channel('__STATE_CHANGES_BY_ID__',
                              lambda x: x.last_state().id)
completed_root_actions = Channel('__COMPLETED_ACTIONS__')
