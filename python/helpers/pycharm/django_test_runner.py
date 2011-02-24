from pycharm.tcunittest import TeamcityTestRunner
from django.test.simple import build_suite, build_test, settings, get_app, get_apps, setup_test_environment, teardown_test_environment
import unittest
from django.test.testcases import TestCase
from tcmessages import TeamcityServiceMessages
import django
import sys

try:
  from django.test.simple import DjangoTestSuiteRunner
  class BaseRunner(TeamcityTestRunner, DjangoTestSuiteRunner):
    def __init__(self, stream=sys.stdout):
      TeamcityTestRunner.__init__(self,stream)
      DjangoTestSuiteRunner.__init__(self)

except ImportError:
  class BaseRunner(TeamcityTestRunner):
    def __init__(self, stream=sys.stdout):
      TeamcityTestRunner.__init__(self,stream)

class DjangoTeamcityTestRunner(BaseRunner):
  def __init__(self, stream=sys.stdout):
    BaseRunner.__init__(self, stream)

  def run_suite(self, suite):
        return TeamcityTestRunner().run(suite)

def partition_suite(suite, classes, bins):
    """
    Partitions a test suite by test type.

    classes is a sequence of types
    bins is a sequence of TestSuites, one more than classes

    Tests of type classes[i] are added to bins[i],
    tests with no match found in classes are place in bins[-1]
    """
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            partition_suite(test, classes, bins)
        else:
            for i in range(len(classes)):
                if isinstance(test, classes[i]):
                    bins[i].addTest(test)
                    break
            else:
                bins[-1].addTest(test)

def reorder_suite(suite, classes):
    """
    Reorders a test suite by test type.

    classes is a sequence of types

    All tests of type clases[0] are placed first, then tests of type classes[1], etc.
    Tests with no match in classes are placed last.
    """
    class_count = len(classes)
    bins = [unittest.TestSuite() for i in range(class_count+1)]
    partition_suite(suite, classes, bins)
    for i in range(class_count):
        bins[0].addTests(bins[i+1])
    return bins[0]

def run_tests(test_labels, verbosity=1, interactive=False, extra_tests=[]):
    """
    Run the unit tests for all the test labels in the provided list.
    Labels must be of the form:
     - app.TestClass.test_method
        Run a single specific test method
     - app.TestClass
        Run all the test methods in a given class
     - app
        Search for doctests and unittests in the named application.

    When looking for tests, the test runner will look in the models and
    tests modules for the application.

    A list of 'extra' tests may also be provided; these tests
    will be added to the test suite.

    Returns the number of tests that failed.
    """
    if django.VERSION[1] > 1:
      return DjangoTeamcityTestRunner().run_tests(test_labels, extra_tests=extra_tests)

    setup_test_environment()

    settings.DEBUG = False
    suite = unittest.TestSuite()

    if test_labels:
        for label in test_labels:
            if '.' in label:
                suite.addTest(build_test(label))
            else:
                app = get_app(label)
                suite.addTest(build_suite(app))
    else:
        for app in get_apps():
            suite.addTest(build_suite(app))

    for test in extra_tests:
        suite.addTest(test)

    suite = reorder_suite(suite, (TestCase,))

    old_name = settings.DATABASE_NAME
    from django.db import connection
    connection.creation.create_test_db(verbosity, autoclobber=True)
    TeamcityServiceMessages(sys.stdout).testCount(suite.countTestCases())
    result = DjangoTeamcityTestRunner().run(suite)
    connection.creation.destroy_test_db(old_name, verbosity)

    teardown_test_environment()

    return len(result.failures) + len(result.errors)
