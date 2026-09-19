import torch

# Ensure CUDA operations run reliably on cutting-edge architectures (e.g. RTX 50-series / CUDA 13)
# by using PyTorch's native high-performance CUDA convolution kernels when cuDNN version symbol mismatches occur.
if torch.cuda.is_available():
    torch.backends.cudnn.enabled = False
