from typing import Dict, Optional, Union, List
import time
from enum import Enum
import sys
import logging
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

    TimeStamp: float
    """Request timestamp, to be set upon transmission"""

    PreRequestScript: str
    """A script that will be executed before sending the request"""

    PreRequestFile: str
    """A script file that will be executed before sending the request"""

    PostRequestScript: str
    """A script that will be executed after getting the response"""

    PostRequestFile: str
    """A script file that will be executed before sending the request"""

    def __init__(self, filename: str):
        self.Path = filename

    def prepare(self, app_vars: AppVars):
        self.Headers = {}
        self.Name = self.Path
        self.Url = ''
        self.Session = False
        self.TimeStamp = time.monotonic()
        self.PreRequestScript = ''
        self.PreRequestFile = ''
        self.PostRequestScript = ''
        self.PostRequestFile = ''
        self.Body = HttpRequest.HttpBody()
        self.__load_from_file(self.Path, app_vars)

    def __wrap_user_script(self, name: str, script: str) -> str:
        # Wrap in a one-time loop so that the user could break out
        # Also wrap in an exception handler to report an error to the user
        script = ("try:\n" +
                  "    for _unused_ in range(1):\n" +
                  "        ".join(("\n" + script).splitlines(True)) + "\n" +
                  "except Exception as ex:\n" +
                  "    exc_type, exc_obj, exc_tb = sys.exc_info()\n" +
                  "    AppLogger.log_result(False, f'" + name + " script in \"{req.Path}\" crashed " +
                  "with \"{exc_type.__name__}\" at line {str(exc_tb.tb_lineno - 3)}: {str(exc_obj)}')")

        return script

    def __load_from_file(self, filename: str, app_vars: AppVars) -> None:

        logging.debug(f'Parsing {filename}')

        with open(filename, "r") as f:
            data = f.read()
            data = app_vars.replace_vars(data)
            data = tomllib.loads(data)

        # Request section must be there
        if "request" not in data:
            raise ValueError('"request" table is missing')

        # Get the URL
        if "url" not in data["request"]:
            logging.warning('URL is missing in the "request" table, using empty one')
            self.Url = ''
        else:
            self.Url = data["request"]["url"]
            logging.debug(f'request.url = "{self.Url}"')

        # Get the method
        if "method" not in data["request"]:
            raise ValueError('Method is missing in the "request" table')

        self.Method = self.HttpMethod(data["request"]["method"].upper())
        logging.debug(f'request.method = "{self.Method.name}"')

        # Get the timeout
        if "timeout" not in data["request"]:
            logging.debug('timeout is missing in the "request" table, system default will be used')
            self.Timeout = None
        else:
            self.Timeout = data["request"]["timeout"] / 1000

        logging.debug(f'request.timeout = {self.Timeout}')

        # Check if session support is needed
        if "session" in data["request"]:
            self.Session = data["request"]["session"]

        logging.debug(f'request.session = {str(self.Session).lower()}')

        if "headers" in data:
            for header in data["headers"]:
                # Make the header name Pascal-Case. They are case-insensitive,
                # but it is common to have them in Pascal-Case.
                header_name = header.replace("-", " ").title().replace(" ", "-")
                self.Headers[header_name] = data["headers"][header]
                logging.debug(f'header: "{header_name}" = "{self.Headers[header_name]}"')

        if "body" not in data:
            raise ValueError('"body" table is missing')

        if "type" not in data["body"]:
            raise ValueError('"body.type" is missing')

        self.Body.Type = self.BodyType(data["body"]["type"].lower())
        logging.debug(f'body.type = "{self.Body.Type.name}"')

        if self.Body.Type == self.BodyType.TEXT:
            if "text" not in data["body"]:
                logging.warning('"text" is missing in the "body" table, although "type" is set to "text"')
                self.Body.Text = ''
            else:
                self.Body.Text = data["body"]["text"]
                logging.debug(f'body.text = "{self.Body.Text}"')
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
                self.PreRequestScript = self.__wrap_user_script("pre-request", data["scripts"]["pre-request"])
            if "pre-request-file" in data["scripts"]:
                self.PreRequestFile = data["scripts"]["pre-request-file"]
            if "post-request" in data["scripts"]:
                self.PostRequestScript = self.__wrap_user_script("post-request",data["scripts"]["post-request"])
            if "post-request-file" in data["scripts"]:
                self.PostRequestFile = data["scripts"]["post-request-file"]
