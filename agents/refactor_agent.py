from pathlib import Path

from agents.gemini_model_manager import GeminiModelManager
from agents.project_analyzer import PHPProjectAnalyzer


class PHPRefactorAgent:
    """
    Refactors existing PHP code while preserving functionality.

    Flow:
        Existing Project
              ↓
        Project Analyzer
              ↓
        Gemini Model Manager
              ↓
        Gemini 3.6 Flash
              ↓
        Gemini 3.5 Flash (fallback)
              ↓
        Refactored Code
              ↓
        Write Changes
    """

    def __init__(self):
        self.model_manager = GeminiModelManager()

    def read_file(self, file_path):
        """Read a PHP file."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File does not exist: {file_path}"
            )

        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    def build_project_context(self, project_path):
        """Analyze the project before refactoring."""
        analyzer = PHPProjectAnalyzer(project_path)

        return analyzer.build_context()

    def refactor_file(
        self,
        project_path,
        file_path,
        instructions
    ):
        """
        Refactor one PHP file using project context.
        """

        project_context = self.build_project_context(
            project_path
        )

        current_code = self.read_file(file_path)

        prompt = f"""
You are an expert PHP 8.x software engineer.

You are refactoring an EXISTING PHP project.

Your goal is to improve the requested code while
PRESERVING its existing functionality.

IMPORTANT RULES:

1. Do not change the intended behavior.
2. Do not remove required functionality.
3. Keep the existing architecture unless the user
   explicitly asks for architectural changes.
4. Use modern PHP 8.x practices.
5. Keep type declarations where appropriate.
6. Preserve existing namespaces.
7. Preserve existing class and method names unless
   absolutely necessary.
8. Do not introduce deprecated PHP functions.
9. Do not introduce unrelated changes.
10. Do not hardcode secrets or credentials.
11. The resulting code must be valid PHP 8.x.
12. Return the COMPLETE corrected file.
13. Do not return explanations outside the code block.

USER REFACTORING REQUEST:

{instructions}

============================================================
PROJECT CONTEXT
============================================================

{project_context}

============================================================
CURRENT FILE
============================================================

FILE:
{file_path}

CURRENT CODE:

```php
{current_code}

============================================================

Return ONLY the complete refactored PHP file inside a single
code block.
"""

        print("Sending code to Gemini for refactoring...")
        print("Model priority: Gemini 3.6 Flash -> Gemini 3.5 Flash")

        result = self.model_manager.generate(prompt)

        if not result.get("success"):
            raise RuntimeError(
                f"Gemini refactoring failed: {result.get('error')}"
            )

        response = result["response"]
        selected_model = result["model"]

        print(f"REFACTOR MODEL USED: {selected_model}")

        refactored_code = self.extract_code(response)

        if not refactored_code:
            raise ValueError(
                "Gemini did not return valid PHP code."
            )

        return refactored_code

    def extract_code(self, response):
        """Extract PHP code from Gemini response."""

        if not response:
            return None

        if "```php" in response:
            code = response.split(
                "```php",
                1
            )[1]

            if "```" in code:
                code = code.split(
                    "```",
                    1
                )[0]

            return code.strip()

        if "```" in response:
            code = response.split(
                "```",
                1
            )[1]

            if "```" in code:
                code = code.split(
                    "```",
                    1
                )[0]

            return code.strip()

        return response.strip()

    def write_refactored_file(
        self,
        file_path,
        refactored_code
    ):
        """Write the refactored code back to the file."""

        path = Path(file_path)

        path.write_text(
            refactored_code,
            encoding="utf-8"
        )

        return str(path)

def main():

    project_path = str(
        Path(__file__).resolve().parent.parent
        / "generated_projects" / "product-api"
    )

    file_path = str(
        Path(__file__).resolve().parent.parent
        / "generated_projects" / "product-api"
        / "src" / "Controllers" / "ProductController.php"
    )

    instructions = """

    Refactor this controller to improve:

    readability
    code organization
    type safety
    maintainability
    duplicated logic where appropriate

    Do not change the API behavior or endpoint behavior.
    Do not change the repository interface.
    """

    agent = PHPRefactorAgent()

    print("\n")
    print("=" * 70)
    print("PHP REFACTOR AGENT")
    print("=" * 70)

    print("\nProject:")
    print(project_path)

    print("\nFile:")
    print(file_path)

    print("\nRefactoring...")

    refactored_code = agent.refactor_file(
        project_path,
        file_path,
        instructions
    )

    agent.write_refactored_file(
        file_path,
        refactored_code
    )

    print("\nRefactored file written successfully:")
    print(file_path)

    print("\nREFACTOR AGENT COMPLETED")

if __name__ == "__main__":
    main()