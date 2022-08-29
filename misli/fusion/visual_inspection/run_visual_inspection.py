import os
import shutil
import argparse
from PIL import Image, ImageChops, ImageStat

import fusion
from .constants import RECORDING_EXTENSION, SNAP_EXTENSION
from fusion.gui import update_components_from_changes
from fusion.gui.utils.qt_widgets.qt_main_loop import QtMainLoop

import pamet

from .gui_recorder import FusionGuiRecorder
from .gui_replay import FusionGuiReplay

INSPECTION_TEMPLATES_PATH = 'inspection_templates'
AUTOMATIC_INSPECTION_OUTPUT_PATH = 'automatic_inspection_output'
MANUAL_INSPECTION_OUTPUT_PATH = 'manually_verified_inspections'
DIFF_FOLDER = 'tmp_last_visual_inspection_diffs'


def run_recording(file_for_replay, output_folder, replay_speed):
    fusion.set_main_loop(QtMainLoop())
    misli_gui.set_reproducible_ids(True)

    recorder = FusionGuiRecorder('BrowserWindowView')
    fusion.gui.on_action_logged(recorder.handle_action_channel)

    replay = FusionGuiReplay(file_for_replay)
    replay.speed = replay_speed

    fusion.on_change(update_components_from_changes)
    fusion.gui.on_action_logged(replay.queue_next_action)

    desktop_app_class = pamet.view_library.get_view_class('BrowserWindowView')
    desktop_app = desktop_app_class(parent=None)

    replay.queue_next_action([])
    desktop_app.exec_()

    recorder.save_recording(output_folder, overwrite=True)


def compare_images(img1, img2):
    # Don't compare if images are of different modes or different sizes.
    if (img1.mode != img2.mode) \
            or (img1.size != img2.size) \
            or (img1.getbands() != img2.getbands()):
        return 100

    # Generate diff image in memory.
    diff_img = ImageChops.difference(img1, img2)
    # Calculate difference as a ratio.
    stat = ImageStat.Stat(diff_img)
    diff_ratio = sum(stat.mean) / (len(stat.mean) * 255)

    return diff_ratio * 100


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manual-verification', action='store_true')
    parser.add_argument('--replay-speed', default=1)
    args = parser.parse_args()

    manual_verification = args.manual_verification
    replay_speed = args.replay_speed

    output_folder = AUTOMATIC_INSPECTION_OUTPUT_PATH
    if manual_verification:
        print('MANUAL MODE: The generated snapshots of the BrowserWindow will'
              ' be used for the automatic visual inspections, so you should'
              ' verify that the app is working correctly. You can adjust the'
              ' actions replay speed with the --replay-speed argument.')
        output_folder = MANUAL_INSPECTION_OUTPUT_PATH

    print('RUNNING AUTOMATED TESTS: press CTRL+C in the console to abort the '
          'process and discard the last test. Press Enter to start.')

    for template in os.scandir(INSPECTION_TEMPLATES_PATH):
        if not template.name.endswith(RECORDING_EXTENSION):
            raise Exception('Unexpected file %s' % template)

        tname = template.name[:-len(RECORDING_EXTENSION)]

        results_folder = os.path.join(output_folder, tname)

        run_recording(template.path, results_folder, replay_speed)
        print('Done with template "%s".' % tname)

    if manual_verification:
        return

    print('Done with all inspections. Starting to compare with the manually '
          'verified data')

    diffs_found = 0

    for recording in os.scandir(AUTOMATIC_INSPECTION_OUTPUT_PATH):
        snapshots_folder = os.path.join(recording.path, 'snapshots')
        good_snaps_folder = os.path.join(
            MANUAL_INSPECTION_OUTPUT_PATH,
            recording.name,
            'snapshots')

        if not os.path.exists(good_snaps_folder):
            print('Manually verified images for %s missing.' % recording.name)
            continue

        for snap in os.scandir(snapshots_folder):
            good_snap_path = os.path.join(good_snaps_folder, snap.name)

            if not os.path.exists(good_snap_path):
                continue

            image = Image.open(snap.path)
            good_image = Image.open(good_snap_path)

            diff_value = compare_images(image, good_image)

            if diff_value > 0.01:
                diffs_found += 1
                snap_meta, ext = os.path.splitext(snap.name)
                print('DIFFERENCE %s (>0.001) for "%s" in recording "%s"' %
                      (diff_value, snap_meta, recording.name))

                diff_folder = os.path.join(
                    DIFF_FOLDER, recording.name, snap_meta)

                if os.path.exists(diff_folder):
                    shutil.rmtree(diff_folder)

                os.makedirs(diff_folder, exist_ok=True)

                common_target_path = os.path.join(diff_folder, snap.name)
                target_path_good_img = (common_target_path + '_good' +
                                        SNAP_EXTENSION)

                shutil.copy(snap.path, common_target_path + SNAP_EXTENSION)
                shutil.copy(good_snap_path, target_path_good_img)


if __name__ == '__main__':
    main()
