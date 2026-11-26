#!/usr/bin/env python3
"""Reassemble byte-split GGUF chunks back into a single model file."""
import json
import os

MODELS_DIR = "models"
MANIFEST_PATH = os.path.join(MODELS_DIR, "manifest.json")

def main():
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    chunks = manifest["chunks"]
    output_name = "nanbeige-reassembled.gguf"
    output_path = os.path.join(MODELS_DIR, output_name)

    print(f"Reassembling {len(chunks)} chunks → {output_path}")
    with open(output_path, "wb") as outfile:
        for chunk_name in chunks:
            chunk_path = os.path.join(MODELS_DIR, chunk_name)
            print(f"  appending {chunk_name} ({os.path.getsize(chunk_path)} bytes)")
            with open(chunk_path, "rb") as infile:
                # 1 MB buffer is fine
                while True:
                    buf = infile.read(1024 * 1024)
                    if not buf:
                        break
                    outfile.write(buf)

    total = os.path.getsize(output_path)
    print(f"Done. Total size: {total} bytes")
    assert total == manifest["total_size_bytes"], "Size mismatch after reassembly!"

if __name__ == "__main__":
    main()
