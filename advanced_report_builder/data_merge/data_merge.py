class DataMerge:

    # def __init__(self, *args):
    #     self._data_merge_objects = []
    #     for a in args:
    #         if isinstance(a, DataMergeObject):
    #             self._data_merge_objects.append(a)
    #         elif type(a) == tuple:
    #             self._data_merge_objects.append(DataMergeObject(*a))
    #         else:
    #             if hasattr(a, 'data_merge_objects'):
    #                 if callable(a):
    #                     data_merge_objects = a().data_merge_objects()
    #                 else:
    #                     data_merge_objects = a.data_merge_objects()
    #                 if isinstance(data_merge_objects, Iterable):
    #                     for data_merge_object in data_merge_objects:
    #                         self._data_merge_objects.append(data_merge_object)
    #                 else:
    #                     self._data_merge_objects.append(data_merge_objects)
    #             else:
    #                 self._data_merge_objects.append(DataMergeObject(model_instance=a))

    def build_menus(self):
        menu = []
        # for _data_merge_object in self._data_merge_objects:
        #     data_merge_menu = getattr(_data_merge_object.get_object(), 'data_merge', None)
        #
        #     if data_merge_menu is not None:
        #         menu.append(data_merge_menu().get_dict(prefix=_data_merge_object.prefix,
        #                                                code=_data_merge_object.code,
        #                                                name=_data_merge_object.name))

        return menu

