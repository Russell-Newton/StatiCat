import json

from typing_extensions import SupportsIndex


def is_jsonable(item):
    try:
        json.dumps(item)
        return True
    except TypeError or OverflowError:
        return False


class NotSavableError(Exception):
    pass


class CallbackOnUpdateDict(dict):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback

    def __setitem__(self, k, v):
        if not is_jsonable(v):
            raise NotSavableError(f"Object {v} cannot be saved in a file, and will not be added.")
        super().__setitem__(k, v)
        self.callback()

    def __delitem__(self, v):
        super().__delitem__(v)
        self.callback()

    def clear(self) -> None:
        super().clear()
        self.callback()

    def popitem(self):
        rtn = super().popitem()
        self.callback()
        return rtn

    def update(self, *args, **kwargs) -> None:
        super().update(*args, **kwargs)
        self.callback()


class CallbackOnUpdateList(list):
    def __init__(self, callback, *args):
        super().__init__(*args)
        self.callback = callback

    def __setitem__(self, *args, **kwargs) -> None:
        super().__setitem__(*args, **kwargs)
        self.callback()

    def __delitem__(self, i) -> None:
        super().__delitem__(i)
        self.callback()

    def clear(self) -> None:
        super().clear()
        self.callback()

    def append(self, __object):
        if not is_jsonable(__object):
            raise NotSavableError(f"Object {__object} cannot be saved in a file, and will not be added.")
        super().append(__object)
        self.callback()

    def pop(self, __index: SupportsIndex = ...):
        rtn = super().pop(__index)
        self.callback()
        return rtn

    def insert(self, __index: SupportsIndex, __object):
        if not is_jsonable(__object):
            raise NotSavableError(f"Object {__object} cannot be saved in a file, and will not be added.")
        super().insert(__index, __object)
        self.callback()

    def remove(self, __value):
        super().remove(__value)
        self.callback()

    def reverse(self):
        super().reverse()
        self.callback()

    def sort(self, **kwargs) -> None:
        super().sort(**kwargs)
        self.callback()


class AutoSavingDict(dict):
    def __init__(self, data_file_location: str):
        self.data_file_location = data_file_location
        self._prepped = False
        super().__init__(**self._get_data())
        self._prepped = True

    def _recurse_convert_list(self, raw: list) -> list:
        converted = CallbackOnUpdateList(self.update_data_file)
        for v in raw:
            if isinstance(v, list):
                converted.append(self._recurse_convert_list(v))
            elif isinstance(v, dict):
                converted.append(self._recurse_convert_dict(v))
            else:
                converted.append(v)
        return converted

    def _recurse_convert_dict(self, raw: dict) -> dict:
        converted = CallbackOnUpdateDict(self.update_data_file)
        for k, v in raw.items():
            if isinstance(v, list):
                converted[k] = self._recurse_convert_list(v)
            elif isinstance(v, dict):
                converted[k] = self._recurse_convert_dict(v)
            else:
                converted[k] = v
        return converted

    def __setitem__(self, k, v):
        if not is_jsonable(v):
            raise NotSavableError(f"Object {v} cannot be saved in a file, and will not be added.")
        if isinstance(v, dict):
            v = self._recurse_convert_dict(v)
        if isinstance(v, list):
            v = self._recurse_convert_list(v)
        super().__setitem__(k, v)
        self.update_data_file()

    def __delitem__(self, v):
        super().__delitem__(v)
        self.update_data_file()

    def clear(self) -> None:
        super().clear()
        self.update_data_file()

    def popitem(self):
        rtn = super().popitem()
        self.update_data_file()
        return rtn

    def update(self, *args, **kwargs) -> None:
        super().update(*args, **kwargs)
        self.update_data_file()

    def _get_data(self) -> dict:
        """
        Save the contents of the json data_file to self.data.
        """
        try:
            with open(self.data_file_location, 'r') as file:
                data_raw: dict = json.load(file)
            return self._recurse_convert_dict(data_raw)

        except FileNotFoundError:
            with open(self.data_file_location, 'w') as file:
                # print("Making {}".format(self.data_file_location))
                file.write("{}")
            return self._get_data()

    def update_data_file(self) -> None:
        """
        Save the contents of self.data to the json data_file.
        """
        if not self._prepped:
            return
        with open(self.data_file_location, 'w') as file:
            json.dump(self, file)
