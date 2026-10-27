"""Train the real classifier (MobileNetV2 transfer learning).

Dataset layout (ImageFolder). Folder names MUST match keys in knowledge.py:
  data/train/potato_late_blight/*.jpg
  data/train/potato_healthy/*.jpg
  data/val/...  (same folders)

Run:  python train.py --data data --epochs 6
Outputs: backend/model/model.pt and backend/model/labels.json
Then restart the server; it switches from demo to real mode automatically.

Tip: evaluate on PlantDoc / your own field photos, not only a PlantVillage
validation split, and report both numbers.
"""
import argparse
import json
import os

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

p = argparse.ArgumentParser()
p.add_argument("--data", default="data")
p.add_argument("--epochs", type=int, default=6)
p.add_argument("--batch", type=int, default=32)
a = p.parse_args()

norm = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
train_tf = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.6, 1.0)), transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(0.3, 0.3, 0.3, 0.05), transforms.ToTensor(), norm])
val_tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(), norm])

train_ds = datasets.ImageFolder(os.path.join(a.data, "train"), train_tf)
val_ds = datasets.ImageFolder(os.path.join(a.data, "val"), val_tf)
train_dl = DataLoader(train_ds, batch_size=a.batch, shuffle=True, num_workers=2)
val_dl = DataLoader(val_ds, batch_size=a.batch, num_workers=2)

dev = "cuda" if torch.cuda.is_available() else "cpu"
model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
model.classifier[1] = nn.Linear(model.last_channel, len(train_ds.classes))
model.to(dev)
opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
loss_fn = nn.CrossEntropyLoss()

for ep in range(a.epochs):
    model.train()
    for x, y in train_dl:
        x, y = x.to(dev), y.to(dev)
        opt.zero_grad()
        loss_fn(model(x), y).backward()
        opt.step()
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for x, y in val_dl:
            pred = model(x.to(dev)).argmax(1).cpu()
            correct += (pred == y).sum().item()
            total += len(y)
    print(f"epoch {ep + 1}/{a.epochs}  val acc {correct / total:.3f}")

out = os.path.join(os.path.dirname(__file__), "backend", "model")
os.makedirs(out, exist_ok=True)
torch.save(model.cpu().state_dict(), os.path.join(out, "model.pt"))
json.dump(train_ds.classes, open(os.path.join(out, "labels.json"), "w"))
print("saved to", out)
