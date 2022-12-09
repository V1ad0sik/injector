import os
from importlib.util import find_spec
from ctypes import CDLL, Structure, POINTER, c_int32, byref, c_char_p
from typing import AnyStr, Callable, Any, Mapping, Type, Optional

libinjector_path = find_spec('.libinjector', __package__).origin
libinjector = CDLL(libinjector_path)

injector_t = type('injector_t', (Structure,), {})
injector_pointer_t = POINTER(injector_t)
pid_t = c_int32

libinjector.injector_attach.argtypes = POINTER(injector_pointer_t), pid_t
libinjector.injector_attach.restype = c_int32
libinjector.injector_inject.argtypes = injector_pointer_t, c_char_p
libinjector.injector_inject.restype = c_int32
libinjector.injector_detach.argtypes = injector_pointer_t,
libinjector.injector_detach.restype = c_int32
libinjector.injector_error.argtypes = ()
libinjector.injector_error.restype = c_char_p


class PyInjectorError(Exception):
    pass


class LibraryNotFoundException(PyInjectorError):
    def __init__(self, path: bytes):
        self.path = path

    def __str__(self):
        return f'Could not find library: {self.path}'


class InjectorError(PyInjectorError):
    def __init__(self, func_name: str, ret_val: int, error_str: Optional[bytes]):
        self.func_name = func_name
        self.ret_val = ret_val
        self.error_str = error_str.decode()

    def __str__(self):
        explanation = 'see error code definition in injector/include/injector.h' \
            if self.error_str is None else self.error_str
        return '{} returned {}: {}'.format(self.func_name, self.ret_val, explanation)


class InjectorPermissionError(InjectorError):
    def __str__(self):
        return (super().__str__()


def call_c_func(func: Callable[..., int], *args: Any,
                exception_map: Mapping[int, Type[InjectorError]] = None) -> None:
    ret = func(*args)
    if ret != 0:
        exception_map = {} if exception_map is None else exception_map
        exception_cls = exception_map.get(ret, InjectorError)
        raise exception_cls(func.__name__, ret, libinjector.injector_error())


class Injector:
    def __init__(self, injector_p: injector_pointer_t):
        self.injector_p = injector_p

    @classmethod
    def attach(cls, pid: int) -> 'Injector':
        assert isinstance(pid, int)
        injector_p = injector_pointer_t()
        call_c_func(libinjector.injector_attach, byref(injector_p), pid,
                    exception_map={-8: InjectorPermissionError})
        return cls(injector_p)

    def inject(self, library_path: AnyStr) -> None:
        if isinstance(library_path, str):
            library_path = library_path.encode()
        assert isinstance(library_path, bytes)
        assert os.path.isfile(library_path), f'Library not found at "{library_path.decode()}"'
        call_c_func(libinjector.injector_inject, self.injector_p, library_path)

    def detach(self) -> None:
        call_c_func(libinjector.injector_detach, self.injector_p)


def inject(pid: int, library_path: AnyStr) -> None:
    if not os.path.isfile(library_path):
        raise LibraryNotFoundException(library_path)
    injector = Injector.attach(pid)
    try:
        injector.inject(library_path)
    finally:
        injector.detach()
