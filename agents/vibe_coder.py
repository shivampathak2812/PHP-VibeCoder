from pathlib import Path

from agents.code_agent import PHPCodeAgent
from agents.php_tester import PHPTester
from agents.debug_agent import PHPDebugAgent, local_fix


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
        """
        Fix files that failed php -l, cheapest step first:
        1. local fixes with no AI (BOM, leftover ``` fences, <?php tag)
        2. one AI request that returns only the changed lines (patch)
        3. one AI request that returns whole files (fallback)
        """

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

        allowed = {
            str(Path(result["file"]).resolve())
            for result in failed_results
        }

        # ---------------- 1. local fixes ----------------
        remaining = []

        for result in failed_results:

            path = Path(result["file"])

            try:
                code = path.read_text(encoding="utf-8")
            except OSError:
                remaining.append(result)
                continue

            fixed = local_fix(code)

            if fixed != code:

                path.write_text(fixed, encoding="utf-8")

                retest = self.php_tester.test_file(path)

                if retest["status"] == "PASS":
                    print(f"Fixed locally (no AI): {path}")
                    continue

                result = retest

            remaining.append(result)

        if not remaining:
            return

        for result in remaining:
            print(f"- {result['file']}")

        # ---------------- 2. patch ----------------
        try:

            fixed_files, remaining = self.debug_agent.debug_files_patch(
                report["project_dir"],
                remaining
            )

        except Exception as e:

            print(f"Patch debugging failed: {e}")
            fixed_files = {}

        # ---------------- 3. whole files ----------------
        if remaining:

            print("\nSome files need a full rewrite...")

            fixed_files.update(
                self.debug_agent.debug_files(
                    report["project_dir"],
                    remaining
                )
            )

        for file_path, corrected_code in fixed_files.items():

            # Only overwrite files that were reported as broken.
            if file_path not in allowed:
                continue

            self.debug_agent.write_fixed_file(
                file_path,
                corrected_code
            )

            print(f"Fixed: {file_path}")

    def _remember(self, requirement, project_dir):
        """A tested project can be reused for similar requests later."""

        # A reused project is already in the memory.
        if self.last_generation and self.last_generation.get("source") == "reuse":
            return

        self.code_agent.remember_project(
            requirement, project_dir, self._model_used()
        )

    def _source(self):
        """"cache", "reuse", "adapt" or "generated"."""
        if self.last_generation:
            return self.last_generation.get("source")
        return None

    def _thinking_used(self):
        if self.last_generation:
            return self.last_generation.get("thinking")
        return None

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

                self._remember(requirement, project_dir)

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
                    "model": self._model_used(),
                    "thinking": self._thinking_used(),
                    "source": self._source()
                }

            # --------------------------------------------------
            # SUCCESS
            # --------------------------------------------------

            if report["failed"] == 0:

                self._remember(requirement, project_dir)

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
                    "thinking": self._thinking_used(),
                    "source": self._source(),
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
                    "thinking": self._thinking_used(),
                    "source": self._source(),
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
                    "thinking": self._thinking_used(),
                    "source": self._source(),
                    "project_dir": project_dir,
                    "project": Path(project_dir).name,
                    "attempts": attempt,
                    "test_report": report
                }


if __name__ == "__main__":
    print("PHPVibeCoder module loaded successfully.")
    print("Use PHPVibeCoder.run() with a dynamic requirement.")