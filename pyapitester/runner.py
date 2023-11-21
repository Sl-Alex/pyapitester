import datetime
import logging

import requests
from typing import List, Optional
from pyapitester.httprequest import HttpRequest
from pyapitester.httpresponse import HttpResponse
from pyapitester.helpers import AppLogger, AppVars
import os
import json


class Runner:
    """
    TODO: Describe the class
    """

    Requests: List[HttpRequest]
    AppVars: AppVars

    def __init__(self, app_vars: AppVars):
        self.Requests = []
        self.AppVars = app_vars

    def add_request(self, request: HttpRequest):
        self.Requests.append(request)

    def run(self):
        # Always start without any session
        session: Optional[requests.Session] = None
        last_folder = ''

        for req in self.Requests:

            req.prepare(self.AppVars)

            AppLogger.log_header(f'Processing {req.Path}:')

            folder = os.path.dirname(req.Path)

            # Drop the session on folder change
            if folder != last_folder:
                if session is not None:
                    session.close()

            # Put our user-agent if missing
            if "User-Agent" not in req.Headers:
                req.Headers["User-Agent"] = "PyApiTester/0.1"

            exec(req.PreRequestScript, {
                "req": req,
                "app_vars": self.AppVars,
                "AppLogger": AppLogger
            }, None)

            # If session is needed
            if req.Session:
                # If session doesn't exist - initialize a new one
                if session is None:
                    session = requests.Session()
                rq = session
            else:
                # Session is not needed, close if there is one
                if session is not None:
                    session.close()
                rq = requests

            res = HttpResponse()

            if req.Body.Type == HttpRequest.BodyType.MULTIPART:
                multipart_fields = {}
                for entry in req.Body.Multipart:
                    if entry.Data and not entry.FileName:
                        multipart_fields[entry.Name] = (None, entry.Data)
                    elif entry.FileName and not entry.Data:
                        multipart_fields[entry.Name] = (os.path.basename(entry.FileName), open(entry.FileName, 'rb+'))
                    elif entry.FileName and entry.Data:
                        multipart_fields[entry.Name] = (os.path.basename(entry.FileName), entry.Data)
                    else:
                        AppLogger.log(f'Neither "data" nor "filename" are specified for {req.Path}, section {entry.Name}')
                        continue
            else:
                multipart_fields = None

            try:
                r = rq.request(
                    method=req.Method.value,
                    url=req.Url,
                    headers=req.Headers,
                    data=req.Body.Text,
                    files=multipart_fields,
                    timeout=req.Timeout,
                    stream=True
                )
                res.Status = r.raw.status
                for k, v in r.raw.headers.items():
                    res.Headers[k] = v

                res.Size = len(r.raw.data)

                res.Time = round(r.elapsed / datetime.timedelta(milliseconds=1))

                # Try to parse as JSON. If it doesn't parse - simply ignore
                # noinspection PyBroadException
                try:
                    res.Json = json.loads(r.raw.data)
                except Exception as ex:
                    AppLogger.log("Couldn't parse the response as JSON", logging.DEBUG)
                    pass

            except Exception as ex:
                res.Exception = type(ex).__name__

            exec(req.PostRequestScript, {
                "req": req,
                "res": res,
                "app_vars": self.AppVars,
                "AppLogger": AppLogger
            }, None)
