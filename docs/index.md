---
layout: default
---

Welcome to the PyApiTester documentation. Here you'll get an idea how to use it and find some useful examples.

The aim of this project is to create a very small and useful command-line tool for testing the backend API.
This tool doesn't have and does not need any GUI, all requests are stored in a simple text-based format. Changing the request means opening the file in your favorite text editor and changing it.
Let's put it simple:

Pros:
- it's a small CLI application written in Python
- it uses [Requests](https://github.com/psf/requests) library, which supports Python v3.7+
- git-friendly text-based ([TOML](https://toml.io/){:target="_blank"}) format for all your requests and environments
- user-friendly colored output
- easy testing with [grappa](https://github.com/grappa-py/grappa)
- pre- and post-request scripts with test cases in Python
- Detailed exception info for easy user scripts debugging

Cons:
- It is CLI application. If you need GUI, I'd recommend using [Bruno](https://www.usebruno.com/).
- You need to have Python v3.7+ installed.

Sometimes one picture can say more than thousand words:

![Sample CLI output](cli_output.png)

And this is an example of the post-request script that tests the response:
```python
@test_case("Validate the response")
def validate_the_response():
    # You can change 'None' to any other exception type if needed, e.g. 'ConnectTimeout' or 'TooManyRedirects'
    expect(res.Exception).to.equal(None)
    expect(res.Status).to.be.equal(200)
    # You can use any environment variable. Everywhere.
    expect(res.Json["json"]["answer"]).to.be.equal(42)
    expect(res.Json["json"]["valid"]).to.be.true
    expect(res.Time).to.be.less(1000)

# You can define your functions (not test-case) and call them as usual
def test_exception():
    # This will always fail
    expect(False).to.be.true
    # This will never be executed because the line above is executed first
    expect(res.Status).to.be.equal(200)

@test_case("This Test Should Fail")
def exceptional_test():
    test_exception()
    # You can raise any exception if you want
    #raise FileNotFoundError("Oops, the file is lost")
``` 
