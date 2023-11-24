from typing import Dict, Optional, List
from enum import Enum
import sys
import logging
import re
import requests

from pyapitester.helpers import AppVars, AppLogger

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


class HttpRequest:
    """
    HTTP request class

    Contains all request fields, prepared for the transmission
    """

    class HttpMethod(Enum):
        """
        Supported HTTP methods
        """

        GET = 'GET'
        OPTIONS = 'OPTIONS'
        HEAD = 'HEAD'
        POST = 'POST'
        PUT = 'PUT'
        PATCH = 'PATCH'
        DELETE = 'DELETE'

    class BodyType(Enum):
        MULTIPART = 'multipart'
        TEXT = 'text'

    class HttpBody:
        Type: 'HttpRequest.BodyType'
        Text: Optional[str]
        Multipart: Optional[List['HttpRequest.MultipartField']]

        def __init__(self):
            self.Text = None
            self.Multipart = None

    class MultipartField:
        Name: str
        """Field name"""
        FileName: Optional[str]
        """Field data, either file name or data"""
        Data: Optional[str]
        """Field data, either file name or data"""

        def __init__(self):
            self.FileName = None
            self.Data = None

    Name: str
    """Request name. Expected to be unique im the collection"""

    Path: str
    """A path to the file"""

    Url: str
    """Request URL"""

    Method: HttpMethod
    """An HTTP method to use with the request"""

    Timeout: Optional[int]
    """Request timeout, ms. Default system timeout is used if zero."""

    Session: bool

    Body: HttpBody

    Headers: Dict
    """A list of http headers"""

    PreRequestScript: str
    """A script that will be executed before sending the request"""

    PostRequestScript: str
    """A script that will be executed after getting the response"""

    Source: str
    """Original content of the request file"""

    MaxRedirects: int
    """Maximum number of redirects"""

    __USER_SCRIPT_PREPEND_STRING: str = '''
from grappa import should, expect
import sys
import logging

def __indent(text_in: str) -> str:
    return '        '.join(('\\n'+text_in.lstrip()).splitlines(True))

def test_case(test_name):
    def inner_decorator(f):
        def wrapped(*args, **kwargs):
            # Covers all exceptions in the user code
            try:
                f(*args, **kwargs)
                AppLogger.log_result(True, f'Test case "{test_name}" in function {f.__name__}')
            except Exception as ex:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                AppLogger.log_result(False, f'Test case "{test_name}" in function {f.__name__}')
                logging.warning(f'    Failed with "{exc_type.__name__}" at line {str(exc_tb.tb_next.tb_lineno - 23)}: {__indent(str(exc_obj))}')

        return wrapped

    return inner_decorator
'''

    def __init__(self, filename: str):
        self.Path = filename

        with open(filename, "r") as f:
            self.Source = f.read()

    def prepare(self, app_vars: AppVars):
        self.Headers = {}
        self.Name = self.Path
        self.Url = ''
        self.Session = False
        self.PreRequestScript = ''
        self.PreRequestFile = ''
        self.PostRequestScript = ''
        self.PostRequestFile = ''
        self.Body = HttpRequest.HttpBody()
        self.__reload(app_vars)

    @staticmethod
    def __wrap_user_script(script: str) -> str:
        before = HttpRequest.__USER_SCRIPT_PREPEND_STRING
        lines = script.splitlines(True)
        after = ''

        found_test_case = False
        function_list = []
        for line in lines:
            if line.startswith("@test_case"):
                # Found a test case definition
                found_test_case = True
                continue

            # Take into account only decorated functions
            if line.startswith("def ") and found_test_case:
                found_test_case = False
                # Extract the function name
                words = re.split('\\W+', line)
                if len(words) > 1:
                    function_list.append(words[1])

        after = ''
        for function_name in function_list:
            after += f'{function_name}()\n'

        return before + script + after

    def __reload(self, app_vars: AppVars) -> None:

        AppLogger.log(f'Parsing {self.Path}', logging.DEBUG)

        data = app_vars.replace_vars(self.Source)
        data = tomllib.loads(data)

        # Request section must be there
        if "request" not in data:
            raise ValueError('"request" table is missing')

        # Get the URL
        if "url" not in data["request"]:
            AppLogger.log('URL is missing in the "request" table, using empty one', logging.WARNING)
            self.Url = ''
        else:
            self.Url = data["request"]["url"]
            AppLogger.log(f'request.url = "{self.Url}"', logging.DEBUG)

        # Get the method
        if "method" not in data["request"]:
            raise ValueError('Method is missing in the "request" table')

        self.Method = self.HttpMethod(data["request"]["method"].upper())
        AppLogger.log(f'request.method = "{self.Method.name}"', logging.DEBUG)

        # Get the timeout
        if "timeout" not in data["request"]:
            AppLogger.log('timeout is missing in the "request" table, system default will be used', logging.DEBUG)
            self.Timeout = None
        else:
            self.Timeout = data["request"]["timeout"] / 1000

        AppLogger.log(f'request.timeout = {self.Timeout}', logging.DEBUG)

        if "max_redirects" not in data["request"]:
            AppLogger.log('max_redirects is not set in the "request" table, default ' +
                          f'({requests.models.DEFAULT_REDIRECT_LIMIT}) will be used', logging.DEBUG)
            self.MaxRedirects = requests.models.DEFAULT_REDIRECT_LIMIT
        else:
            self.MaxRedirects = data["request"]["max_redirects"]

        AppLogger.log(f'request.max_redirects = {self.MaxRedirects}', logging.DEBUG)

        # Check if session support is needed
        if "session" in data["request"]:
            self.Session = data["request"]["session"]

        AppLogger.log(f'request.session = {str(self.Session).lower()}', logging.DEBUG)

        if "headers" in data:
            for header in data["headers"]:
                # Make the header name Pascal-Case. They are case-insensitive,
                # but it is common to have them in Pascal-Case.
                header_name = header.replace("-", " ").title().replace(" ", "-")
                self.Headers[header_name] = data["headers"][header]
                AppLogger.log(f'header: "{header_name}" = "{self.Headers[header_name]}"', logging.DEBUG)

        if "body" not in data:
            raise ValueError('"body" table is missing')

        if "type" not in data["body"]:
            raise ValueError('"body.type" is missing')

        self.Body.Type = self.BodyType(data["body"]["type"].lower())
        AppLogger.log(f'body.type = "{self.Body.Type.name}"', logging.DEBUG)

        if self.Body.Type == self.BodyType.TEXT:
            if "text" not in data["body"]:
                AppLogger.log('"text" is missing in the "body" table, although "type" is set to "text"',
                              logging.WARNING)
                self.Body.Text = ''
            else:
                self.Body.Text = data["body"]["text"]
                AppLogger.log(f'body.text = "{self.Body.Text}"', logging.DEBUG)
        elif self.Body.Type == self.BodyType.MULTIPART:
            multipart_keys = sorted(list(filter(lambda s: "multipart" in s, data.keys())))
            self.Body.Multipart = []
            for key in multipart_keys:
                multipart_entry = HttpRequest.MultipartField()
                if "name" not in data[key]:
                    raise KeyError(f'"name" is missing in section "{key}", file {self.Path}')
                multipart_entry.Name = data[key]["name"]
                if "data" in data[key]:
                    multipart_entry.Data = data[key]["data"]
                if "filename" in data[key]:
                    multipart_entry.FileName = data[key]["filename"]
                self.Body.Multipart.append(multipart_entry)

        if "scripts" in data:
            if "pre-request" in data["scripts"]:
                self.PreRequestScript = self.__wrap_user_script(data["scripts"]["pre-request"])
            if "post-request" in data["scripts"]:
                self.PostRequestScript = self.__wrap_user_script(data["scripts"]["post-request"])
