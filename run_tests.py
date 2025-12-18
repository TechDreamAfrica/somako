#!/usr/bin/env python
"""
Test runner for the Food delivery app
Run all tests for the food and food_pwa apps
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner


def run_tests():
    """Run all tests for food-related apps"""
    os.environ['DJANGO_SETTINGS_MODULE'] = 'somako.settings'
    django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Define test modules to run
    test_modules = [
        'food.test_models',
        'food.test_views', 
        'food.test_forms',
        'food.test_utils',
        'food_pwa.test_views',
    ]
    
    print("Running Food App Test Suite...")
    print("=" * 50)
    
    failures = test_runner.run_tests(test_modules)
    
    if failures:
        print(f"\n❌ {failures} test(s) failed")
        return False
    else:
        print("\n✅ All tests passed!")
        return True


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
