"""Functions for local file import/export operations, e. g. CSV file reading and writing."""
import os
from multiprocessing.dummy import Pool as ThreadPool
from typing import Union
import logging

import pandas as pd

from scrawler.defaults import DEFAULT_CSV_ENCODING, DEFAULT_CSV_SEPARATOR, DEFAULT_CSV_QUOTING, DEFAULT_CSV_ESCAPECHAR


def export_to_csv(data, directory: str, fn: str, header: Union[list, str, bool] = None,
                  encoding: str = DEFAULT_CSV_ENCODING, separator: str = DEFAULT_CSV_SEPARATOR,
                  quoting: int = DEFAULT_CSV_QUOTING, escapechar: str = DEFAULT_CSV_ESCAPECHAR,
                  current_index: int = None, **kwargs) -> None:
    """Export data to a CSV file.

    :param data: One- or two-dimensional data that will be parsed to a :class:`pandas:pandas.DataFrame`.
    :param directory: Path to directory where file will be saved.
    :param fn: Filename (*without* file extension).
    :param header: If ``None`` or ``False``, no header will be written.
        If ``first-row`` or ``True``, uses first row of data as header.
        Else, pass list of strings of appropriate length.
    :param encoding: Encoding to use to create the CSV file.
    :param separator: Column separator or delimiter to use for creating the CSV file.
    :param quoting: Puts quotes around cells that contain the separator character.
    :param escapechar: Escapes the separator character.
    :param current_index: If ``fn`` is a list of filenames, use this to specify which filename to use.
    :param kwargs: Any parameter supported by :meth:`pandas:pandas.DataFrame.to_csv` can be passed.
    """
    if type(fn) is not str and current_index is not None:
        fn = fn[current_index]
    filepath = f"{directory}/{fn}.csv"

    write_index = False
    write_columns = False if (header is None) else True

    if data is None or len(data) == 0:    # TODO maybe raise ValueError instead?
        logging.error("Can't export empty dataset.")
        return

    if not isinstance(data[0], (list, tuple, set)):  # if data consists of just one data point, wrap into another list so that Pandas correctly parses it into multiple columns
        data = [data]

    if (header is None) or (header is False):
        container = pd.DataFrame(data)
    elif (header == "first-row") or (header is True):
        container = pd.DataFrame(data[1:], columns=data[0])
    else:
        container = pd.DataFrame(data, columns=header)

    container.to_csv(filepath, encoding=encoding, sep=separator,
                     header=write_columns, index=write_index,
                     quoting=quoting, escapechar=escapechar, **kwargs)

    logging.info(f"Data exported to {filepath}.")


def multithreaded_csv_export(list_of_datasets: list, **kwargs) -> None:
    """Export a list of multi-column dataset to a CSV file in parallel using ``multithreading``.

    :param list_of_datasets: List of two-dimensional data objects that will be parsed to a :class:`pandas:pandas.DataFrame`.
    :param kwargs: Keywords arguments that are passed on to :func:`.export_to_csv`.
    """
    # Prepare argument list
    args = list(enumerate(list_of_datasets))

    # Define function with constant parameters pre-filled
    def do_export(index, data):
        return export_to_csv(data, current_index=index, **kwargs)

    # Map function for multi-threading
    pool = ThreadPool()
    pool.starmap(do_export, args)
    pool.close()
    pool.join()


def get_data_in_dir(directory: str,
                    start_idx: int = 0, end_idx: int = None,
                    encoding: str = DEFAULT_CSV_ENCODING, separator: str = DEFAULT_CSV_SEPARATOR) -> list:
    """Read all CSV files within a directory. All files in the directory must be CSV files.

    :param directory: Path to the directory.
    :param start_idx: Sometimes, not all CSV files in the directory should be read. Together with ``end_idx``, this
        parameter allows to specify an interval of files that should be read in, e. g. the first up to the 5th file.
    :param end_idx: See ``start_idx``.
    :param encoding: The character encoding of the CSV files to be read.
    :param separator: The separator/delimiter of the CSV files to be read.
    """
    filenames = os.listdir(directory)
    end_idx = end_idx if end_idx is not None else len(filenames)

    paths = [directory + "/" + filename for filename in filenames[start_idx:end_idx]]

    return [pd.read_csv(path, encoding=encoding, sep=separator) for path in paths]
