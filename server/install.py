#!/usr/bin/env python

import argparse
import os
from pathlib import Path
import shutil

LOCAL = os.path.expanduser('~/.local')
LOCAL_BIN = os.path.join(LOCAL, 'bin')
LOCAL_LIB = os.path.join(LOCAL, 'lib')
LOCAL_APPS = os.path.join(LOCAL, 'share', 'applications')
ICONS_DIR = os.path.join(LOCAL, 'share', 'icons', 'hicolor', '256x256', 'apps')
SOURCE_PATH = Path(__file__).parent
PAMET_RESOURCES_PATH = SOURCE_PATH / 'pamet' / 'resources'

for path in [LOCAL, LOCAL_APPS, LOCAL_BIN, LOCAL_LIB, ICONS_DIR]:
    os.makedirs(path, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    # parser.add_argument('build_dir', help='Location of the release build')
    parser.add_argument('--uninstall', action='store_true')

    args = parser.parse_args()
    # build_dir = args.build_dir
    uninstall = args.uninstall

    # if not os.path.exists(build_dir) or not os.path.isdir(build_dir):
    #     print('Invalid build dir')

    def apply(build_path, install_path):
        if uninstall:
            if not os.path.exists(install_path):
                print('Missing file at install path', install_path)
                return

            print('Removing', install_path)
            os.remove(install_path)
        else:
            if os.path.lexists(install_path):
                print('Removing existing file at install path', install_path)
                os.remove(install_path)

            print('Copying %s to %s' % (build_path, install_path))
            shutil.copy(build_path, install_path)

    # Icon
    icon_path = PAMET_RESOURCES_PATH / 'icons' / 'pamet-icon.png'
    icon_install_path = os.path.join(ICONS_DIR, 'pamet.png')
    apply(icon_path, icon_install_path)

    # Desktop entry
    desktop_entry = PAMET_RESOURCES_PATH / 'desktop_entries' / 'pamet.desktop'
    apply(desktop_entry, os.path.join(LOCAL_APPS, 'pamet.desktop'))

    os.system('update-desktop-database ~/.local/share/applications')


if __name__ == '__main__':
    main()
