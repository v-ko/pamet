#!/usr/bin/env python

import os
import shutil
import signal
import argparse
import json
import uuid

from PySide2.QtCore import Qt, QPoint
from PySide2.QtGui import QPixmap, QRegion

import misli
from misli.gui import update_components_from_changes
from misli.gui.desktop import usecases, QtMainLoop
from misli.gui.actions_lib import ActionStateTypes

log = misli.get_logger(__name__)
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Save smaller images for the visual comparisons in order to ignore pixel-level
# differences (that might occure on different resolutions, etc)
RESIZED_IMAGE_HEIGHT = 200


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_folder', default='recording_output')
    replay_help = ('First replays the commands from the given actions '
                   'recording file and then appends any actions done by the '
                   'user.')
    parser.add_argument('--start-with-replay',  type=argparse.FileType('r'),
                        help=replay_help)
    parser.add_argument('--ignore-actions', nargs='+',
                        help='Names of the actions to skip while recording')

    parser.add_argument('--overwrite', action='store_true')

    args = parser.parse_args()

    output_folder = args.output_folder
    # replay_file_path = args.start_with_replay
    ignored_actions_list = args.ignore_actions

    if os.path.exists(output_folder):
        if args.overwrite:
            shutil.rmtree(output_folder)
        else:
            print('The given output path is not empty. To overwrite it use the'
                  ' "--overwrite" option. Aborting.')
            return

    os.makedirs(output_folder)
    if not ignored_actions_list:
        ignored_actions_list = []

    actions_stack = []
    recoding = []
    pixmaps = {}

    def capture_qt_component_to_image(image_id):
        browser_windows = [c for c in misli.gui.components()
                           if c.obj_class == 'BrowserWindow']

        if not browser_windows:
            return

        if len(browser_windows) > 1:
            raise Exception('More than one browser window')

        browser_window = browser_windows[0]

        pixmap = QPixmap(browser_window.rect().size())
        browser_window.render(pixmap, QPoint(), QRegion(browser_window.rect()))

        pixmaps[image_id] = pixmap

    def record_action_state(action_state):
        recoding.append(action_state.to_dict())
        capture_qt_component_to_image(action_state.id)

    def handle_action_channel(action_states):
        for action_state in action_states:
            if action_state.type == ActionStateTypes.STARTED:
                actions_stack.append(action_state)

            elif action_state.type == ActionStateTypes.FINISHED:
                last = actions_stack.pop()

                if action_state.id != last.id:
                    raise Exception('Logical mismatch in action nesting')

                if actions_stack:  # We only want to recod top-level actions
                    continue

                if action_state.action_name in ignored_actions_list:
                    continue

                misli.call_delayed(record_action_state, 0, args=[action_state])

    misli.set_main_loop(QtMainLoop())
    misli.on_change(update_components_from_changes)
    misli.gui.on_action(handle_action_channel)

    desktop_app = misli.gui.create_component('DesktopApp', parent_id='')

    # If playing back recording - ignore this
    usecases.new_browser_window_ensure_page()
    desktop_app.exec_()

    #
    # Process recorded action_states
    log.info('Processing recorded action states')

    output_file_path = os.path.join(output_folder, 'misli_actions_record.json')
    if os.path.exists(output_file_path):
        unique_name = 'misli_actions_record-%s.json' % str(uuid.uuid4())[:8]
        output_file_path = os.path.join(output_folder, unique_name)

    with open(output_file_path, 'w') as of:
        json.dump(recoding, of)

    images_folder = os.path.join(output_folder, 'images')
    os.makedirs(images_folder)

    for image_id, pixmap in pixmaps.items():
        image = pixmap.toImage()
        image_scaled = image.scaledToHeight(
            RESIZED_IMAGE_HEIGHT, Qt.SmoothTransformation)

        image_path = os.path.join(images_folder, image_id + '.jpg')
        image_scaled.save(image_path)

    print('Record finished.')


if __name__ == '__main__':
    main()
