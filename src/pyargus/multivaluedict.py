"""A ``dict`` subclass that preserves multiple values per key.

:class:`MultiValueDict` is intentionally free of any Argus-specific knowledge;
incident tags are merely its first consumer.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from typing import Any

# Sentinel distinguishing "no default supplied" from an explicit ``None`` default,
# used by :meth:`MultiValueDict.pop`.
_MISSING = object()


class MultiValueDict(dict):
    """A ``dict`` subclass that can hold more than one value per key.

    Modelled on Django's ``django.utils.datastructures.MultiValueDict``. The
    ``dict`` base always holds the *collapsed* view -- one value per key, the last
    one assigned (last wins) -- so ``isinstance(d, dict)``, item access,
    ``json.dumps(d)`` and ``dict(d)`` keep working exactly as for an ordinary
    dict. A parallel store keeps every value for each key, in insertion order,
    reachable through :meth:`getlist`, :meth:`lists`, :meth:`allitems`,
    :meth:`add`, :meth:`setlist`, :meth:`remove` and :meth:`poplist`.

    Unlike ``dict``, constructing from an iterable of ``(key, value)`` pairs with
    repeated keys keeps *all* the values::

        >>> d = MultiValueDict([("host", "a"), ("host", "b")])
        >>> d.getlist("host")
        ['a', 'b']
        >>> dict(d)
        {'host': 'b'}

    Reading a multi-valued key through the single-value interface (``d[key]`` or
    ``d.get(key)``) returns only the last value and emits a ``DeprecationWarning``,
    because the other values are silently dropped. Use :meth:`getlist` instead.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if len(args) > 1:
            raise TypeError(
                f"MultiValueDict expected at most 1 argument, got {len(args)}"
            )
        super().__init__()
        self._lists: dict[Any, list] = {}
        if args:
            self._merge(args[0], replace=False)
        for key, value in kwargs.items():
            self[key] = value

    def _merge(self, source: Any, replace: bool) -> None:
        """Fold ``source`` into this dict.

        With ``replace=False`` a pairs iterable appends every value (preserving
        repeated keys); with ``replace=True`` each pair assigns (last wins), to
        mirror ``dict.update``. Mappings always assign per key, and another
        ``MultiValueDict`` always contributes its full value lists.
        """
        if isinstance(source, MultiValueDict):
            for key, values in source.lists():
                self.setlist(key, values)
        elif hasattr(source, "keys"):
            for key in source.keys():
                self[key] = source[key]
        else:
            for key, value in source:
                if replace:
                    self[key] = value
                else:
                    self.add(key, value)

    # -- single-value (collapsed) interface -------------------------------------

    def __setitem__(self, key: Any, value: Any) -> None:
        # Replace semantics: assignment drops any prior values for the key.
        super().__setitem__(key, value)
        self._lists[key] = [value]

    def __getitem__(self, key: Any) -> Any:
        self._warn_if_lossy(key)
        return super().__getitem__(key)

    def get(self, key: Any, default: Any = None) -> Any:
        self._warn_if_lossy(key)
        return super().get(key, default)

    def __delitem__(self, key: Any) -> None:
        super().__delitem__(key)  # raises KeyError before we touch _lists
        del self._lists[key]

    def pop(self, key: Any, default: Any = _MISSING) -> Any:
        if key in self:
            value = super().__getitem__(key)  # collapsed last value, no warning
            super().__delitem__(key)
            del self._lists[key]
            return value
        if default is _MISSING:
            raise KeyError(key)
        return default

    def popitem(self) -> tuple:
        key, value = super().popitem()  # raises KeyError when empty
        del self._lists[key]
        return key, value

    def setdefault(self, key: Any, default: Any = None) -> Any:
        if key not in self:
            self[key] = default
        return super().__getitem__(key)  # collapsed last value, no warning

    def clear(self) -> None:
        super().clear()
        self._lists.clear()

    def update(self, *args: Any, **kwargs: Any) -> None:
        if len(args) > 1:
            raise TypeError(f"update expected at most 1 argument, got {len(args)}")
        if args:
            self._merge(args[0], replace=True)
        for key, value in kwargs.items():
            self[key] = value

    def _warn_if_lossy(self, key: Any) -> None:
        values = self._lists.get(key)
        if values is not None and len(values) > 1:
            warnings.warn(
                f"Key {key!r} has multiple values; single-value access returns "
                f"only the last. Use getlist({key!r}) to get all of them.",
                category=DeprecationWarning,
                stacklevel=3,  # point at the caller of __getitem__/get
            )

    # -- multi-value interface --------------------------------------------------

    def add(self, key: Any, value: Any) -> None:
        """Append ``value`` to the values stored under ``key``."""
        self._lists.setdefault(key, []).append(value)
        super().__setitem__(key, value)  # collapsed view tracks the last value

    def getlist(self, key: Any) -> list:
        """Return a copy of every value stored under ``key`` (``[]`` if absent)."""
        return list(self._lists.get(key, []))

    def setlist(self, key: Any, values: Iterable) -> None:
        """Replace all values under ``key``. An empty ``values`` removes the key."""
        values = list(values)
        if not values:
            if key in self:
                del self[key]
            return
        self._lists[key] = values
        super().__setitem__(key, values[-1])

    def lists(self) -> list:
        """Return ``[(key, [values...]), ...]`` in insertion order, with copies."""
        return [(key, list(values)) for key, values in self._lists.items()]

    def allitems(self) -> list:
        """Return every ``(key, value)`` pair, including repeats, in order.

        Unlike :meth:`items` (which yields the collapsed view, one value per
        key), this yields a separate pair for each stored value.
        """
        return [(key, value) for key, values in self._lists.items() for value in values]

    def poplist(self, key: Any) -> list:
        """Remove ``key`` and return all of its values (``KeyError`` if absent)."""
        values = self._lists.pop(key)  # raises KeyError before we touch the base
        super().__delitem__(key)
        return values

    def remove(self, key: Any, value: Any) -> None:
        """Remove a single occurrence of ``value`` from ``key``.

        Raises ``KeyError`` if the key is absent and ``ValueError`` if the value
        is not present. If it was the key's last value, the key is removed.
        """
        values = self._lists[key]
        values.remove(value)
        if values:
            super().__setitem__(key, values[-1])
        else:
            super().__delitem__(key)
            del self._lists[key]

    # -- copying, pickling, equality, repr --------------------------------------

    def copy(self) -> MultiValueDict:
        return MultiValueDict(self)

    @classmethod
    def fromkeys(cls, iterable: Iterable, value: Any = None) -> MultiValueDict:
        # Like ``dict.fromkeys``, every key shares the same ``value`` object.
        result = cls()
        for key in iterable:
            result[key] = value
        return result

    @classmethod
    def _from_lists(cls, items: Iterable) -> MultiValueDict:
        """Rebuild from the output of :meth:`lists`; used by ``__reduce_ex__``."""
        result = cls()
        for key, values in items:
            result.setlist(key, values)
        return result

    def __reduce_ex__(self, protocol: int) -> tuple:
        # Default dict pickling would rebuild only the collapsed base and drop the
        # extra values, so reconstruct from the full lists instead.
        return (self.__class__._from_lists, (self.lists(),))

    def __or__(self, other: Any) -> MultiValueDict:
        if not isinstance(other, dict):
            return NotImplemented
        result = self.copy()
        result.update(other)
        return result

    def __ror__(self, other: Any) -> MultiValueDict:
        if not isinstance(other, dict):
            return NotImplemented
        result = MultiValueDict(other)
        result.update(self)
        return result

    def __ior__(self, other: Any) -> MultiValueDict:
        self.update(other)
        return self

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MultiValueDict):
            return self._lists == other._lists
        return super().__eq__(other)  # compare the collapsed view to a plain dict

    def __ne__(self, other: object) -> bool:
        # dict supplies its own C-level __ne__ that ignores our __eq__, so it must
        # be overridden explicitly (it is not auto-derived for a dict subclass).
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    # Defining __eq__ already resets __hash__ to None; spell it out for clarity.
    __hash__ = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.allitems()!r})"
