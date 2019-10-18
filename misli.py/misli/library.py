#!/usr/bin/env python

import os
import sys
import argparse


class Config(object):

    def __init__(self, cfg_path=None):
        if cfg_path is None:  # Using default
            default_path = join(os.environ['HOME'], '.config', 'misli')

            if not os.path.exists(default_path):
                os.makedirs(default_path)

            self._cfg_path = join(default_path, 'config.json')

            if not os.path.exists(self._cfg_path):
                with open(self._cfg_path, 'w') as cfg:
                    json.dump({}, cfg)

        else:
            assert os.path.exists(cfg_path), \
                'No config file at the given path %s' % (cfg_path)

            self._cfg_path = cfg_path

    def _get_cfg(self):
        with open(self._cfg_path) as cfg_file:
            return json.load(cfg_file)

    def get(self, key):
        cfg = self._get_cfg()

        if key not in cfg:
            print('No key %s in %s' % (key, self._cfg_path))
            return None

        return cfg[key]

    def set(self, key, value): # timestamp=True
        cfg = self._get_cfg()
        cfg[key] = value

        with open(self._cfg_path, 'w') as cfg_file:
            json.dump(cfg, cfg_file)


class Libarary():
    def __init__(self):
        self.v = ""