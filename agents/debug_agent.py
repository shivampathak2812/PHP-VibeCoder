from pathlib import Path

from agents.gemini_model_manager import GeminiModelManager


class PHPDebugAgent:
    def __init__(self):
        self.model_manager = GeminiModelManager()

    def read_file(self, file_path):
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        return path.read_text(encoding="utf-8")

    def debug_file(self, file_path, error_message):
        code = self.read_file(file_path)

        prompt = f"""
You are an expert PHP 8.5 debugging agent.

A PHP Testing Agent found a syntax error in a generated PHP project.

FILE:
{file_path}

PHP ERROR:
{error_message}

CURRENT CODE:
```php
{code}

Your task:

Identify the exact cause of the PHP syntax error.
Fix the code.
Preserve the original functionality.
Use valid PHP 8.x syntax.
Do not introduce unrelated changes.
Return the complete corrected PHP file.

IMPORTANT:
Return ONLY the corrected PHP code inside a single

...

code block.

Do not include explanations outside the code block.
"""

        print("\nTrying Gemini 3.6 Flash -> Gemini 3.5 Flash...")

        result = self.model_manager.generate(prompt)

        if not result.get("success"):
            raise RuntimeError(
                f"Gemini debugging failed: {result.get('error')}"
            )

        response = result["response"]

        print(f"DEBUG MODEL USED: {result['model']}")

        corrected_code = self.extract_code(response)

        if not corrected_code:
            raise ValueError(
                "Gemini did not return valid PHP code."
            )

        return corrected_code

    def extract_code(self, response):
        lines = response.splitlines()

        inside_code = False
        code_lines = []

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                if not inside_code:
                    inside_code = True
                else:
                    break

                continue

            if inside_code:
                code_lines.append(line)

        # If Gemini returned code without a code fence
        if not code_lines:
            return response.strip()

        return "\n".join(code_lines).strip()

    def write_fixed_file(self, file_path, corrected_code):
        path = Path(file_path)

        path.write_text(
            corrected_code,
            encoding="utf-8"
        )

        return str(path)

def main():
    print("=" * 70)
    print("PHP VibeCoder - Debug Agent Test")
    print("=" * 70)

    file_path = (
        r"D:\PHP-VibeCoder\generated_projects"
        r"\php-project\public\index.php"
    )

    error_message = (
        'Parse error: syntax error, unexpected identifier '
        '"DATABASE" in public/index.php on line 73'
    )

    agent = PHPDebugAgent()

    print("\nDebugging:")
    print(file_path)

    print("\nSending error to Gemini...")

    corrected_code = agent.debug_file(
        file_path,
        error_message
    )

    print("\nCorrected code received.")

    agent.write_fixed_file(
        file_path,
        corrected_code
    )

    print("\nFixed file written successfully:")
    print(file_path)

    print("\n" + "=" * 70)
    print("DEBUG AGENT COMPLETED")
    print("=" * 70)

if __name__ == "__main__":
    main()