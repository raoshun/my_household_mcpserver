This PR refactors test-related exports and paths:
- Add test helper functions to __init__.py exports (_data_dir, _get_data_loader, _get_db_manager)
- Add category_analysis function export
- Add _server_module export for better test mocking
- Update test_category_analysis.py to use _server_module for mocking paths
- Fix test assertion for DataSourceError handling

This refactoring improves test maintainability and mocking capabilities.