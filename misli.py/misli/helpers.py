from misli import misli


def get_default_page():
    pass

def new_int_id(id_list):
    if id_list:
        new_id = id_list[-1] + 1
    else:
        new_id = 1

    if new_id in id_list:
        id_list = sorted(id_list)
        return new_int_id(id_list)
