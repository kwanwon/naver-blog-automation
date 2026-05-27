import os
import json
import sys
from pathlib import Path
import graphify.llm as gllm

# 1. Load .env
env_path = Path('.env')
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")

# Verify Gemini API Key
api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment or .env file.")
    sys.exit(1)

# 2. Read uncached files
uncached_path = Path('graphify-out/.graphify_uncached.txt')
if not uncached_path.exists():
    # If the file doesn't exist, we might have already run the extraction
    # Let's check if we can read it, or if it's empty
    print("Warning: graphify-out/.graphify_uncached.txt does not exist. Re-checking cache to rebuild it.")
    
    detect = json.loads(Path('graphify-out/.graphify_detect.json').read_text())
    all_files = [f for files in detect['files'].values() for f in files]
    from graphify.cache import check_semantic_cache
    cached_nodes, cached_edges, cached_hyperedges, uncached = check_semantic_cache(all_files)
    
    if cached_nodes or cached_edges or cached_hyperedges:
        Path('graphify-out/.graphify_cached.json').write_text(json.dumps({'nodes': cached_nodes, 'edges': cached_edges, 'hyperedges': cached_hyperedges}))
    uncached_files = [Path(f) for f in uncached]
else:
    uncached_files = [Path(line.strip()) for line in uncached_path.read_text().splitlines() if line.strip()]

print(f"Loaded {len(uncached_files)} uncached files for semantic extraction.")

if not uncached_files:
    print("No uncached files to extract.")
    results = {'nodes': [], 'edges': [], 'hyperedges': [], 'input_tokens': 0, 'output_tokens': 0}
else:
    # 3. Run extract_corpus_parallel with gemini-2.5-flash
    print("Starting semantic extraction via Gemini (gemini-2.5-flash)...")
    results = gllm.extract_corpus_parallel(
        files=uncached_files,
        backend="gemini",
        api_key=api_key,
        model="gemini-2.5-flash",
        root=Path('.'),
        max_concurrency=5
    )

# 4. Save results to a temporary new file
new_semantic_path = Path('graphify-out/.graphify_semantic_new.json')
new_semantic_path.write_text(json.dumps(results, indent=2))
print(f"Extraction complete. New nodes: {len(results.get('nodes', []))}, New edges: {len(results.get('edges', []))}")

# 5. Load cached semantic results if any
cached_path = Path('graphify-out/.graphify_cached.json')
cached_data = {'nodes': [], 'edges': [], 'hyperedges': []}
if cached_path.exists():
    try:
        cached_data = json.loads(cached_path.read_text())
        print(f"Loaded cached data: {len(cached_data.get('nodes', []))} nodes, {len(cached_data.get('edges', []))} edges")
    except Exception as e:
        print(f"Failed to load cached data: {e}")

# 6. Merge cached and new
all_nodes = cached_data.get('nodes', []) + results.get('nodes', [])
all_edges = cached_data.get('edges', []) + results.get('edges', [])
all_hyperedges = cached_data.get('hyperedges', []) + results.get('hyperedges', [])

seen = set()
deduped_nodes = []
for n in all_nodes:
    if n['id'] not in seen:
        seen.add(n['id'])
        deduped_nodes.append(n)

merged_semantic = {
    'nodes': deduped_nodes,
    'edges': all_edges,
    'hyperedges': all_hyperedges,
    'input_tokens': results.get('input_tokens', 0) + cached_data.get('input_tokens', 0) if 'input_tokens' in cached_data else results.get('input_tokens', 0),
    'output_tokens': results.get('output_tokens', 0) + cached_data.get('output_tokens', 0) if 'output_tokens' in cached_data else results.get('output_tokens', 0),
}

# 7. Write to .graphify_semantic.json
semantic_path = Path('graphify-out/.graphify_semantic.json')
semantic_path.write_text(json.dumps(merged_semantic, indent=2))
print(f"Merged semantic results written: {len(deduped_nodes)} nodes, {len(all_edges)} edges.")

# 8. Clean up cached files if exists
if new_semantic_path.exists():
    new_semantic_path.unlink()
if cached_path.exists():
    cached_path.unlink()
if uncached_path.exists():
    uncached_path.unlink()

print("Semantic extraction pipeline completed successfully.")
