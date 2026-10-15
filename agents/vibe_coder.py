from pathlib import Path

from agents.code_agent import PHPCodeAgent
from agents.php_tester import PHPTester
from agents.debug_agent import PHPDebugAgent


class PHPVibeCoder:

    def __init__(self, max_retries=3, api_key=None):
        self.code_agent = PHPCodeAgent(top_k=3, api_key=api_key)
        self.php_tester = PHPTester()
        self.debug_agent = PHPDebugAgent(api_key=api_key)
        self.max_retries = max_retries
        self.last_generation = None

    def generate_project(
        self,
        requirement,
        project_name="vibe-project",
        attachment_path=None,
        attachment_type=None,
        on_progress=None
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
            attachment_type=attachment_type,
            on_progress=on_progress
        )

        self.last_generation = result

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
            print(f"- {result['file']}")

        # One Gemini request for all broken files.
        print("\nSending all errors to Debug Agent in one request...")

        fixed_files = self.debug_agent.debug_files(
            report["project_dir"],
            failed_results
        )

        allowed = {
            str(Path(result["file"]).resolve())
            for result in failed_results
        }

        for file_path, corrected_code in fixed_files.items():

            # Only overwrite files that were reported as broken.
            if file_path not in allowed:
                continue

            self.debug_agent.write_fixed_file(
                file_path,
                corrected_code
            )

            print(f"Fixed: {file_path}")

    def _model_used(self):
        if self.last_generation:
            return self.last_generation.get("model")
        return None

    def run(
        self,
        requirement,
        project_name="vibe-project",
        attachment_path=None,
        attachment_type=None,
        on_progress=None
    ):
        """
        on_progress: optional callback(text_so_far) called while the
        project is being written (streaming).
        """
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
            attachment_type=attachment_type,
            on_progress=on_progress
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
            # PHP NOT INSTALLED: don't spend Gemini calls
            # "fixing" files that are not actually broken.
            # --------------------------------------------------

            if not report.get("php_available", True):

                print(
                    "\nPHP is not installed. "
                    "Skipping syntax validation."
                )

                return {
                    "success": True,
                    "validated": False,
                    "project_dir": project_dir,
                    "project": Path(project_dir).name,
                    "attempts": 0,
                    "test_report": report,
                    "model": self._model_used()
                }

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
                    "validated": True,
                    "model": self._model_used(),
                    "project_dir": project_dir,
                    "project": Path(project_dir).name,
                    "attempts": attempt,
                    "test_report": report
                }

            # --------------------------------------------------
            # FAILURE
            # --------------------------------------------------

            if attempt < self.max_retries:

                print("\nPHP errors detected.")

                try:

                    self.debug_project(report)

                except Exception as e:

                    # The project itself was generated; keep it and
                    # report the debugging failure instead of losing it.
                    return {
                        "success": False,
                        "model": self._model_used(),
                        "project_dir": project_dir,
                        "project": Path(project_dir).name,
                        "attempts": attempt,
                        "test_report": report,
                        "error": f"Automatic debugging failed: {e}"
                    }

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
                    "model": self._model_used(),
                    "project_dir": project_dir,
                    "project": Path(project_dir).name,
                    "attempts": attempt,
                    "test_report": report
                }


if __name__ == "__main__":
    print("PHPVibeCoder module loaded successfully.")
    print("Use PHPVibeCoder.run() with a dynamic requirement.")