from typing import List, Dict, Tuple
import re


def _extract_numbers(part: str) -> Tuple[int, ...]:
    """
    Extract the integer(s) that appear at the end of *part*.

    The function splits *part* on the last hyphen and tries to parse the tail
    as an integer. If that fails (e.g. because there is no trailing number),
    it simply returns an empty tuple.

    Parameters
    ----------
    part : str
        A substring that ends with a hyphen‑separated number, e.g.
        'fa6055ab-5acc-4d04-bda8-098b0a7528e0-11'.

    Returns
    -------
    tuple[int, ...]
        A one‑element tuple containing the number.
    """
    # We use rsplit to keep everything after the final '-' character.
    suffix = part.rsplit('-', 1)[-1]
    try:
        return (int(suffix),)
    except ValueError:
        # If for some reason the suffix isn't numeric, return an empty key.
        return ()


def sort_by_trailing(s: str) -> Tuple[int, ...]:
    """
    Return a key that can be used to sort the string *s*.

    For strings of the form

        uuid-<id1>
        uuid-<id1>_uuid-<id2>

    the key is

        (int(id1), int(id2))    # if both parts are present
        (int(id1),)             # if only one part

    Parameters
    ----------
    s : str
        One element from the list you want to sort.

    Returns
    -------
    tuple[int, ...]
        The sort key.
    """
    if '_' in s:
        first, second = s.split('_', 1)
        n1 = _extract_numbers(first)
        n2 = _extract_numbers(second)
        # Combine into a tuple that sorts by first then second
        return n1 + n2
    else:
        return _extract_numbers(s)

def sort_identifiers(strings: List[str]) -> List[str]:
    """
    Return a new list sorted by the trailing number(s).

    Parameters
    ----------
    strings : list[str]
        The list to sort.

    Returns
    -------
    list[str]
        A new list, sorted in ascending order.
    """
    return sorted(strings, key=sort_by_trailing)

