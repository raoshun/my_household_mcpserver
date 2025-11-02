### Refactor create_http_app implementation

This issue covers the tasks discussed in this chat to refactor the create_http_app function to reduce its complexity and adhere to the single responsibility principle. The planned changes include:

1. Breaking down the create_http_app function into smaller, focused sub-functions:
   - initialize_app
   - setup_cache_and_streamer
   - setup_cors
   - register_endpoints

2. Simplifying the main create_http_app function to delegate tasks to these sub-functions.

3. Testing the refactored function to ensure it works as expected.

The work is tracked in the branch `refactor-create-http-app`, created from the `main` branch. The next steps include implementing the proposed changes, testing them, and opening a pull request for review.

This issue serves as a placeholder to track the progress and discussions related to this task.
