import re, os, sys
import logging

test_folder = "./playground"
env_file = "default.env"

def check_results(text_output):
    requests_passed = len(re.findall(r'Requests:.+failed: 0', text_output)) == 1
    tests_passed = len(re.findall(r'Tests:.+failed: 0', text_output)) == 1
    if not requests_passed or not tests_passed:
        sys.stderr.write(text_output)
        assert requests_passed, "There are failed requests"
        assert tests_passed, "There are failed tests"


def test_auth(capfd):
    os.system(f"python main.py run {test_folder}/00_auth -e {test_folder}/{env_file}")
    text_output = capfd.readouterr().err
    check_results(text_output)

def test_methods(capfd):
    os.system(f"python main.py run {test_folder}/01_methods -e {test_folder}/{env_file}")
    text_output = capfd.readouterr().err
    check_results(text_output)

def test_headers(capfd):
    os.system(f"python main.py run {test_folder}/02_headers -e {test_folder}/{env_file}")
    text_output = capfd.readouterr().err
    check_results(text_output)

def test_body(capfd):
    os.system(f"python main.py run {test_folder}/03_body -e {test_folder}/{env_file}")
    text_output = capfd.readouterr().err
    check_results(text_output)
