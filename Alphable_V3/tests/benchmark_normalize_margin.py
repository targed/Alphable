import timeit
import torch
import math

def normalize_margin_pytorch(margin, margin_scale):
    return float(torch.tanh(torch.tensor(margin / margin_scale)).item())

def normalize_margin_math(margin, margin_scale):
    return math.tanh(margin / margin_scale)

def run_benchmark():
    margin = 50.0
    margin_scale = 100.0

    print("Benchmarking PyTorch version...")
    # warm up
    for _ in range(100):
        normalize_margin_pytorch(margin, margin_scale)

    t_pytorch = timeit.timeit(lambda: normalize_margin_pytorch(margin, margin_scale), number=100000)
    print(f"PyTorch version (100,000 runs): {t_pytorch:.6f} seconds")

    print("\nBenchmarking math version...")
    # warm up
    for _ in range(100):
        normalize_margin_math(margin, margin_scale)

    t_math = timeit.timeit(lambda: normalize_margin_math(margin, margin_scale), number=100000)
    print(f"Math version (100,000 runs): {t_math:.6f} seconds")

    print(f"\nSpeedup: {t_pytorch / t_math:.2f}x faster")

if __name__ == "__main__":
    run_benchmark()
