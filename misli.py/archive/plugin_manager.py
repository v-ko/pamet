import os
import inspect
import importlib
import logging

class PluginManager(object):
    def __init__(self):
        self.noteWidgetPlugins = {}

    def loadPluginsFromModule(self, module):
        # Load NoteWidget plugins
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if name.endswith('NoteWidget'):
                self.noteWidgetPlugins[name] = cls

        # load other types of plugins..

    def loadPluginsFolder(self, folder):
        logging.info('Loading plugins from folder ', folder)

        for file in os.scandir(folder):
            logging.info('Loading plugin from file ', file.name)
            module = importlib.import_module(file.path)
            self.loadPluginsFromModule(module)
