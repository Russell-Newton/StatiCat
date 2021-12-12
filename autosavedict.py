import json
from typing import overload

from typing_extensions import SupportsIndex


def is_jsonable(item):
    try:
        json.dumps(item)
        return True
    except TypeError or OverflowError:
        return False


class NotSavableError(Exception):
    pass


def _recurse_convert_list(callback, raw: list) -> list:
    converted = CallbackOnUpdateList(callback)
    for v in raw:
        if isinstance(v, list):
            converted.append(_recurse_convert_list(callback, v))
        elif isinstance(v, dict):
            converted.append(_recurse_convert_dict(callback, v))
        else:
            converted.append(v)
    return converted

def _recurse_convert_dict(callback, raw: dict) -> dict:
    converted = CallbackOnUpdateDict(callback)
    for k, v in raw.items():
        if isinstance(v, list):
            converted[k] = _recurse_convert_list(callback, v)
        elif isinstance(v, dict):
            converted[k] = _recurse_convert_dict(callback, v)
        else:
            converted[k] = v
    return converted


class CallbackOnUpdateDict(dict):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback

    def __setitem__(self, k, v):
        if not is_jsonable(v):
            raise NotSavableError(f"Object {v} cannot be saved in a file, and will not be added.")
        if isinstance(v, dict):
            v = _recurse_convert_dict(self.callback, v)
        if isinstance(v, list):
            v = _recurse_convert_list(self.callback, v)
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
        raise NotImplementedError("Please use the other methods for this :)")


class CallbackOnUpdateList(list):
    def __init__(self, callback, *args):
        super().__init__(*args)
        self.callback = callback

    @overload
    def __setitem__(self, i: SupportsIndex, o) -> None: ...

    @overload
    def __setitem__(self, s: slice, o) -> None: ...

    def __setitem__(self, i: SupportsIndex, o) -> None:
        if not is_jsonable(o):
            raise NotSavableError(f"Object {o} cannot be saved in a file, and will not be added.")
        if isinstance(o, dict):
            o = _recurse_convert_dict(self.callback, o)
        if isinstance(o, list):
            o = _recurse_convert_list(self.callback, o)
        super().__setitem__(i, o)

    def __delitem__(self, i) -> None:
        super().__delitem__(i)
        self.callback()

    def clear(self) -> None:
        super().clear()
        self.callback()

    def append(self, __object):
        if not is_jsonable(__object):
            raise NotSavableError(f"Object {__object} cannot be saved in a file, and will not be added.")
        if isinstance(__object, dict):
            __object = _recurse_convert_dict(self.callback, __object)
        if isinstance(__object, list):
            __object = _recurse_convert_list(self.callback, __object)
        super().append(__object)
        self.callback()

    def pop(self, __index: SupportsIndex = ...):
        rtn = super().pop(__index)
        self.callback()
        return rtn

    def insert(self, __index: SupportsIndex, __object):
        if not is_jsonable(__object):
            raise NotSavableError(f"Object {__object} cannot be saved in a file, and will not be added.")
        if isinstance(__object, dict):
            __object = _recurse_convert_dict(self.callback, __object)
        if isinstance(__object, list):
            __object = _recurse_convert_list(self.callback, __object)
        super().insert(__index, __object)
        self.callback()

    def remove(self, __value):
        super().remove(__value)
        self.callback()

    def reverse(self):
        super().reverse()
        self.callback()

    @overload
    def sort(self, *, key: None = ..., reverse: bool = ...) -> None: ...

    @overload
    def sort(self, *, key, reverse: bool = ...) -> None: ...

    def sort(self, *, key: None = ..., reverse: bool = ...) -> None:
        super().sort(key=key, reverse=reverse)
        self.callback()


class AutoSavingDict(dict):
    def __init__(self, data_file_location: str):
        self.data_file_location = data_file_location
        self._prepped = False
        super().__init__(**self._get_data())
        self._prepped = True

    def __setitem__(self, k, v):
        if not is_jsonable(v):
            raise NotSavableError(f"Object {v} cannot be saved in a file, and will not be added.")
        if isinstance(v, dict):
            v = _recurse_convert_dict(self.update_data_file, v)
        if isinstance(v, list):
            v = _recurse_convert_list(self.update_data_file, v)
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
            return _recurse_convert_dict(self.update_data_file, data_raw)

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
