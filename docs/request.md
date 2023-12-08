---
title: Request
order: 4
---
# Request file

Request file is a simple [TOML](https://toml.io/en/) file with all request parameters. Depending on the request, some parameters could be optional. A typical request file might look like this:

{% raw %}
```toml
# "request" section is mandatory for each request
[request]
# Environment variables can be used everywhere in this file,
# they are replaced before processing.
# They should be defined like this: {{variable_name}}

# URL to call. Optional parameter.
url = 'http://httpbin.org/post'
# This is how it looks like with the environment variable:
# url = '{{base_url}}'

# Method, should be one of [OPTIONS,HEAD,POST,PUT,PATCH,DELETE].
# Mandatory parameter
method = 'POST'

# Request timeout, ms. Optional parameter
timeout = 2000

# Maximum number of redirects, default is 30.
# Zero means no redirects are allowed
max_redirects = 0

# The request is considered to be OK if either the response code
# or the exception are specified in the array. Optional field.
# If not specified then all requests without exception will be
# considered as "passed"
expected_status = [200, "TooManyRedirects"]

# Sessions are disabled unless asked explicitly
# Any request in the chain that doesn't have "session" option
# or that have "session" set to false will break the session
session = false

[headers]
# According to HTTP specification header names are case-insensitive
# Internally we convert them to Pascal-Case, for example:
# "cOnTeNt-tYpE" --> "Content-Type"
# The value remains case-sensitive
cOnTeNt-tYpE = "application/json; charset=utf-8"

[body]
# Body type, either "text" or "multipart"
type = "text"
# This is a simple text body
text = '''
{
    "valid": true,
    "value": 3755399308445874391,
    "status": "This Is A String"
}
'''
# All multipart sections should have names starting with "multipart-",
# followed by a number. Numbers start from 1 and should be contiguous
[multipart-1]
# This example adds a normal key/value part
name = "json_data"
data = '''{
    "id": 10325,
    "value": 56532,
    "status": "Invalid data"
}'''
[multipart-2]
# This example adds the file from the file system
name = "file_data"
filename = "data.zip"
[multipart-3]
# This creates a "virtual" file. The file doesn't exist
# on the file system, but will be sent as such
name = "virtual_file"
filename = "virtual.txt"
data = '''Lorem ipsum dolor sit amet,
consectetur adipiscing elit,
sed do eiusmod tempor incididunt
ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis
nostrud exercitation ullamco laboris
nisi ut aliquip ex ea commodo
consequat. Duis aute irure dolor
in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla
pariatur. Excepteur sint occaecat
cupidatat non proident, sunt in culpa
qui officia deserunt mollit anim
id est laborum.'''
[scripts]
# This section has two scripts: pre-request and post-request
# pre-request script has access to:
#     - req (HttpRequest object)
#     - EnvVars (Dictionary with var_name:var_value pairs)
#     - AppLogger - log custom messages and test results
#     - @test_case decorator for the test case functions
#           see examples below
# post-request script has access to the same set of objects,
# as well as to:
#     - res (HttpResponse object) 
pre-request = '''
# Here you can write any python code your interpreter can execute
# These test cases will be executed before sending the request

# For example, we test some pre-requisites ....
@test_case("Sessions should be disabled")
def validate_sessions():
    expect(req.Session).to.be.false

'''
# The post-request script is executed after getting the response
# Test cases defined here can check the result and set some environment
# variables if needed
post-request = '''
@test_case("Validate the response")
def validate_the_response():
    # You can change 'None' to any other exception type if needed,
    # e.g. 'ConnectTimeout' or 'TooManyRedirects'
    expect(res.Exception).to.equal(None)
    expect(res.Status).to.be.equal(200)
    # You can use any environment variable. Everywhere.
    expect(res.Json["json"]["value"]).to.be.equal({{test_int}})
    expect(res.Json["json"]["valid"]).to.be.{{test_bool}}
    expect(res.Time).to.be.less(1000)

# You can define your functions (not test-case) and call them as usual
def test_exception():
    # This will always fail
    expect(False).to.be.true
    # This will never be executed because the line above
    # is executed first
    expect(res.Status).to.be.equal(200)

@test_case("This Test Should Fail")
def exceptional_test():
    test_exception()
    # You can raise any exception if you want
    raise FileNotFoundError("Oops, the file is lost")
'''

```
{% endraw %}
