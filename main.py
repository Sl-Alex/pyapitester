import logging
import errno
import fnmatch
from typing import List

from pyapitester.helpers import AppLogger, AppVars
from pyapitester.httprequest import HttpRequest
from pyapitester.runner import Runner
import argparse
import os

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=['run', 'check'], help="Command to execute")
    parser.add_argument("path", help="Could be a folder or a single file")
    parser.add_argument("--environment", "-e", help="Path to the environment configuration file (*.env)")
    parser.add_argument("--verbose", "-v", action='store_true', help="Enable verbose mode")
    args = parser.parse_args()

    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    AppLogger.init_logger(level=log_level)

    if not os.path.exists(args.path):
        logging.error(f'No such file or directory: "{args.path}"')
        exit(errno.ENOENT)

    if (args.environment is not None) and (not os.path.exists(args.environment)):
        logging.error(f'Environment not found: "{args.environment}"')
        exit(errno.ENOENT)

    if (args.environment is not None) and (os.path.splitext(args.environment)[1] != '.env'):
        logging.error(f'Environment file should have *.env extension')
        exit(errno.ENOENT)

    app_vars: AppVars = AppVars(args.environment)

    # Check if the path is a file or a directory
    file_list: List[str] = []
    folder_list: List[str] = []
    if os.path.isfile(args.path):
        if not args.path.endswith(".toml"):
            logging.error(f'Expected *.toml, found "{args.path}"')
            exit(errno.EINVAL)
        file_list.append(args.path)
        folder_list.append(os.path.dirname(args.path))
    else:
        for root, dirnames, filenames in os.walk(args.path):
            for filename in fnmatch.filter(filenames, '*.toml'):
                if os.path.basename(filename) != "env.toml":
                    # Add the file to the list
                    full_name = os.path.join(root, filename)
                    file_list.append(full_name)
                    # Add the folder to the list if necessary
                    if root not in folder_list:
                        folder_list.append(root)

    if len(file_list) == 0:
        logging.error('No requests found')
        exit(errno.ENOENT)

    # Order the list
    # The order should be the following:
    # 1. ALL files in the folder in the alphabetic order
    # 2. All folders in the alphabetic order

    file_list_ordered: List[str] = []
    # Sort folders in the alphabetic order
    folder_list.sort()
    for folder_name in folder_list:
        # Get all files in the folder
        for filename in file_list:
            if os.path.dirname(filename) == folder_name:
                file_list_ordered.append(filename)

    if args.command == 'run':
        # Add all requests to the runner
        runner = Runner(app_vars)
        for filename in file_list_ordered:
            runner.add_request(HttpRequest(filename))
        # Run all requests
        runner.run()

    if args.command == 'check':
        # TODO: Implement requests validation
        # TODO: Think of renaming the CLI command, e.g. 'check' ==> 'validate'
        logging.error('Checking is not implemented yet')
        exit(errno.EINVAL)
