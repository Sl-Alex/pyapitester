from string import Template
from typing import Dict, Optional, Tuple, List
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


class AppState(object):
    RequestsTotal: int = 0
    RequestsOk: int = 0
    RequestsFailed: int = 0

    TestsTotal: int = 0
    TestsOk: int = 0
    TestsFailed: int = 0

    @staticmethod
    def add_test_result(ok: bool):
        AppState.TestsTotal += 1
        if ok:
            AppState.TestsOk += 1
        else:
            AppState.TestsFailed += 1

    @staticmethod
    def add_request_result(ok: bool):
        AppState.RequestsTotal += 1
        if ok:
            AppState.RequestsOk += 1
        else:
            AppState.RequestsFailed += 1


class AppLogger(object):
    progress_step: int = 0
    request_in_progress: bool = False

    class Colors:
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

    COLOR_HEADER: str = f'{Colors.HEADER}'
    RESULT_OK: str = f"{Colors.OKGREEN}✓"
    RESULT_FAILED: str = f"{Colors.FAIL}✗"

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

    log_buffer: List[Tuple[int, str]] = []

    @staticmethod
    def init_logger(level=logging.INFO, logger=None):
        """
        Configures a simple console logger with the given level.
        A usecase is to change the formatting of the default handler of the root logger
        """
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
    def __log(message: str, level: int = logging.INFO, log_now: bool = False):
        if AppLogger.request_in_progress and not log_now:
            AppLogger.log_buffer.append((level, message))
        else:
            logging.log(level, message)

    @staticmethod
    def log(message: str, level: int = logging.INFO):
        AppLogger.__log(f'    {message}', level)

    @staticmethod
    def log_header(ok: bool, message: str, result: str):
        logging.log(logging.INFO,f'{AppLogger.RESULT_OK if ok else AppLogger.RESULT_FAILED} ' +
                    f'{AppLogger.Colors.OKBLUE}{message} (' +
                    f'{AppLogger.Colors.OKGREEN if ok else AppLogger.Colors.FAIL}{result}' +
                    f'{AppLogger.Colors.ENDC}{AppLogger.Colors.OKBLUE}){AppLogger.Colors.ENDC}')

    @staticmethod
    def log_summary():
        logging.log(logging.INFO, f'\n{AppLogger.Colors.OKCYAN}Summary:{AppLogger.Colors.ENDC}')

        req_total = str(AppState.RequestsTotal)
        req_ok = str(AppState.RequestsOk)
        req_failed = str(AppState.RequestsTotal - AppState.RequestsOk)

        tests_total = str(AppState.TestsTotal)
        tests_ok = str(AppState.TestsOk)
        tests_failed = str(AppState.TestsTotal - AppState.TestsOk)

        len_total = max(len(req_total), len(tests_total))
        len_ok = max(len(req_ok), len(tests_ok))
        len_failed = max(len(req_failed), len(tests_failed))

        AppLogger.log(f'Requests: {req_total:>{len_total}}, ' +
                      f'failed: {req_failed:>{len_failed}}, ' +
                      f'succeeded: {req_ok:>{len_ok}}')

        AppLogger.log(f'Tests:    {tests_total:>{len_total}}, ' +
                      f'failed: {tests_failed:>{len_failed}}, ' +
                      f'succeeded: {tests_ok:>{len_ok}}')

    @staticmethod
    def log_result(ok: bool, message: str):
        AppLogger.log(f'{AppLogger.RESULT_OK if ok else AppLogger.RESULT_FAILED} {message}{AppLogger.Colors.ENDC}')

    @staticmethod
    def buffering_start():
        AppLogger.request_in_progress = True

    @staticmethod
    def buffering_end():
        AppLogger.request_in_progress = False
        for log_entry in AppLogger.log_buffer:
            logging.log(log_entry[0], log_entry[1])
        AppLogger.log_buffer = []

    @staticmethod
    def update_progress():
        AppLogger.progress_step = AppLogger.progress_step + 1
        if AppLogger.progress_step == len(AppLogger.progress):
            AppLogger.progress_step = 0

        print(" " + AppLogger.progress[AppLogger.progress_step], end='\r')
