#!/usr/bin/env python

import os
import sys
import argparse

from PySide2.QtWidgets import QApplication


class MisliApp(QApplication):
    def __init__(self, sys.argv):
        super().__init__(sys.argv)