#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-


class PrefixView(object):
    def __init__(self, dct, prefix='', delim='.'):
        self.dct = dct
        self.prefix = prefix
        self.delim = delim

    def sub_view(self, name):
        return PrefixView(
            self.dct,
            prefix=self.build_key(name),
            delim=self.delim,
        )

    def build_key(self, name):
        return safe_join([self.prefix, name], self.delim)

    def strip_prefix(self, name):
        if not self.prefix:
            return name
        if name.startswith(self.prefix):
            name = name[len(self.prefix):]
        if name.startswith(self.delim):
            name = name[len(self.delim):]
        return name

    def __getitem__(self, name):
        return self.dct[self.build_key(name)]

    def __contains__(self, name):
        return self.build_key(name) in self.dct

    def __iter__(self):
        return self.keys()

    def __len__(self):
        return len(list(self.keys()))

    def __bool__(self):
        for k in self.keys():
            return True
        return False

    def get(self, name, default=None):
        return self.dct.get(self.build_key(name), default)

    def get_path(self, path, default=None):
        return self.get(safe_join(path), default)

    def keys(self):
        return (
            self.strip_prefix(k)
            for k in self.dct
            if k == self.prefix or (not self.prefix) or k.startswith(self.prefix + self.delim)
        )

    def items(self):
        return (
            (self.strip_prefix(k), v)
            for k, v in self.dct.items()
            if k == self.prefix or (not self.prefix) or k.startswith(self.prefix + self.delim)
        )

    def values(self):
        return (
            v
            for k, v in self.dct.items()
            if k == self.prefix or (not self.prefix) or k.startswith(self.prefix + self.delim)
        )

def safe_join(ss, delim='.'):
    stripped = [(s or '').strip(delim) for s in ss]
    return delim.join(s for s in stripped if s)


# V = TypeVar('V')
# class DictFilter(Generic[V], extra=MutableMapping[Text, V]):
#     def __init__(self, dct:MutableMapping[Text, V], prefix:Text='') -> None:
#         self.dct = dct
#         self.prefix = prefix or ''

#     def _name(self, name:Text) -> Text:
#         return self.prefix + name

#     def __getitem__(self, name:Text) -> V:
#         if not name.startswith(self.prefix):
#             raise KeyError(name)
#         return self.dct[name]

#     def __setitem__(self, name:Text, value:V) -> None:
#         if not name.startswith(self.prefix):
#             raise KeyError(name)
#         self.dct[name] = value

#     def __delitem__(self, name:Text) -> None:
#         if not name.startswith(self.prefix):
#             raise KeyError(name)
#         del self.dct[name]

#     def __contains__(self, name:Text) -> bool:
#         if not name.startswith(self.prefix):
#             return False
#         return name in self.dct

#     def __len__(self) -> int:
#         return (take_last(enumerate(self.keys(), 1)) or (0, 0))[0]

#     def __bool__(self) -> bool:
#         for k in self.keys():
#             return True
#         return False

#     def get(self, name: Text, default:Optional[V]=None) -> Optional[V]:
#         if not name.startswith(self.prefix):
#             return default
#         return self.dct.get(name, default)

#     def __iter__(self) -> Iterator[Text]:
#         skeys = (
#             (k, k.startswith(self.prefix))
#             for k in self.dct.keys()
#         )
#         return (
#             k
#             for k, stripped in skeys
#             if stripped
#         )

#     def keys(self) -> MutableSet[Text]:
#         return set(self)

#     def items(self) -> Iterable[Tuple[Text, V]]:
#         sitems = (
#             (k, k.startswith(self.prefix), v)
#             for k, v in self.dct.items()
#         )
#         return (
#             (k, v)
#             for k, stripped, v in sitems
#             if stripped
#         )

#     def values(self) -> Iterable[V]:
#         sitems = (
#             (k, k.startswith(self.prefix), v)
#             for k, v in self.dct.items()
#         )
#         return (
#             v
#             for k, stripped, v in sitems
#             if stripped
#         )
