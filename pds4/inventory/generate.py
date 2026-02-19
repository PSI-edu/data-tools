#! /usr/bin/env python3
"""Generate a PDS4 inventory for all of the basic products in a directory"""

import multiprocessing

import argparse
import logging
from typing import Iterable, Callable, Union
from multiprocessing import pool
from functools import partial

import inventory


def main() -> None:
    """
    Generates the inventory
    """
    parser = build_parser()

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING
        if args.quiet
        else logging.DEBUG
        if args.debug
        else logging.INFO,
        format="%(asctime)s;%(levelname)s;%(name)s; %(message)s",
        filename=args.logfile,
    )

    p = pool.Pool(processes=args.processes) if args.processes > 1 else None
    inv = build_inventory(
        args.dirname,
        args.deep_product_check,
        args.tolerant,
        p,
    )
    write_inventory(inv, args.crlf, args.outfilepath)


def build_parser() -> argparse.ArgumentParser:
    """
    Create an argument parser for the program.
    """
    parser = argparse.ArgumentParser(
        description="Generate a PDS4 inventory for all of the basic products in a directory"
    )
    parser.add_argument(
        "outfilepath", help="Write the inventory to the specified file."
    )
    parser.add_argument("dirname", help="Traverse the given directory for products.")
    parser.add_argument(
        "--deep-product-check",
        action="store_true",
        help="Check for basic products by parsing the label instead of using the filename. "
        "May decrease performance.",
    )
    parser.add_argument(
        "--logfile", help="Log to the specified file instead of the console."
    )
    parser.add_argument(
        "--debug", action="store_true", help="More detailed log output."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Less detailed log output, report problems only.",
    )
    parser.add_argument(
        "--tolerant",
        action="store_true",
        help="Keep parsing products even if some are invalid. "
        "Invalid entries may appear in the inventory file.",
    )
    parser.add_argument(
        "--crlf", action="store_true", help="Use CRLF line terminators instead of LF."
    )
    parser.add_argument(
        "--processes",
        type=int,
        default=1,
        help="Split the task among the specified number of processes. May increase performance.",
    )
    return parser


def build_inventory(
    dirname: str,
    deep: bool,
    tolerant: bool,
    pool_: multiprocessing.pool.Pool | None,
) -> Iterable[str]:
    """
    Create an inventory for all of the basic products located in the specified directory.
    """
    filenames = peeks(get_filenames(dirname, pool_, deep), logging.DEBUG)
    lidvids = peeks(get_lidvids(filenames, pool_, tolerant), logging.INFO)
    return (f"P,{lidvid}" for lidvid in lidvids)


def write_inventory(inv: Iterable[str], crlf: bool, outfilename: str) -> None:
    """
    Write the output to the specified destination.
    """
    sep = "\r\n" if crlf else "\n"

    with open(outfilename, "w", encoding="utf-8") as f:
        f.write(f"{sep.join(sorted(inv))}{sep}")


def get_filenames(
    dirname: str, pool_: multiprocessing.pool.Pool | None, deep: bool
) -> Iterable[str]:
    """
    Get the filenames for all of the basic products located in the given directory
    """
    filenames = inventory.get_all_product_filenames(dirname)
    func = partial(squelch_collections, deep=deep)
    return (x for x in do_map(func, filenames, pool_) if x is not None)


def squelch_collections(filename: str, deep: bool) -> Union[str, None]:
    """
    Convert the filenames for collections in the provided list to none.
    This is kind of a hack because multiprocessing doesn't directly support
    filtering.
    """
    if inventory.is_basic_product(filename, deep=deep):
        return filename
    return None


def get_lidvids(
    filenames: Iterable[str], pool_: multiprocessing.pool.Pool | None, tolerant: bool
) -> Iterable[str]:
    """
    Get all of the LIDVIDs declared in the list of filenames.
    """
    func = partial(inventory.extract_lidvid, tolerant=tolerant)
    return do_map(func, filenames, pool_)


def do_map(
    func: Callable[[str], str], items: Iterable[str], pool_: multiprocessing.pool.Pool | None
) -> Iterable[str]:
    """
    This is a "multiprocessing-optional" version of unordered_map. If no multiprocessing pool is
    provided, then just do a standard generator comprehension.
    """
    if pool_ is None:
        return (func(x) for x in items)
    return pool_.imap_unordered(func, items, 1024)


def peeks(items: Iterable[str], level: int) -> Iterable[str]:
    """
    Log and return all of the values in the specified "list".
    """
    return (peek(x, level) for x in items)


def peek(x: str, level: int) -> str:
    """
    Log and return a single value, at the specified log level.
    """
    logging.log(level, x)
    return x


if __name__ == "__main__":
    main()
