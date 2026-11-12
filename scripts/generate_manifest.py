#!/usr/bin/env python3
"""Generate manifest.json for byte-split GGUF chunks."""

import json
import os
import glob

MODELS_DIR = "models"

def main():
    chunks = sorted(glob.glob(os.path.join(MODELS_DIR, "nanbeige-part-*.gguf")))
    if not chunks:
        raise SystemExit("No chunks found in models/")

    sizes = [os.path.getsize(c) for c in chunks]
    total = sum(sizes)

    manifest = {
        "model_name": "nanbeige-4.2b-q2k",
        "quant_type": "Q2_K",
        "format": "raw-gguf-byte-chunks",
        "total_size_bytes": total,
        "num_chunks": len(chunks),
        "chunk_size_bytes": sizes[0] if sizes else 0,
        "chunks": [os.path.basename(c) for c in chunks],
        "needle": "needle2.cact",
    }

    out_path = os.path.join(MODELS_DIR, "manifest.json")
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(json.dumps(manifest, indent=2))
    print(f"\nTotal: {total} bytes across {len(chunks)} chunks")
    print(f"Manifest written to {out_path}")

if __name__ == "__main__":
    main()
