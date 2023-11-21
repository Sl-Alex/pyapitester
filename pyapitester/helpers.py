from string import Template
from typing import Dict, Optional
import sys
import logging

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


class AppVars(object):
    """
    TODO: Document
    """

    __data: Dict[str, str]

    def __init__(self, filename: Optional[str]):
        self.__data = {}

        if filename is None:
            return

        with open(filename, "rb") as f:
            data = tomllib.load(f)

        for key in data.keys():
            self.__setitem__(key, data[key])

    def __getitem__(self, key: str):
        if key in self.__data.keys():
            return self.__data[key]
        else:
            return None

    def __setitem__(self, key, value):
        if isinstance(value, bool):
            value = "true" if value else "false"
        self.__data[key] = value

    def __delitem__(self, key: str):
        if key in self.__data.keys():
            del self.__data[key]

    def replace_vars(self, text: str) -> str:
        """
        Replace all placeholders in the input text with the data from the dictionary

        All placeholders that are not in the dict, will remain untouched

        :param text: Input text with {{var_name}}  placeholders
        :param data: Dictionary with "var_name" : "var_value" pairs
        :return: Input text with all placeholders replaced whenever possible
        """

        class VariableReplacer(Template):
            delimiter = '{{'
            pattern = r'''
            \{\{(?:
            (?P<escaped>\{\{)|
            (?P<named>[_a-z][_a-z0-9]*)\}\}|
            (?P<braced>[_a-z][_a-z0-9]*)\}\}|
            (?P<invalid>)
            )
            '''

        return VariableReplacer(text).safe_substitute(self.__data)


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class AppLogger(object):
    progress_step: int = 0

    class bcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        NORMAL = "\033[38m"
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    COLOR_HEADER: str = f'{bcolors.HEADER}'
    RESULT_OK: str = f"{bcolors.OKGREEN}✓"
    RESULT_FAILED: str = f"{bcolors.FAIL}✗"

    # app_logger = logging.getLogger('app_logger')
    # app_logger.setLevel(logging.DEBUG)
    # sh = logging.StreamHandler()
    # sh.setFormatter(logging.Formatter('%(message)s'))
    # app_logger.addHandler(sh)
    # app_logger.propagate = False
    # urllib_logger = logging.getLogger("urllib3")
    # urllib_logger.setLevel(logging.DEBUG)

    # progress = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    progress = [
        "[O=-  ]",
        "[O-   ]",
        "[O    ]",
        "[=O   ]",
        "[-=O  ]",
        "[ -=O ]",
        "[  -=O]",
        "[   -O]",
        "[    O]",
        "[   O=]",
        "[  O=-]",
        "[ O=- ]"
    ]

    @staticmethod
    def init_logger(level=logging.INFO, logger=None):
        """
        Configures a simple console logger with the givel level.
        A usecase is to change the formatting of the default handler of the root logger
        """
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(message)s')
        logger = logger or logging.getLogger()  # either the given logger or the root logger
        logger.setLevel(level)
        # If the logger has handlers, we configure the first one. Otherwise we add a handler and configure it
        if logger.handlers:
            console = logger.handlers[0]  # we assume the first handler is the one we want to configure
        else:
            console = logging.StreamHandler()
            logger.addHandler(console)
        console.setFormatter(CustomFormatter())
        console.setLevel(level)

    @staticmethod
    def __log(message: str, level: int = logging.INFO):
        logging.log(level, message)

    @staticmethod
    def log(message: str, level: int = logging.INFO):
        AppLogger.__log(f'    {message}', level)
        # AppLogger.app_logger.log(level= level, msg=message)

    @staticmethod
    def log_header(message: str):
        AppLogger.__log(f'{AppLogger.COLOR_HEADER}{message}{AppLogger.bcolors.ENDC}')

    @staticmethod
    def log_result(ok: bool, message: str):
        AppLogger.log(f'{AppLogger.RESULT_OK if ok else AppLogger.RESULT_FAILED} {message}{AppLogger.bcolors.ENDC}')

    @staticmethod
    def update_progress():
        AppLogger.progress_step = AppLogger.progress_step + 1
        if AppLogger.progress_step == len(AppLogger.progress):
            AppLogger.progress_step = 0

        print(" " + AppLogger.progress[AppLogger.progress_step], end='\r')
