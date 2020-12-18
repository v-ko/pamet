import os
import shutil
import json

from PySide2.QtCore import Qt, QPoint
from PySide2.QtGui import QPixmap, QRegion

import misli
from constants import RECORDING_EXTENSION, SNAPSHOTS_FOLDER_NAME

# Save smaller images for the visual comparisons in order to ignore pixel-level
# differences (that might occure on different resolutions, etc)
# RESIZED_IMAGE_HEIGHT = 200


class MisliGuiRecorder:
    def __init__(self, component_name, ignored_actions_list=None):
        self.component_name = component_name
        self.ignored_actions_list = ignored_actions_list or []
        self.recoding = []
        self.snapshots = {}

    def capture_qt_component_to_image(self, image_id):
        browser_windows = [c for c in misli.gui.components()
                           if c.obj_class == self.component_name]

        if not browser_windows:
            self.snapshots[image_id] = None

        if len(browser_windows) > 1:
            raise Exception('More than one browser window')

        browser_window = browser_windows[0]

        pixmap = QPixmap(browser_window.rect().size())
        browser_window.render(pixmap, QPoint(), QRegion(browser_window.rect()))

        self.snapshots[image_id] = pixmap

    def record_action_state(self, action_state):
        self.recoding.append(action_state)
        self.capture_qt_component_to_image(len(self.recoding) - 1)

    def handle_action_channel(self, action_states):
        top_lvl_action = action_states[-1]

        misli.call_delayed(
            self.record_action_state, 0, args=[top_lvl_action])

    def save_recording(self, output_folder, overwrite=False):
        if os.path.exists(output_folder):
            if overwrite:
                shutil.rmtree(output_folder)
            else:
                print('The given output path is not empty. To overwrite it '
                      'use the "--overwrite" option. Aborting.')
                return

        os.makedirs(output_folder)

        # Make times relative to the first action
        t0 = -1
        for i, action_state in enumerate(self.recoding):
            if i == 0:
                t0 = action_state['start_time']
                action_state['start_time'] = 0
                continue

            action_state['start_time'] -= t0

        name = os.path.basename(output_folder) + RECORDING_EXTENSION
        output_file_path = os.path.join(output_folder, name)
        with open(output_file_path, 'w') as of:
            json.dump(self.recoding, of)

        images_folder = os.path.join(output_folder, SNAPSHOTS_FOLDER_NAME)
        os.makedirs(images_folder)

        img_idx = -1
        for image_id, pixmap in self.snapshots.items():
            img_idx += 1

            image = pixmap.toImage()
            # image = image.scaledToHeight(
            #     RESIZED_IMAGE_HEIGHT, Qt.SmoothTransformation)

            _type = self.recoding[image_id]['type']
            image_name = '%s_%s.png' % (img_idx, _type)
            image_path = os.path.join(images_folder, image_name)
            image.save(image_path)
