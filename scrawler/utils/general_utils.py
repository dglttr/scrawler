"""General purpose utility functions."""
import datetime
import re


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


def timing_decorator(method):
    """A function decorator to measure function runtime and print the runtime on the console."""

    def timed(*args, **kw):
        start_time = datetime.datetime.now()
        result = method(*args, **kw)
        end_time = datetime.datetime.now()

        print(f"\nRuntime of method {method.__name__}: {end_time - start_time}")
        return result

    return timed


class ProgressBar:
    """Print a progress bar in the command line interface."""

    def __init__(self, total_length: int = 0,
                 progress: int = 0,
                 custom_message: str = "",
                 width_in_command_line: int = 100,
                 progress_char: str = "█",
                 remaining_char: str = "-"):
        self.TOTAL_LENGTH = total_length
        self.PROGRESS = progress

        self.CUSTOM_MSG = custom_message

        self.WIDTH_IN_COMMAND_LINE = width_in_command_line

        self.PROGRESS_CHAR = progress_char
        self.REMAINING_CHAR = remaining_char

    def update(self, iterations: int = 1, total_length_update: int = 0):
        """Update internal progress parameters."""
        self.PROGRESS += iterations
        self.TOTAL_LENGTH += total_length_update

        self.print()

    def print(self):
        """Print current progress on the command line."""
        try:
            percentage = self.PROGRESS / self.TOTAL_LENGTH
        except ZeroDivisionError:
            percentage = 0

        no_progress_characters = int(percentage * self.WIDTH_IN_COMMAND_LINE)
        no_remaining_characters = self.WIDTH_IN_COMMAND_LINE - no_progress_characters

        progress_bar = self.PROGRESS_CHAR * no_progress_characters + self.REMAINING_CHAR * no_remaining_characters

        progress_in_numbers = f"{round(percentage * 100, 2)}% ({self.PROGRESS} / {self.TOTAL_LENGTH})"     # e.g. "99.00% (99/100)"

        print(f"\r{self.CUSTOM_MSG} |{progress_bar}| {progress_in_numbers}", end="")
