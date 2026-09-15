import subprocess
import sys


def run_tests(test_path: str = ".") -> dict:
    """
    Runs pytest against the given path and returns structured results:
    passed (bool), output (full stdout+stderr), summary (last line, usually the pass/fail count).
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = result.stdout + result.stderr
    passed = result.returncode == 0

    lines = [line for line in output.strip().split("\n") if line.strip()]
    summary = lines[-1] if lines else "No output"

    return {
        "passed": passed,
        "output": output,
        "summary": summary,
        "returncode": result.returncode,
    }