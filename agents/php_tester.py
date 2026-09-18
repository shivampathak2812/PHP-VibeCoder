from pathlib import Path
import subprocess


class PHPTester:
    def __init__(self, php_executable="php"):
        self.php_executable = php_executable

    def find_php_files(self, project_dir):
        project_dir = Path(project_dir)

        return sorted(
            file for file in project_dir.rglob("*.php")
            if file.is_file()
        )

    def test_file(self, file_path):
        try:
            result = subprocess.run(
                [
                    self.php_executable,
                    "-l",
                    str(file_path)
                ],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return {
                    "file": str(file_path),
                    "status": "PASS",
                    "error": None
                }

            return {
                "file": str(file_path),
                "status": "FAIL",
                "error": (
                    result.stderr.strip()
                    or result.stdout.strip()
                )
            }

        except FileNotFoundError:
            return {
                "file": str(file_path),
                "status": "FAIL",
                "error": "PHP executable was not found."
            }

        except Exception as e:
            return {
                "file": str(file_path),
                "status": "FAIL",
                "error": str(e)
            }

    def test_project(self, project_dir):
        php_files = self.find_php_files(project_dir)

        results = []

        for file_path in php_files:
            result = self.test_file(file_path)
            results.append(result)

        passed = sum(
            1 for result in results
            if result["status"] == "PASS"
        )

        failed = sum(
            1 for result in results
            if result["status"] == "FAIL"
        )

        return {
            "project_dir": str(project_dir),
            "total_files": len(php_files),
            "passed": passed,
            "failed": failed,
            "results": results
        }


def main():
    project_dir = str(
        Path(__file__).resolve().parent.parent
        / "generated_projects" / "php-project"
    )

    print("=" * 70)
    print("PHP VibeCoder - PHP Testing Agent")
    print("=" * 70)

    tester = PHPTester()

    report = tester.test_project(project_dir)

    print(f"\nProject: {report['project_dir']}")
    print(f"PHP files: {report['total_files']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")

    print("\n" + "-" * 70)
    print("TEST RESULTS")
    print("-" * 70)

    for result in report["results"]:
        print(f"\n[{result['status']}] {result['file']}")

        if result["error"]:
            print(f"Error: {result['error']}")

    print("\n" + "=" * 70)

    if report["failed"] == 0:
        print("ALL PHP FILES PASSED")
    else:
        print("PHP PROJECT HAS ERRORS")

    print("=" * 70)


if __name__ == "__main__":
    main()