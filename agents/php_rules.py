"""
Code quality rules sent to Gemini whenever it writes PHP code
(project generation and refactoring). Changing this text also
invalidates the generation cache, so old answers are not reused.
"""

PHP_QUALITY_RULES = """
CODE QUALITY RULES (apply to every project):

Security
- Never put variables or user input inside SQL strings. Every query that
  uses a value must be a prepared statement with a placeholder
  (:name or ?) and the value passed to execute() / bind_param().
- If the project demonstrates queries, include at least one real query
  that takes user input (e.g. a filter or search form) as a bound
  parameter.
- Escape all output with htmlspecialchars($value, ENT_QUOTES, 'UTF-8').
- Use password_hash() / password_verify() for passwords and CSRF tokens
  for state-changing forms.

Error handling
- Catch exceptions (PDOException, mysqli_sql_exception, ...), write the
  real message to error_log(), and show users only a generic message.
- Show detailed error messages only when an APP_DEBUG environment
  variable is true. Never echo $e->getMessage() to users otherwise.

Configuration
- Read database settings and APP_DEBUG from environment variables
  (getenv) with safe local defaults. No secrets in source code.

SQL scripts
- Schema scripts must be safe to run more than once:
  CREATE DATABASE / TABLE IF NOT EXISTS, UNIQUE keys on natural
  identifiers, and INSERT IGNORE (or ON DUPLICATE KEY UPDATE) for
  sample data so rows are never duplicated.

Code quality
- No duplicated logic: reuse a method instead of copying code.
- Comments must describe what the code really does.
- Use declare(strict_types=1) and type declarations.

Tutorial / "explain" requests
- When the user asks to learn or explain a concept, build a small
  working demo plus on-page explanations that cover: the recommended
  approach, common alternatives (e.g. PDO and mysqli for databases)
  with when to use each, and side-by-side UNSAFE vs SAFE examples.
"""
