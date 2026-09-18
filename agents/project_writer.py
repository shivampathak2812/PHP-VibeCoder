import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "generated_projects"


class ProjectWriter:

    def __init__(self, output_dir=OUTPUT_DIR):
        self.output_dir = Path(output_dir)

    def extract_files(self, gemini_response):
        lines = gemini_response.splitlines()

        files = []
        current_file = None
        current_content = []
        inside_code = False

        for line in lines:

            if line.startswith("FILE:"):
                if current_file is not None:
                    files.append({
                        "path": current_file,
                        "content": "\n".join(current_content).strip()
                    })

                current_file = line.replace("FILE:", "", 1).strip()
                current_content = []
                inside_code = False
                continue

            if current_file is not None:

                if line.strip().startswith("```"):
                    inside_code = not inside_code
                    continue

                if inside_code:
                    current_content.append(line)

        if current_file is not None:
            files.append({
                "path": current_file,
                "content": "\n".join(current_content).strip()
            })

        return files

    def validate_path(self, file_path):
        path = Path(file_path)

        if path.is_absolute():
            raise ValueError(
                f"Absolute path not allowed: {file_path}"
            )

        if ".." in path.parts:
            raise ValueError(
                f"Path traversal not allowed: {file_path}"
            )

        return path

    def write_project(self, project_name, gemini_response):
        project_name = re.sub(
            r"[^a-zA-Z0-9_-]",
            "-",
            project_name
        )

        project_dir = self.output_dir / project_name

        project_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        files = self.extract_files(gemini_response)

        if not files:
            raise ValueError(
                "No files found in Gemini response."
            )

        files_created = []

        for file_data in files:
            relative_path = self.validate_path(
                file_data["path"]
            )

            full_path = project_dir / relative_path

            full_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            full_path.write_text(
                file_data["content"],
                encoding="utf-8"
            )

            files_created.append(
                str(relative_path)
            )

        return {
            "project_dir": str(project_dir),
            "files_created": files_created,
            "file_count": len(files_created)
        }


def main():
    print("=" * 70)
    print("PHP VibeCoder - Project Writer Test")
    print("=" * 70)

    test_response = """
PROJECT OVERVIEW

Simple PHP test project.

FILES

FILE: public/index.php
```php
<?php

echo "PHP VibeCoder is working!";

?>

FILE: config/config.php

<?php

return [
    "app_name" => "PHP VibeCoder"
];

?>

FILE: database/schema.sql

CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL
);

"""

    writer = ProjectWriter()

    result = writer.write_project(
        "test-project",
        test_response
)

    print()
    print("Project created:")
    print(result["project_dir"])

    print()
    print("Files created:")

    for file_path in result["files_created"]:
        print(f"- {file_path}")

    print()
    print(f"Total files: {result['file_count']}")

    print()
    print("Project Writer test completed successfully.")

if __name__ == "__main__":
    main()