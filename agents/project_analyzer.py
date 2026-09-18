from pathlib import Path
import re


class PHPProjectAnalyzer:
    """
    Analyzes an existing PHP project and extracts:
    - Project structure
    - PHP files
    - Classes
    - Functions / methods
    - Namespaces
    - Basic file-level information
    """

    def __init__(self, project_path):
        self.project_path = Path(project_path)

        if not self.project_path.exists():
            raise FileNotFoundError(
                f"Project path does not exist: {self.project_path}"
            )

        if not self.project_path.is_dir():
            raise ValueError(
                f"Project path is not a directory: {self.project_path}"
            )

    def find_php_files(self):
        """Find all PHP files recursively."""
        return sorted(
            [
                path
                for path in self.project_path.rglob("*.php")
                if path.is_file()
            ]
        )

    def read_file(self, file_path):
        """Read a PHP file safely."""
        try:
            return Path(file_path).read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except Exception as e:
            return f"[Unable to read file: {e}]"

    def extract_namespace(self, code):
        """Extract PHP namespace."""
        match = re.search(
            r"\bnamespace\s+([^;]+);",
            code
        )

        return match.group(1).strip() if match else None

    def extract_classes(self, code):
        """Extract PHP class, interface, trait and enum names."""

        pattern = (
            r"\b(class|interface|trait|enum)\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)"
        )

        matches = re.findall(pattern, code)

        return [
            {
                "type": item_type,
                "name": name
            }
            for item_type, name in matches
        ]

    def extract_functions(self, code):
        """
        Extract function/method names.
        This is intentionally lightweight and does not try to fully parse PHP.
        """

        pattern = (
            r"\bfunction\s+"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*\("
        )

        return re.findall(pattern, code)

    def analyze_file(self, file_path):
        """Analyze one PHP file."""

        code = self.read_file(file_path)

        relative_path = Path(file_path).relative_to(
            self.project_path
        )

        return {
            "file": str(relative_path),
            "absolute_path": str(file_path),
            "lines": len(code.splitlines()),
            "namespace": self.extract_namespace(code),
            "classes": self.extract_classes(code),
            "functions": self.extract_functions(code),
            "content": code
        }

    def analyze(self):
        """Analyze the complete PHP project."""

        php_files = self.find_php_files()

        files = []

        for file_path in php_files:
            files.append(
                self.analyze_file(file_path)
            )

        return {
            "project_path": str(self.project_path),
            "php_file_count": len(php_files),
            "files": files
        }

    def get_project_structure(self):
        """Return a simple project structure."""

        structure = []

        for path in sorted(self.project_path.rglob("*")):

            if not path.is_file():
                continue

            # Ignore common unnecessary directories
            parts = path.relative_to(self.project_path).parts

            ignored = {
                "vendor",
                ".git",
                "node_modules",
                "__pycache__"
            }

            if any(part in ignored for part in parts):
                continue

            relative_path = path.relative_to(self.project_path)

            structure.append(str(relative_path))

        return structure

    def build_context(self):
        """
        Build a compact context that can later be sent
        to the Code Understanding Agent / Gemini.
        """

        analysis = self.analyze()
        structure = self.get_project_structure()

        context = []

        context.append("PHP PROJECT ANALYSIS")
        context.append("=" * 60)

        context.append(
            f"Project Path: {analysis['project_path']}"
        )

        context.append(
            f"PHP Files: {analysis['php_file_count']}"
        )

        context.append("\nPROJECT STRUCTURE")
        context.append("-" * 60)

        for item in structure:
            context.append(item)

        context.append("\nPHP FILE DETAILS")
        context.append("-" * 60)

        for file_info in analysis["files"]:

            context.append(
                f"\nFILE: {file_info['file']}"
            )

            context.append(
                f"Lines: {file_info['lines']}"
            )

            if file_info["namespace"]:
                context.append(
                    f"Namespace: {file_info['namespace']}"
                )

            if file_info["classes"]:
                context.append("Classes / Types:")

                for item in file_info["classes"]:
                    context.append(
                        f"  - {item['type']}: {item['name']}"
                    )

            if file_info["functions"]:
                context.append("Functions / Methods:")

                for function in file_info["functions"]:
                    context.append(
                        f"  - {function}()"
                    )

            context.append("\nSOURCE CODE")
            context.append(file_info["content"])

        return "\n".join(context)


def main():

    project_path = str(
        Path(__file__).resolve().parent.parent
        / "generated_projects" / "product-api"
    )

    analyzer = PHPProjectAnalyzer(project_path)

    analysis = analyzer.analyze()

    print("\nPHP PROJECT ANALYZER")
    print("=" * 60)

    print(
        f"Project: {analysis['project_path']}"
    )

    print(
        f"PHP files found: {analysis['php_file_count']}"
    )

    print("\nFILES")
    print("-" * 60)

    for file_info in analysis["files"]:

        print(f"\nFILE: {file_info['file']}")

        if file_info["namespace"]:
            print(
                f"Namespace: {file_info['namespace']}"
            )

        if file_info["classes"]:
            print("Classes / Types:")

            for item in file_info["classes"]:
                print(
                    f"  - {item['type']}: {item['name']}"
                )

        if file_info["functions"]:
            print("Functions / Methods:")

            for function in file_info["functions"]:
                print(
                    f"  - {function}()"
                )

    print("\nPROJECT ANALYSIS COMPLETED")


if __name__ == "__main__":
    main()