import re
from app.services.file_tools import read_file, write_file, restore_backup
from app.services.test_executor import run_tests
from app.services.llm_client import get_llm_client

MAX_ATTEMPTS = 3


def extract_code_block(text: str) -> str:
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def fix_and_verify(file_path: str, test_path: str, provider: str = "gemini") -> dict:
    llm = get_llm_client(provider)
    history = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = run_tests(test_path)

        if result["passed"]:
            return {
                "success": True,
                "attempts": attempt - 1,
                "history": history,
                "final_output": result["output"],
            }

        current_code = read_file(file_path)

        prompt = "The following Python file has a bug, confirmed by a failing test.\n\n"
        prompt += "FILE: " + file_path + "\n```python\n" + current_code + "\n```\n\n"
        prompt += "TEST OUTPUT (shows the failure):\n```\n" + result["output"] + "\n```\n\n"
        prompt += "Fix the bug in the file above. Respond with ONLY the corrected, complete file content "
        prompt += "inside a single python code block. Do not include any explanation outside the code block."

        llm_result = llm.generate(prompt)
        fixed_code = extract_code_block(llm_result["text"])

        backup_path = write_file(file_path, fixed_code)

        history.append({
            "attempt": attempt,
            "test_output_before_fix": result["output"],
            "applied_fix": fixed_code,
            "backup_path": backup_path,
        })

    final_result = run_tests(test_path)
    return {
        "success": final_result["passed"],
        "attempts": MAX_ATTEMPTS,
        "history": history,
        "final_output": final_result["output"],
    }