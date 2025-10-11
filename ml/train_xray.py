import torch, torchvision
from torch import nn, optim
from torchvision import models, transforms
from PIL import Image
import os, numpy as np

class XRayCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.base = models.efficientnet_b0(pretrained=True)
        self.base.classifier[1] = nn.Linear(1280, 2)
    def forward(self, x): return self.base(x)

# training placeholder
print("✅ XRay model structure ready for training.")
