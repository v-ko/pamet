import shutil
import sys
from pathlib import Path

mock_root = Path(__file__).parent


def anonymize_repo():
    # Copy all files from the original/ repo and replace absolute paths with {template_root}
    original_repo_path = mock_root / "original"
    anonymized_repo_path = mock_root / "template"
    if anonymized_repo_path.exists():
        shutil.rmtree(anonymized_repo_path)
    shutil.copytree(original_repo_path, anonymized_repo_path)

    # Walk through all files in the anonymized repo and replace absolute paths
    for file_path in anonymized_repo_path.rglob("*"):
        if file_path.is_file() and file_path.suffix in {".json"}:
            with file_path.open("r", encoding="utf-8") as f:
                content = f.read()
            # Replace absolute paths with {template_root}
            content = content.replace(str(original_repo_path), "{template_root}")
            with file_path.open("w", encoding="utf-8") as f:
                f.write(content)


def prepare_mock_repo():
    # Copy the template repo to prepared_test_time/ and replace {template_root} with the actual path
    template_repo_path = mock_root / "template"
    prepared_repo_path = mock_root / "prepared_test_time"
    if prepared_repo_path.exists():
        shutil.rmtree(prepared_repo_path)
    shutil.copytree(template_repo_path, prepared_repo_path)

    for file_path in prepared_repo_path.rglob("*"):
        if file_path.is_file() and file_path.suffix in {".json"}:
            with file_path.open("r", encoding="utf-8") as f:
                content = f.read()
            # Replace {template_root} with the actual path
            content = content.replace("{template_root}", str(prepared_repo_path))
            with file_path.open("w", encoding="utf-8") as f:
                f.write(content)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "anonymize":
        anonymize_repo()
    else:
        prepare_mock_repo()


if __name__ == "__main__":
    main()
