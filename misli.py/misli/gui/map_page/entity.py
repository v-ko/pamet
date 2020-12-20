from misli.entities import Page


class MapPage(Page):
    def __init__(self, **props):
        id = props.pop('id', None)
        Page.__init__(self, id=id, obj_class='MapPage')
