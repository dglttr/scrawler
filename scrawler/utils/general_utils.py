"""General purpose utility functions."""
import datetime
import re
import functools


def sanitize_text(text: str, lower: bool = False) -> str:
    """Sanitize texts by removing unnecessary or unwanted characters."""
    text = text.replace("\n", " ")  # newline character
    text = text.replace("\t", " ")  # tabulator
    text = text.replace("\r", " ")  # alternative newline character
    text = text.strip()             # spaces at beginning and end
    if lower:
        text = text.lower()

    text = re.sub("(<!--).+?(-->)", "", text)   # remove HTML comments that can contain JavaScript code

    return text


def timing_decorator(func):
    """A function decorator to measure function runtime and print the runtime on the console."""

    @functools.wraps(func)
    def timed(*args, **kw):
        start_time = datetime.datetime.now()
        result = func(*args, **kw)
        end_time = datetime.datetime.now()

        print(f"\nRuntime of method {func.__name__}: {end_time - start_time}")
        return result

    return timed


class ProgressBar:
    def __init__(self, total_length: int = 0,
                 progress: int = 0,
                 custom_message: str = "",
                 width_in_command_line: int = 100,
                 progress_char: str = "█",
                 remaining_char: str = "-"):
        """Print a progress bar in the command line interface.

        Default looks like this: ``Custom Message |██████████----------| 50.0% (5 / 10)``.

        :param total_length: Absolute length of concept (e.g. total download size = 20,000 bytes).
        :param progress: Share of ``total_length`` already reached (e.g. 10,000 bytes already downloaded).
        :param custom_message: String to appear to the left of the progress bar.
        :param width_in_command_line: Number of characters used in print to display the progress bar.
        :param progress_char: Character to use for filling the progress bar.
        :param remaining_char: Character to use for the space not yet filled by progress.
        """
        self.total_length = total_length
        self.progress = progress

        self.custom_msg = custom_message

        self.width_in_command_line = width_in_command_line

        self.progress_char = progress_char
        self.remaining_char = remaining_char

    def update(self, iterations: int = 1, total_length_update: int = 0):
        """Update internal progress parameters.

        :param iterations: Used to update :attr:`progress`.
        :param total_length_update: Used to update :attr:`total_length`.
        """
        self.progress += iterations
        self.total_length += total_length_update

        self.print()

    def print(self):
        """Print current progress on the command line."""
        try:
            percentage = self.progress / self.total_length
        except ZeroDivisionError:
            percentage = 0

        no_progress_characters = int(percentage * self.width_in_command_line)
        no_remaining_characters = self.width_in_command_line - no_progress_characters

        progress_bar = self.progress_char * no_progress_characters + self.remaining_char * no_remaining_characters

        progress_in_numbers = f"{round(percentage * 100, 2)}% ({self.progress} / {self.total_length})"     # e.g. "99.00% (99/100)"

        print(f"\r{self.custom_msg} |{progress_bar}| {progress_in_numbers}", end="")
