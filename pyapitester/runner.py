import datetime
import logging

import requests
from typing import List, Optional
from pyapitester.httprequest import HttpRequest
from pyapitester.httpresponse import HttpResponse
from pyapitester.helpers import AppLogger, AppVars, AppState
import os
import json


class Runner:
    """
    Prepares and runs all requests, executes pre- and post-request scriptss
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

            AppLogger.buffering_start()

            folder = os.path.dirname(req.Path)

            # Drop the session on folder change
            if folder != last_folder:
                if session is not None:
                    session.close()
                    session = None

            # Put our user-agent if missing
            if "User-Agent" not in req.Headers:
                req.Headers["User-Agent"] = "PyApiTester/0.1"

            if len(req.PreRequestScript) > 0:
                AppLogger.log('Executing a pre-request script')

            exec(req.PreRequestScript, {
                "req": req,
                "AppVars": self.AppVars,
                "AppLogger": AppLogger,
                "AppState": AppState
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
                    session = None
                rq = requests.Session()

            res = HttpResponse()

            rq.max_redirects = req.MaxRedirects

            try:
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

            # Go through expected statuses to check if response is OK
            # TODO: By default the response is considered to be OK
            if req.ExpectedStatuses is not None:
                if res.Exception is not None:
                    if res.Exception not in req.ExpectedStatuses:
                        res.Result = False
                        res.ResultValue = res.Exception
                    else:
                        res.ResultValue = res.Exception
                else:
                    if res.Status not in req.ExpectedStatuses:
                        res.Result = False
                        res.ResultValue = res.Status
                    else:
                        res.ResultValue = res.Status
            else: # There are no expectation, assume any valid response is fine
                if res.Exception is not None:
                    res.Result = False
                    res.ResultValue = res.Exception
                else:
                    res.ResultValue = res.Status

            AppLogger.log_header(res.Result, f'Processing {req.Path}', str(res.ResultValue))

            AppState.add_request_result(res.Result)

            AppLogger.buffering_end()

            if len(req.PostRequestScript) > 0:
                AppLogger.log('Executing a post-request script')

            exec(req.PostRequestScript, {
                "req": req,
                "res": res,
                "AppVars": self.AppVars,
                "AppLogger": AppLogger,
                "AppState": AppState
            }, None)

        AppLogger.log_summary()