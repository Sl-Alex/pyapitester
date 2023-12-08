---
title: Collection
order: 2
---
# Collection

Collection is a set of [requests](request.html) and [enviroment](environment.html) configurations. Requests are organized in folders, making a clear and structured project tree. It is possible to run any request, or any folder in the collection, or even the entire collection at once.

All files in the collection should be created using [TOML](https://toml.io/en/) syntax.

This is how a typical collection might look like:

<pre style="letter-spacing: 0px; line-height:100%;">
Collection/                          Execution order
├─ 01 users/
│  ├─ 01 login/
│  │  ├─ 01 login wrong pass.toml       1
│  │  ├─ 02 login wrong user.toml       2
│  │  └─ 03 login normal.toml           3
│  ├─ 02 second login.toml              4
│  ├─ 03 get profile.toml               5
│  ├─ 04 logout/
│  │  ├─ 01 logout.toml                 6
│  │  └─ 02 second logout.toml          7
│  └─ 05 get profile failed.toml        8
├─ 02 device/
│  ├─ 01 login admin.toml               9
│  ├─ 02 factory reset.toml             10
│  └─ 03 get status.toml                11
├─ dev.env
└─ prod.env
</pre>

The order, in which the collection is processed, depends solely on the names of the files and folders. PyApiTester will get the full path for each file in the collection and sort them in an alphabetic order before execution. The example above is already sorted and will be executed exactly in that order.

## Running the test

Running the test is very simple. Here are all supported parameters:

```bash
$ python ./main.py -h
usage: main.py [-h] [--environment ENVIRONMENT] [--verbose] {run,check} path

positional arguments:
  {run,check}           Command to execute
  path                  Could be a folder or a single file

options:
  -h, --help            show this help message and exit
  --environment ENVIRONMENT, -e ENVIRONMENT
                        Path to the environment configuration file (*.env)
  --verbose, -v         Enable verbose mode
```

All parameters except of ```command``` and ```path ``` are optional. ```path``` accepts either a request file name if you want to run a single request or a folder name if you have a lot of requests to test. As of now, only ```run``` command is supported.