import os.path
from typing import Dict, Optional, List, Any, Union
from enum import Enum
import sys
import logging
import re
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from pyapitester.helpers import EnvVars, AppLogger

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
        Type: Optional['HttpRequest.BodyType']
        Text: Optional[str]
        Multipart: Optional[List['HttpRequest.MultipartField']]

        def __init__(self):
            self.Type = None
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

    FullPath: str
    """A full path to the file"""

    Url: str
    """Request URL"""

    Method: HttpMethod
    """An HTTP method to use with the request"""

    Timeout: Optional[int]
    """Request timeout, ms. Default system timeout is used if zero."""

    Auth: Optional[Union[HTTPBasicAuth, HTTPDigestAuth]] = None

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

    ExpectedStatuses: Optional[List] = None
    """Expected status code or exception name. Both are in string format"""

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
                AppState.add_test_result(True)
                AppLogger.log_result(True, f'Test case "{test_name}" in function {f.__name__}')
            except Exception as ex:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                AppState.add_test_result(False)
                AppLogger.log_result(False, f'Test case "{test_name}" in function {f.__name__}')
                logging.warning(f'    Failed with "{exc_type.__name__}" at line {str(exc_tb.tb_next.tb_lineno - 25)}: {__indent(str(exc_obj))}')

        return wrapped

    return inner_decorator
'''

    def __init__(self, filename: str):
        self.Path = filename
        self.FullPath = os.path.abspath(self.Path)

        with open(filename, "r") as f:
            self.Source = f.read()

    def prepare(self, env_vars: EnvVars):
        self.Headers = {}
        self.Name = self.Path
        self.Url = ''
        self.Session = False
        self.PreRequestScript = ''
        self.PostRequestScript = ''
        self.Body = HttpRequest.HttpBody()
        self.__reload(env_vars)

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

    def __reload(self, env_vars: EnvVars) -> None:
        """
        Reload the original *.toml file

        Internally the function doesn't re-open the file, but just re-applies
        current variables to the file content.
        """

        AppLogger.log(f'Parsing {self.Path}', logging.DEBUG)

        data: Dict[str, Any] = tomllib.loads(env_vars.replace_vars(self.Source))

        # Request section must be there
        if "request" not in data:
            raise ValueError('"request" table is missing')

        # Get the URL
        self.Url = data["request"].get("url", '')
        if len(self.Url) == 0:
            AppLogger.log('URL is missing in the "request" table, using empty one', logging.WARNING)
        else:
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

        # Get the auth
        if "auth" in data:
            if "basic" in data["auth"]:
                if "username" in data["auth"]["basic"] and "password" in data["auth"]["basic"]:
                    self.Auth = HTTPBasicAuth(
                        data["auth"]["basic"]["username"],
                        data["auth"]["basic"]["password"]
                    )
                else:
                    AppLogger.log("Basic auth should have username and password", logging.WARNING)
            elif "digest" in data["auth"]:
                if "username" in data["auth"]["digest"] and "password" in data["auth"]["digest"]:
                    self.Auth = HTTPDigestAuth(
                        data["auth"]["digest"]["username"],
                        data["auth"]["digest"]["password"]
                    )
                else:
                    AppLogger.log("Digest auth should have username and password", logging.WARNING)
            else:
                # Auth is not basic
                AppLogger.log("Only basic and digest auth are supported as of now", logging.WARNING)

        self.MaxRedirects = data["request"].get("max_redirects")
        if self.MaxRedirects is None:
            AppLogger.log('max_redirects is not set in the "request" table, default ' +
                          f'({requests.models.DEFAULT_REDIRECT_LIMIT}) will be used', logging.DEBUG)
            self.MaxRedirects = requests.models.DEFAULT_REDIRECT_LIMIT

        AppLogger.log(f'request.max_redirects = {self.MaxRedirects}', logging.DEBUG)

        self.ExpectedStatuses = data["request"].get("expected_status")
        if self.ExpectedStatuses is None:
            AppLogger.log('expected_status is not set in the "request" table, by default ' +
                          f'all responses with valid status codes will be considered as OK', logging.DEBUG)
        else:
            AppLogger.log(f'request.expected_status = {self.ExpectedStatuses}', logging.DEBUG)

        # Check if session support is needed
        self.Session = data["request"].get("session")
        AppLogger.log(f'request.session = {str(self.Session).lower()}', logging.DEBUG)

        if "headers" in data:
            for header in data["headers"]:
                # Make the header name Pascal-Case. They are case-insensitive,
                # but it is common to have them in Pascal-Case.
                header_name = header.replace("-", " ").title().replace(" ", "-")
                self.Headers[header_name] = data["headers"][header]
                AppLogger.log(f'header: "{header_name}" = "{self.Headers[header_name]}"', logging.DEBUG)

        if "body" in data:

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
                        # if "data" entry is not present then a real file will be sent
                        if multipart_entry.Data is None:
                            # Calculate absolute path to the file if needed
                            if not os.path.isabs(multipart_entry.FileName):
                                multipart_entry.FileName = \
                                    os.path.join(os.path.dirname(self.FullPath),multipart_entry.FileName)
                    self.Body.Multipart.append(multipart_entry)

        if "scripts" in data:
            if "pre-request" in data["scripts"]:
                self.PreRequestScript = self.__wrap_user_script(data["scripts"]["pre-request"])
            if "post-request" in data["scripts"]:
                self.PostRequestScript = self.__wrap_user_script(data["scripts"]["post-request"])
