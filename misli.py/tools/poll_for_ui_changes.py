#!/usr/bin/env python

import os
import argparse
import subprocess
import time
from collections import defaultdict


def output_path(ui_path):
    folder = os.path.dirname(ui_path)
    file_name = os.path.basename(ui_path)
    name, ext = os.path.splitext(file_name)

    return os.path.join(folder, 'ui_' + name + '.py')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', help="Folder to watch")

    args = parser.parse_args()

    folder_path = args.folder

    if not os.path.exists(folder_path):
        print('No such path')
        return

    if not os.path.isdir(folder_path):
        print('Given path is not a folder')
        return

    ui_files_tmod = defaultdict(float)

    def pollAndGenerate(verbose=False):
        updated_count = 0

        for r, d, files in os.walk(folder_path):

            for f in files:
                f_path = os.path.join(r, f)

                if not os.path.isfile(f_path) or not f.endswith('.ui'):
                    continue

                tmod = os.path.getmtime(f_path)

                if tmod == ui_files_tmod[f_path]:
                    continue

                command = ['pyside2-uic', f_path]
                result = subprocess.run(command, stdout=subprocess.PIPE)
                output = result.stdout.decode('utf-8')

                out_path = output_path(f_path)
                with open(out_path, 'w') as of:
                    of.write(output)

                ui_files_tmod[f_path] = tmod

                updated_count += 1

                if verbose:
                    print('Updated %s' % out_path)

        return updated_count

    # Start doing stuff
    count = pollAndGenerate()
    print('Found and updated %s ui files' % count)

    while True:
        try:
            pollAndGenerate(verbose=True)
            time.sleep(2)
        except KeyboardInterrupt:
            print('\nTerminated by user. Exiting.')
            break


if __name__ == '__main__':
    main()
