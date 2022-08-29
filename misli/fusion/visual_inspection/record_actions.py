#!/usr/bin/env python

import signal
import argparse

import fusion
from fusion.gui import update_components_from_changes
from pamet import usecases
import pamet
from fusion.gui.utils.qt_widgets.qt_main_loop import QtMainLoop

from .gui_recorder import FusionGuiRecorder
from .gui_replay import FusionGuiReplay

log = fusion.get_logger(__name__)
signal.signal(signal.SIGINT, signal.SIG_DFL)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-folder', default='tmp_recording')
    parser.add_argument(
        '--start-with-replay',
        help=('First replays the commands from the given actions recording '
              'file and then appends any actions done by the user.'))
    parser.add_argument(
        '--ignore-actions', nargs='+',
        help='Names of the actions to skip while recording')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--replay-speed', default=1, type=float)
    args = parser.parse_args()

    output_folder = args.output_folder
    file_for_replay = args.start_with_replay
    ignored_actions_list = args.ignore_actions
    overwrite = args.overwrite
    replay_speed = args.replay_speed

    fusion.set_main_loop(QtMainLoop())
    misli_gui.set_reproducible_ids(True)
    fusion.on_change(update_components_from_changes)

    controller = FusionGuiRecorder('BrowserWindowView', ignored_actions_list)
    fusion.gui.on_action_logged(controller.handle_action_channel)

    if file_for_replay:
        replay = FusionGuiReplay(file_for_replay)
        replay.speed = replay_speed
        fusion.gui.on_action_logged(replay.queue_next_action)

    desktop_app_class = pamet.view_library.get_view_class('BrowserWindowView')
    desktop_app = desktop_app_class(parent=None)

    if file_for_replay:
        replay.queue_next_action()
    else:
        usecases.new_browser_window_ensure_page()

    desktop_app.exec_()

    # Process recorded action_states
    log.info('App closed. Processing recorded action states.')
    controller.save_recording(output_folder, overwrite=overwrite)
    print('Recording saved to %s' % output_folder)


if __name__ == '__main__':
    main()
