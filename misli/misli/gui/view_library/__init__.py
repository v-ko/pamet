_views_by_class_name = {}
_view_metadata_by_class_name = {}

CLASS_NAME = 'class_name'


def register_view_type(_cls=None, **view_metadata):
    """Register a view in the library. The metadata can be used later for
    querying the view library. It can not include a 'class_name', since that's
    automatically added to the metadata on registration.
    """

    if CLASS_NAME in view_metadata:
        raise Exception('view_metadata cannot include a \'class_name\'.'
                        ' That\'s inferred by calling type(cls)')

    def view_registration_decorator(cls):
        class_name = cls.__name__
        view_metadata[CLASS_NAME] = class_name

        _views_by_class_name[class_name] = cls
        _view_metadata_by_class_name[class_name] = view_metadata

        return cls

    if _cls is None:
        return view_registration_decorator
    else:
        return view_registration_decorator(_cls)


def get_view_classes(**metadata_filter) -> list:
    """Get a list of view classes matching the specified metadata criteria.

    Keyword arguments:
        Each key/value pair in the kwargs has to match a respective pair
        in the metadata that a view is registered with, so that view is
         included in the list that get_views returns.

    Returns:
        list: The matching view classes
    """

    metas_found = []

    for class_name, meta in _view_metadata_by_class_name.items():
        if metadata_filter.items() <= meta.items():  # True if is subset
            metas_found.append(meta)

    vcs_found = [_views_by_class_name[meta[CLASS_NAME]] for meta in metas_found]
    return vcs_found


def get_view_class(class_name: str = '', **metadata_filter):
    """Get a view class either by specifying the class_name or by querying the
    library for a view matching the criteria in metadata_filter.

    Args:
        class_name (str, optional): The class name to match by (empty=skip)

    Raises:
        Exception: If there's no results or more than one match.

    Returns:
        A view class
    """

    if class_name:
        metadata_filter[CLASS_NAME] = class_name

    views_found = get_view_classes(**metadata_filter)

    if len(views_found) != 1:
        raise Exception(f'!=1 views found for metadata_filter: '
                        f'{metadata_filter}: {views_found}')

    return views_found[0]
