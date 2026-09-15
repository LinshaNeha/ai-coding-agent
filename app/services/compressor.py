def compress_code(text: str) -> str:
    """
    Reduces token count of code text before sending to the LLM, without
    changing its meaning. Strips:
    - trailing whitespace on each line
    - collapses multiple consecutive blank lines into one
    - removes full-line comments (lines that are ONLY a comment)

    Does NOT touch inline comments or anything inside strings, to avoid
    accidentally breaking code semantics.
    """
    lines = text.split("\n")
    compressed = []
    blank_run = 0

    for line in lines:
        stripped = line.rstrip()

        if not stripped.strip():
            blank_run += 1
            if blank_run > 1:
                continue
            compressed.append("")
            continue

        blank_run = 0

        if stripped.strip().startswith("#"):
            continue

        compressed.append(stripped)

    return "\n".join(compressed)