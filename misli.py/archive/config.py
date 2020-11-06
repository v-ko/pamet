import configparser


# Това трябва да е отделен файл и да е JSON based
# освен това при пускане да поглежда за old style Config и
# да го импортва (ако няма нов)
class Config():
    def __init__(self, file_path):
        self._parser = configparser.ConfigParser()

        self._path = file_path
        self._parser.read(file_path)
        if 'General' not in self._parser.sections():
            self.add_section('General')

    def get(self, key):
        return self._parser['General'][key]

    def set(self, key, value):
        self._parser['General'][key] = value
        with open(self._parser.file_path, 'a') as cf:
            self._parser.write(cf)

