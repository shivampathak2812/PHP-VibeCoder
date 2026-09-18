from agents.code_agent import PHPCodeAgent
from agents.php_tester import PHPTester
from agents.debug_agent import PHPDebugAgent


class PHPVibeCoder:

    def __init__(self, max_retries=3):
        self.code_agent = PHPCodeAgent(top_k=5)
        self.php_tester = PHPTester()
        self.debug_agent = PHPDebugAgent()
        self.max_retries = max_retries

    def generate_project(
        self,
        requirement,
        project_name="vibe-project",
        attachment_path=None,
        attachment_type=None
    ):
        print("\n" + "=" * 70)
        print("STEP 1 - CODE GENERATION")
        print("=" * 70)

        print("\nGenerating PHP project...")

        if attachment_path:
            print(f"Attachment: {attachment_path}")
            print(f"Attachment type: {attachment_type}")

        result = self.code_agent.generate_code(
            requirement,
            project_name=project_name,
            attachment_path=attachment_path,
            attachment_type=attachment_type
        )

        project_dir = result["project_dir"]

        print("\nProject generated:")
        print(project_dir)

        print("\nFiles created:")
        for file_path in result["files_created"]:
            print(f"- {file_path}")

        return project_dir

    def test_project(self, project_dir):
        print("\n" + "=" * 70)
        print("PHP TESTING")
        print("=" * 70)

        report = self.php_tester.test_project(project_dir)

        print(f"\nPHP files: {report['total_files']}")
        print(f"Passed: {report['passed']}")
        print(f"Failed: {report['failed']}")

        for result in report["results"]:
            print(
                f"\n[{result['status']}] "
                f"{result['file']}"
            )

            if result["error"]:
                print(f"Error: {result['error']}")

        return report

    def debug_project(self, report):
        failed_results = [
            result
            for result in report["results"]
            if result["status"] == "FAIL"
        ]

        if not failed_results:
            return

        print("\n" + "=" * 70)
        print("DEBUGGING ERRORS")
        print("=" * 70)

        for result in failed_results:

            file_path = result["file"]
            error_message = result["error"]

            print("\nDebugging file:")
            print(file_path)

            print("\nSending error to Debug Agent...")

            corrected_code = self.debug_agent.debug_file(
                file_path,
                error_message
            )

            self.debug_agent.write_fixed_file(
                file_path,
                corrected_code
            )

            print("File fixed successfully.")

    def run(
        self,
        requirement,
        project_name="vibe-project",
        attachment_path=None,
        attachment_type=None
    ):
        print("\n" + "=" * 70)
        print("PHP VIBECODER")
        print("=" * 70)

        print("\nUSER REQUIREMENT:")
        print(requirement)

        if attachment_path:
            print("\nUSER ATTACHMENT:")
            print(f"Path: {attachment_path}")
            print(f"Type: {attachment_type}")

        # --------------------------------------------------
        # STEP 1: Generate project
        # --------------------------------------------------

        project_dir = self.generate_project(
            requirement=requirement,
            project_name=project_name,
            attachment_path=attachment_path,
            attachment_type=attachment_type
        )

        # --------------------------------------------------
        # STEP 2: Test project
        # --------------------------------------------------

        for attempt in range(1, self.max_retries + 1):

            print("\n" + "=" * 70)
            print(
                f"VALIDATION ATTEMPT "
                f"{attempt}/{self.max_retries}"
            )
            print("=" * 70)

            report = self.test_project(project_dir)

            # --------------------------------------------------
            # SUCCESS
            # --------------------------------------------------

            if report["failed"] == 0:

                print("\n" + "=" * 70)
                print("PROJECT VALIDATION SUCCESSFUL")
                print("=" * 70)

                print(
                    f"\nAll {report['passed']} PHP files "
                    "passed syntax validation."
                )

                return {
                    "success": True,
                    "project_dir": project_dir,
                    "project": project_dir.split("\\")[-1],
                    "attempts": attempt,
                    "test_report": report
                }

            # --------------------------------------------------
            # FAILURE
            # --------------------------------------------------

            if attempt < self.max_retries:

                print("\nPHP errors detected.")

                self.debug_project(report)

                print("\nRe-testing fixed project...")

            else:

                print("\n" + "=" * 70)
                print("PROJECT VALIDATION FAILED")
                print("=" * 70)

                print(
                    f"\nMaximum retries reached: "
                    f"{self.max_retries}"
                )

                return {
                    "success": False,
                    "project_dir": project_dir,
                    "project": project_dir.split("\\")[-1],
                    "attempts": attempt,
                    "test_report": report
                }


if __name__ == "__main__":
    print("PHPVibeCoder module loaded successfully.")
    print("Use PHPVibeCoder.run() with a dynamic requirement.")