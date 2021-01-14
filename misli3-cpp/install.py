#!/usr/bin/env python

import argparse
import os
import shutil

LOCAL = os.path.expanduser('~/.local')
LOCAL_BIN = os.path.join(LOCAL, 'bin')
LOCAL_LIB = os.path.join(LOCAL, 'lib')
LOCAL_APPS = os.path.join(LOCAL, 'share', 'applications')
ICONS_DIR = os.path.join(LOCAL, 'share', 'icons', 'hicolor', '256x256', 'apps')
SOURCE_PATH = './'

for path in [LOCAL, LOCAL_APPS, LOCAL_BIN, LOCAL_LIB, ICONS_DIR]:
    os.makedirs(path, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('build_dir', help='Location of the release build')
    parser.add_argument('--uninstall', action='store_true')

    args = parser.parse_args()
    build_dir = args.build_dir
    uninstall = args.uninstall

    if not os.path.exists(build_dir) or not os.path.isdir(build_dir):
        print('Invalid build dir')

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

    # Apply changes
    # Executable
    executable_path = os.path.join(build_dir, 'misli')
    executable_install_path = os.path.join(LOCAL_BIN, 'misli')
    apply(executable_path, executable_install_path)

    # Main libs
    main_libs = [f.path for f in os.scandir(build_dir)
                 if f.name.endswith('.o')]
    for ml in main_libs:
        target_path = os.path.join(LOCAL_LIB, os.path.basename(ml))
        apply(ml, target_path)

    # Desktop libs2
    desktop_dir = os.path.join(build_dir, 'misli_desktop')
    install_desktop_dir = os.path.join(LOCAL_LIB, 'misli_desktop')
    os.makedirs(install_desktop_dir, exist_ok=True)

    desktop_libs = [f.path for f in os.scandir(desktop_dir)
                    if f.name.endswith('.o')]

    for dl in desktop_libs:
        target_path = os.path.join(install_desktop_dir, os.path.basename(dl))
        apply(dl, target_path)

    # Icon
    icon_path = os.path.abspath(os.path.join(SOURCE_PATH, 'img/icon.png'))
    icon_install_path = os.path.join(ICONS_DIR, 'misli.png')
    apply(icon_path, icon_install_path)

    # Desktop entry
    desktop_entry = os.path.abspath(
        os.path.join(SOURCE_PATH, 'other/misli.desktop'))
    apply(desktop_entry, os.path.join(LOCAL_APPS, 'misli.desktop'))

    os.system('update-desktop-database ~/.local/share/applications')


if __name__ == '__main__':
    main()
