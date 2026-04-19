import os
import git

CLONE_DIR = "./cloned_repos"

def clone_repo(repo_url: str) -> str:
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(CLONE_DIR, repo_name)

    if not os.path.exists(repo_path):
        git.Repo.clone_from(repo_url, repo_path)

    return repo_path

def read_files(repo_path: str) -> dict:
    file_contents = {}
    SKIP = {'.git', 'node_modules', '__pycache__', '.env'}

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go')):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_path)
                try:
                    with open(full_path, 'r', errors='ignore') as f:
                        file_contents[rel_path] = f.read()
                except Exception:
                    pass

    return file_contents