from typing import Dict, Optional, Union


class HttpResponse:
    """
    HTTP request class

    Contains all request fields, prepared for the transmission
    """

    Headers: Dict
    """A list of http headers"""

    Status: int
    """Http status code"""

    Exception: Optional[str]
    """Exception during request processing, None if there is no exception"""

    ExceptionDetails: Optional[str]
    """Exception details, None if there is no exception"""

    Json: Optional[Dict]

    Result: bool

    ResultValue: Union[int,str]
    """Either status code or exception"""

    Size: int

    Time: int

    def __init__(self):
        self.Headers = {}
        self.Status = 0
        self.Exception = None
        self.ExceptionDetails = None
        self.Size = 0
        self.Json = None
        self.Time = 0
        self.Result = True
        self.ResultValue = ''
