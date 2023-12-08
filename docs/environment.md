---
title: Environment
order: 3
---
# Environment

Enviroment configuration simplifies collection management a lot. It has all environment variables and other parameters, that need to be common on the collectionn level. Instead of hardcoding the base URL, or the user name, it makes sense to put them to the environment configuration file.

This file can be stored anywhere. It has "env" extension, and despite the extension, it is a TOML file. For now it has only one section for environment variables, e.g.:

{% raw %}
```toml
[vars]
# All variables defined here can be used in any request, e.g. {{base_url}}
base_url = 'http://httpbin.org/'
base_timeout = 3500
test_str = 'This Is A String'
test_int = 3755399308445874391
test_bool = true
```
{% endraw %}

In the future, it will have other sections, such as proxy configuration and so on.

Variables defined in the environment can be used in any part of the [request](request.html) file. In fact, the parser just replaces all variable names, surrounded with double curly brackets, with the value of that variable.