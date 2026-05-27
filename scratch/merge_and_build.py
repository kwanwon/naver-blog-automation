import os
import json
import sys
from pathlib import Path

# Load AST and Semantic
ast_path = Path('graphify-out/.graphify_ast.json')
sem_path = Path('graphify-out/.graphify_semantic.json')

if not ast_path.exists() or not sem_path.exists():
    print("Error: AST or Semantic files are missing in graphify-out/.")
    sys.exit(1)

ast_result = json.loads(ast_path.read_text(encoding="utf-8"))
sem_result = json.loads(sem_path.read_text(encoding="utf-8"))

# Merge AST + semantic
merged = {
    "nodes": list(ast_result.get("nodes", [])) + list(sem_result.get("nodes", [])),
    "edges": list(ast_result.get("edges", [])) + list(sem_result.get("edges", [])),
    "hyperedges": list(sem_result.get("hyperedges", [])),
    "input_tokens": ast_result.get("input_tokens", 0) + sem_result.get("input_tokens", 0),
    "output_tokens": ast_result.get("output_tokens", 0) + sem_result.get("output_tokens", 0),
}

# Build graph + cluster + score + write
from graphify.build import build as _build
from graphify.cluster import cluster as _cluster, score_all as _score_all
from graphify.export import to_json, to_html, _git_head as _gh
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate

# Set root watch_path
watch_path = Path(".")
out = watch_path / "graphify-out"

# Build graph
G = _build([merged], dedup=True)
print(f"Merged Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# Cluster & Analyze
communities = _cluster(G)
cohesion = _score_all(G, communities)
try:
    gods = god_nodes(G)
except Exception:
    gods = []
try:
    surprises = surprising_connections(G, communities)
except Exception:
    surprises = []

# Generate Labels
labels = {cid: f"Community {cid}" for cid in communities}
# Try to load existing labels if any
labels_path = out / ".graphify_labels.json"
if labels_path.exists():
    try:
        loaded_labels = json.loads(labels_path.read_text(encoding="utf-8"))
        for k, v in loaded_labels.items():
            labels[int(k)] = v
    except Exception:
        pass

try:
    questions = suggest_questions(G, communities, labels)
except Exception:
    questions = []

tokens = {"input": merged.get("input_tokens", 0), "output": merged.get("output_tokens", 0)}
_commit = _gh()

# Generate Report
report = generate(
    G, communities, cohesion, labels, gods, surprises,
    {"warning": "built successfully from AST + semantic"},
    tokens, str(watch_path), suggested_questions=questions,
    min_community_size=3, built_at_commit=_commit
)

# Write outputs
(out / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
to_json(G, communities, str(out / "graph.json"), force=True)
labels_path.write_text(json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False), encoding="utf-8")

# Generate visualization
to_html(G, communities, str(out / "graph.html"))

# Generate tree visualization
try:
    from graphify.tree_html import write_tree_html
    write_tree_html(out / "graph.json", out / "GRAPH_TREE.html")
    print("D3 tree visualization successfully generated at graphify-out/GRAPH_TREE.html")
except Exception as e:
    print(f"Failed to generate D3 tree visual: {e}")

print("Merge, build, clustering, and report generation completed successfully!")
