import os, torch, torchvision, numpy as np
from torch import nn, optim
from torchvision import transforms, datasets, models
from torch.utils.data import DataLoader
from tqdm import tqdm
import onnx

# ==============================================
# DrHealth Phase 5 – X-Ray Training Script
# ==============================================

DATA_DIR = "lib/ai_model/dataset"
MODEL_SAVE_PATH = "lib/ai_model/models/xray_model.onnx"
BATCH_SIZE = 16
EPOCHS = 3
IMG_SIZE = 224
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

train_tfms = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])
val_tfms = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])

train_ds = datasets.ImageFolder(os.path.join(DATA_DIR, "train"), transform=train_tfms)
val_ds = datasets.ImageFolder(os.path.join(DATA_DIR, "val"), transform=val_tfms)
train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
val_dl = DataLoader(val_ds, batch_size=BATCH_SIZE)

print(f"Loaded {len(train_ds)} training and {len(val_ds)} validation images.")

model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
in_feats = model.classifier[1].in_features
model.classifier[1] = nn.Linear(in_feats, 2)
model = model.to(DEVICE)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=1e-4)

for epoch in range(EPOCHS):
    model.train()
    train_loss = 0
    for imgs, labels in tqdm(train_dl, desc=f"Epoch {epoch+1}/{EPOCHS}"):
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(imgs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
    avg_loss = train_loss / len(train_dl)
    print(f"Epoch {epoch+1} | Train Loss: {avg_loss:.4f}")

model.eval()
correct = 0
with torch.no_grad():
    for imgs, labels in val_dl:
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
        outputs = model(imgs)
        preds = outputs.argmax(1)
        correct += (preds == labels).sum().item()
acc = correct / len(val_ds)
print(f"Validation Accuracy: {acc*100:.2f}%")

dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE).to(DEVICE)
torch.onnx.export(model, dummy, MODEL_SAVE_PATH,
                  input_names=["input"], output_names=["output"],
                  opset_version=17)
print(f"Model exported → {MODEL_SAVE_PATH}")
