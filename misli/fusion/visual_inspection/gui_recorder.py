import os
import shutil
import json

from PySide6.QtCore import QPoint
from PySide6.QtGui import QPixmap, QRegion

import fusion
from fusion import gui

from fusion.gui.actions_library import ActionCall
from .constants import RECORDING_EXTENSION, SNAPSHOTS_FOLDER_NAME

log = fusion.get_logger(__name__)

# Save smaller images for the visual comparisons in order to ignore pixel-level
# differences (that might occure on different resolutions, etc)
# RESIZED_IMAGE_HEIGHT = 200


class FusionGuiRecorder:

    def __init__(self, component_name, ignored_actions_list=None):
        self.component_name = component_name
        self.ignored_actions_list = ignored_actions_list or []
        self.recoding = []
        self.snapshots = {}

    def capture_qt_component_to_image(self, image_id):
        matching_components = [
            c for c in gui.views() if c.view_class == self.component_name
        ]

        if not matching_components:
            self.snapshots[image_id] = None

        if len(matching_components) > 1:
            raise Exception('More than one browser window')

        target_component = matching_components[0]

        pixmap = QPixmap(target_component.rect().size())
        target_component.render(pixmap, QPoint(),
                                QRegion(target_component.rect()))

        self.snapshots[image_id] = pixmap

    def handle_action_channel(self, action_states):
        top_lvl_action = action_states[-1]
        self.recoding.append(top_lvl_action)

        action = ActionCall(**top_lvl_action)
        log.info('Recorded action %s' % action)

        last_index = len(self.recoding) - 1
        fusion.call_delayed(self.capture_qt_component_to_image,
                            0,
                            args=[last_index])

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
            json.dump(self.recoding, of, ensure_ascii=False)

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
