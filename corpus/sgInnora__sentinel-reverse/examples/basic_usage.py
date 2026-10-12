#!/usr/bin/env python3
"""
Basic usage example for sentinel-reverse Python API.

This example demonstrates:
1. Creating a function context from disassembly
2. Computing GPU-accelerated embeddings
3. Finding similar functions
4. Predicting function names
"""

from sentinel_reverse.engine.mps_accelerator import MPSAccelerator

def main():
    # Initialize MPS accelerator (works in CPU fallback too)
    accel = MPSAccelerator(embedding_dim=256)
    print(f"Device: {accel.get_stats()['device']}")
    print(f"MPS available: {accel.get_stats()['mps_available']}")

    # Example function disassembly snippets
    functions = [
        (0x401000, "push rbp\nmov rbp, rsp\nsub rsp, 0x20\nmov [rbp-8], rdi\ncall malloc\nmov [rbp-16], rax\npop rbp\nret"),
        (0x401100, "push rbp\nmov rbp, rsp\nmov rdi, [rbp-8]\ncall free\npop rbp\nret"),
        (0x401200, "push rbp\nmov rbp, rsp\nsub rsp, 0x30\nmov [rbp-8], rdi\ncall malloc\nmov [rbp-16], rax\npop rbp\nret"),
        (0x401300, "push rbp\nmov rbp, rsp\nxor eax, eax\nmov ecx, 0x100\nrep stosb\npop rbp\nret"),
    ]

    # Compute embeddings (batch)
    print("\n--- Computing embeddings ---")
    embeddings = accel.batch_compute_embeddings(functions)
    for emb in embeddings:
        print(f"  0x{emb.address:x}: dim={emb.dimension}, time={emb.elapsed_ms:.1f}ms")

    # Find similar functions
    print("\n--- Finding similar functions ---")
    for i, emb in enumerate(embeddings):
        matches = accel.find_similar_functions(
            emb.embedding, embeddings, top_k=3, threshold=0.7
        )
        # Filter self-match
        matches = [m for m in matches if m.target_address != emb.address]
        if matches:
            for m in matches:
                print(f"  0x{emb.address:x} ~ 0x{m.target_address:x}: "
                      f"score={m.similarity_score:.4f} ({m.match_type})")

    # Predict function names
    print("\n--- Function name predictions ---")
    for emb in embeddings:
        pred = accel.predict_function_name(emb.embedding, address=emb.address)
        print(f"  0x{emb.address:x}: {pred.predicted_name} "
              f"[{pred.category}] conf={pred.confidence:.2f}")

    print(f"\nStats: {accel.get_stats()}")


if __name__ == "__main__":
    main()
