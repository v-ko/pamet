import os
import json

from dataclasses import dataclass
from datetime import datetime

from misli.basic_classes import Point2D
from pamet.model import Page
from pamet.model.text_note import TextNote


def _convert_v3_to_v4(json_path):
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

        nt['page_id'] = name

    for i, nt in enumerate(notes):
        nt['id'] = str(nt['id'])
        nt['color'] = nt.pop('txt_col')
        nt['background_color'] = nt.pop('bg_col')
        nt['x'] = nt.pop('x')
        nt['y'] = nt.pop('y')
        nt['width'] = nt.pop('width')
        nt['height'] = nt.pop('height')
        nt['time_created'] = datetime.strptime(nt.pop('t_made'),
                                               '%m.%d.%Y %H:%M:%S')
        nt['time_modified'] = datetime.strptime(nt.pop('t_mod'),
                                                '%m.%d.%Y %H:%M:%S')

        # Redirect notes
        if nt['text'].startswith('this_note_points_to:'):
            nt['href'] = nt['text'].split(':', 1)[1]
            nt['text'] = nt['href']
            nt['type_name'] = 'Text'
            # nt['type_name'] = 'Redirect'

        else:
            nt['type_name'] = 'Text'

        # Remove unimplemented attributes to avoid errors
        note = TextNote(*nt)
        new_state = {}
        for key in nt:
            if hasattr(note, key):
                new_state[key] = nt[key]

        notes[i] = new_state

        # Testing
        # nt['class'] = 'Test'
        # if nt['id'] % 2 == 0:
        #     nt['font_size'] = 2

    note_states = {n['id']: n for n in json_object.pop('notes')}

    json_object['type_name'] = Page.__name__
    json_object['note_states'] = note_states

    return json_object


def _convert_v2_to_v4(file_path):
    # Example:
    # [79367]
    # txt=this_note_points_to:Програмиране
    # x=-7
    # y=-4.5
    # z=0
    # a=9
    # b=2.5
    # font_size=1
    # t_made=6.10.2019 14:1:12
    # t_mod=6.10.2019 14:1:12
    # txt_col=0;0;1;1
    # bg_col=0;0;1;0.100008
    # l_id=
    # l_txt=
    # l_CP_x=
    # l_CP_y=
    # tags=

    # Ignored fields: font_size, z (unused)

    with open(file_path) as misl_file:
        misl_file_string = misl_file.read()

    is_displayed_first_on_startup = False
    is_a_timeline_notefile = False

    # Clear the windows standart junk
    misl_file_string = misl_file_string.replace('\r', '')
    lines = [ln for ln in misl_file_string.split('\n') if ln]  # Skip empty

    lines_left = []
    for line in lines:
        if line.startswith('#'):  # Skip comments
            continue

        if line.startswith('is_displayed_first_on_startup'):
            is_displayed_first_on_startup = True
            continue

        elif line.startswith('is_a_timeline_note_file'):
            is_a_timeline_notefile = True

        lines_left.append(line)

    @dataclass
    class Arrow:
        source_id: str
        target_id: str
        control_point: Point2D

    # Extract groups
    notes = {}
    current_note_id = None
    arrows = []  # source, target, control_point

    for line in lines_left:
        if line.startswith('[') and line.endswith(']'):
            current_note_id = line[1:-1]
            continue

        [key, value] = line.split('=', 1)

        if key == 'txt':
            value = value.replace('\\n', '\n')
        elif key in ['txt_col', 'bg_col']:
            value = [float(channel) for channel in value.split(';')]
        elif key in ['l_id', 'l_CP_x', 'l_CP_y']:
            value = value.split(';')

        notes[current_note_id][key] = value

    for note_id, nt in notes.items():
        # Pop unused values
        nt.pop('font_size', '')
        nt.pop('z', '')

        nt['id'] = int(note_id)
        nt['color'] = nt.pop('txt_col')
        nt['background_color'] = nt.pop('bg_col')
        nt['x'] = float(nt.pop('x'))
        nt['y'] = float(nt.pop('y'))
        nt['width'] = float(nt.pop('a'))
        nt['height'] = float(nt.pop('b'))
        nt['text'] = nt.pop('txt')
        nt['time_created'] = datetime.strptime(nt.pop('t_made'),
                                               '%m.%d.%Y %H:%M:%S')
        nt['time_modified'] = datetime.strptime(nt.pop('t_mod'),
                                                '%m.%d.%Y %H:%M:%S')
        # nt['tags'] unchanged

        # Process arrows (formerly named links)
        control_points = []
        if 'l_CP_x' in nt and 'l_CP_y' in nt:
            for cp_x, cp_y in zip(nt['l_CP_x'], nt['l_CP_y']):
                control_points.append(Point2D(cp_x, cp_y))
        else:
            control_points = None

        for arrow_idx, target_id in enumerate(nt['l_id']):
            if control_points:
                control_point = control_points[arrow_idx]
            else:
                control_point = None

            arrows.append(Arrow(nt['id'], target_id, control_point))

