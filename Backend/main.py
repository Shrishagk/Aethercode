from fastapi import FastAPI
from pydantic import BaseModel
from repo_handler import clone_repo, read_files
from indexer import build_index, search_index
from llm_engine import get_change_plan
from dependency_graph import build_dependency_graph, get_impact_analysis
app = FastAPI()

# In-memory store
INDEX_STORE = {}

# ── Models ──────────────────────────────────────────
class RepoRequest(BaseModel):
    repo_url: str

class SearchRequest(BaseModel):
    repo_name: str
    query: str

class AnalyzeRequest(BaseModel):
    repo_name: str
    task: str

# ── Routes ──────────────────────────────────────────
@app.post("/load-repo")
def load_repo(request: RepoRequest):
    repo_path = clone_repo(request.repo_url)
    files = read_files(repo_path)
    return {
        "status": "success",
        "files_found": len(files),
        "file_list": list(files.keys())
    }
@app.post("/index-repo")
def index_repo(request: RepoRequest):
    repo_path = clone_repo(request.repo_url)
    files = read_files(repo_path)
    index, chunks = build_index(files)
    dep_graph = build_dependency_graph(files)        # ← add this
    repo_name = request.repo_url.split("/")[-1]
    INDEX_STORE[repo_name] = {
        "index": index,
        "chunks": chunks,
        "dep_graph": dep_graph,                      # ← add this
        "files": files                               # ← add this
    }
    return {
        "status": "indexed",
        "chunks": len(chunks),
        "files_mapped": len(dep_graph["dependencies"])
    }
class ImpactRequest(BaseModel):
    repo_name: str
    file_path: str

@app.post("/impact")
def impact(request: ImpactRequest):
    store = INDEX_STORE.get(request.repo_name)
    if not store:
        return {"error": "Repo not indexed yet"}
    return get_impact_analysis(request.file_path, store["dep_graph"])

@app.post("/index-repo")
def index_repo(request: RepoRequest):
    repo_path = clone_repo(request.repo_url)
    files = read_files(repo_path)
    index, chunks = build_index(files)
    repo_name = request.repo_url.split("/")[-1]
    INDEX_STORE[repo_name] = {"index": index, "chunks": chunks}
    return {"status": "indexed", "chunks": len(chunks)}

@app.post("/search")
def search(request: SearchRequest):
    store = INDEX_STORE.get(request.repo_name)
    if not store:
        return {"error": "Repo not indexed yet"}
    results = search_index(request.query, store["index"], store["chunks"])
    return {"results": results}

@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    store = INDEX_STORE.get(request.repo_name)
    if not store:
        return {"error": "Repo not indexed. Call /index-repo first."}

    relevant_chunks = search_index(
        request.task, store["index"], store["chunks"], top_k=6
    )

    dep_graph = store.get("dep_graph", {})
    source_files = list(set(c["file"] for c in relevant_chunks))
    impact_summary = []
    for f in source_files[:3]:
        impact = get_impact_analysis(f, dep_graph)
        if impact["affected_count"] > 0:
            impact_summary.append(impact)

    change_plan = get_change_plan(request.task, relevant_chunks)

    return {
        "task": request.task,
        "sources": source_files,
        "impact_analysis": impact_summary,
        "plan": change_plan
    }