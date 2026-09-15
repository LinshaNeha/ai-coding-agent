import os
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())


class CodeIndexer:
    def __init__(self):
        self.parser = Parser(PY_LANGUAGE)

    def index_file(self, file_path: str) -> list[dict]:
        """Parses a single Python file and returns a list of chunk dicts."""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source_code = f.read()

        tree = self.parser.parse(bytes(source_code, "utf-8"))
        root_node = tree.root_node

        chunks = []
        self._walk(root_node, source_code, file_path, chunks)
        return chunks

    def _walk(self, node, source_code, file_path, chunks):
        if node.type in ("function_definition", "class_definition"):
            name_node = node.child_by_field_name("name")
            chunk_name = name_node.text.decode("utf-8") if name_node else "unknown"

            chunks.append({
                "file_path": file_path,
                "chunk_type": node.type.replace("_definition", ""),  # "function" or "class"
                "chunk_name": chunk_name,
                "content": node.text.decode("utf-8"),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
            })
            # Don't descend into function bodies to avoid nested duplicate chunks,
            # but DO descend into classes to catch their methods.
            if node.type == "class_definition":
                for child in node.children:
                    self._walk(child, source_code, file_path, chunks)
        else:
            for child in node.children:
                self._walk(child, source_code, file_path, chunks)

    def index_directory(self, directory: str, exclude_dirs=None) -> list[dict]:
        """Walks a directory recursively and indexes every .py file."""
        exclude_dirs = exclude_dirs or {"venv", "__pycache__", ".git", "node_modules"}
        all_chunks = []

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    try:
                        chunks = self.index_file(full_path)
                        all_chunks.extend(chunks)
                    except Exception as e:
                        print(f"Failed to index {full_path}: {e}")

        return all_chunks