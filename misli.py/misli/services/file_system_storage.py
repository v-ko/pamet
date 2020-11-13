import os
import json
from misli.objects import Repository, Page, Note

import random
import string

example_nf = '/sync/misli/ИИ.json'
RANDOMIZE_TEXT = False


class FSStorageBackend(Repository):
    def __init__(self):
        self.pages = {}
        mock_page = self.convert_v3_to_v4(example_nf)
        self.pages[mock_page.id] = mock_page

    @classmethod
    def open(cls, repo_path):
        repo = cls()
        # Регистрираш първо репото (лоудва му се стейта от system.page.json)
        # Може да преместиш от там да зарежда и десктоп сетингите (др записка)
        # После адваш страниците в SM маркирани с това репо

        # for file in os.scandir(repo_path): това е за в Репозиторъ
        #     if self.is_page_json(file_path):
        return repo

    def page(self, page_id):
        if page_id not in self.pages:
            return None

        return self.pages[page_id]

    def is_page_json(self, file_path):
        if file_path.endswith('.page.json') and os.path.isfile(file_path):
            return True

        return False

    def catch_legacy_version(self, file_path):
        fname = os.path.basename(file_path)
        name, ext = os.path.splitext(fname)
        version = 0

        if ext == 'json':
            version = 3
        elif ext == 'misl':
            version = 1

        return version

    def convert_v3_to_v4(self, json_path):
        # V3 example: {"notes": [
        # {"bg_col": [0,0,1,0.1],
        #     "font_size": 1,
        #     "height": 3,
        #     "id": 1,
        #     "links": [],
        #     "t_made": "10.4.2019 14:2:2",
        #     "t_mod": "10.4.2019 14:2:2",
        #     "tags": [],
        #     "text": "this_note_points_to:notes",
        #     "txt_col": [0,0,1,1],
        #     "width": 11,
        #     "x": 1,
        #     "y": -2.5}]}

        json_object = json.load(open(json_path))

        fname = os.path.basename(json_path)
        name, ext = os.path.splitext(fname)
        json_object['id'] = name

        ONE_V3_COORD_UNIT_TO_V4 = 20

        notes = json_object['notes']

        # Scale old coords by 10 so that default widget fonts
        # look adequate without correction
        for nt in notes:
            for coord in ['x', 'y', 'width', 'height']:
                nt[coord] = nt[coord] * ONE_V3_COORD_UNIT_TO_V4

            nt['font_size'] = nt['font_size']  # * DEFAULT_FONT_SIZE

        for nt in notes:
            if RANDOMIZE_TEXT:
                text = nt['text']
                words = text.split()

                for i, word in enumerate(words):
                    new_word = []
                    for c in word:
                        new_word.append(random.choice(string.ascii_letters))

                    words[i] = ''.join(new_word)
                text = ' '.join(words)
                # print(text)
                nt['text'] = text

        for nt in notes:
            # Redirect notes
            if nt['text'].startswith('this_note_points_to:'):
                nt['href'] = nt['text'].split(':', 1)[1]
                nt['text'] = nt['href']
                nt['obj_type'] = 'Redirect'

            else:
                nt['obj_type'] = 'Text'

            # Testing
            # nt['class'] = 'Test'
            # if nt['id'] % 2 == 0:
            #     nt['font_size'] = 2

        json_object['notes'] = [Note(**n) for n in notes]

        return Page(**json_object)

    # def defaultCanvas(self):
    #     cv = json.load(open(example_nf))
    #     cv = self.convertCanvasFromV3toV4(cv)
    #     return Canvas(cv)
