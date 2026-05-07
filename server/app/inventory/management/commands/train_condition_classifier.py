"""
Обучение головы ConvNeXt-Tiny на фиксированные классы состояния актива по фото.

Разметка: каталог CONDITION_TRAINING_DATA_DIR (см. settings / .env), по умолчанию рядом с manage.py:
  training_data/asset_condition/<slug>/
Подпапки (slug класса): см. inventory.ml.condition_classes.CLASS_SLUGS
Внутри каждой — изображения (.jpg, .jpeg, .png, .webp, .bmp).

Запуск из каталога с manage.py (обычно server/app):
  pip install torch torchvision  # если ещё не стоят (в Docker ml-worker уже есть)
  python manage.py train_condition_classifier

Веса сохраняются в CONDITION_CLASSIFIER_WEIGHTS (по умолчанию ``weights/asset_condition_convnext.pt`` рядом с manage.py).
"""

from __future__ import annotations

import random
from pathlib import Path
from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from inventory.ml.condition_classes import CLASS_SLUGS, NUM_CONDITION_CLASSES


def _collect_files(folder: Path, extensions: set[str]) -> list[Path]:
    out: list[Path] = []
    if not folder.is_dir():
        return out
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in extensions:
            out.append(p)
    return out


class _ImageListDataset:
    def __init__(self, items: list[tuple[Path, int]], transform):
        self.items = items
        self.transform = transform

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        path, label = self.items[idx]
        from PIL import Image

        img = Image.open(path).convert("RGB")
        return self.transform(img), label


class Command(BaseCommand):
    help = "Обучить ConvNeXt-Tiny (фиксированные классы) на фото из CONDITION_TRAINING_DATA_DIR"

    def add_arguments(self, parser):
        parser.add_argument("--epochs", type=int, default=15)
        parser.add_argument("--batch-size", type=int, default=8)
        parser.add_argument("--lr", type=float, default=1e-4)
        parser.add_argument("--val-ratio", type=float, default=0.15, help="Доля валидации из каждого класса")
        parser.add_argument(
            "--balance",
            type=str,
            default="auto",
            choices=("auto", "none", "sampler", "loss"),
            help="Балансировка классов при дисбалансе: auto|none|sampler|loss.",
        )
        parser.add_argument(
            "--imbalance-ratio",
            type=float,
            default=1.5,
            help="Порог дисбаланса (max/min) для режима auto.",
        )
        parser.add_argument("--jitter", type=float, default=0.15, help="Интенсивность ColorJitter (0 = выключить).")
        parser.add_argument("--rotation-deg", type=float, default=7.0, help="RandomRotation градусов (0 = выключить).")
        parser.add_argument("--affine-deg", type=float, default=5.0, help="RandomAffine degrees (0 = выключить).")
        parser.add_argument("--affine-translate", type=float, default=0.03, help="RandomAffine translate (0..1).")
        parser.add_argument("--affine-scale", type=float, default=0.05, help="RandomAffine scale jitter (0..1).")
        parser.add_argument("--erase-p", type=float, default=0.15, help="RandomErasing probability (0 = выключить).")
        parser.add_argument(
            "--data-dir",
            type=str,
            default="",
            help="Переопределить каталог с подпапками-классами (по умолчанию settings.CONDITION_TRAINING_DATA_DIR)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Куда сохранить .pt (по умолчанию settings.CONDITION_CLASSIFIER_WEIGHTS)",
        )

    def handle(self, *args, **options):
        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader
            from torchvision import transforms
            from torchvision.models import ConvNeXt_Tiny_Weights, convnext_tiny
        except ImportError as exc:
            raise CommandError(
                "Нужны torch и torchvision. Установите, например: "
                "pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu"
            ) from exc

        data_root = Path(options["data_dir"] or settings.CONDITION_TRAINING_DATA_DIR).expanduser()
        out_path = Path(options["output"] or settings.CONDITION_CLASSIFIER_WEIGHTS).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        per_class: dict[str, list[Path]] = {}
        for slug in CLASS_SLUGS:
            folder = data_root / slug
            files = _collect_files(folder, exts)
            if not files:
                raise CommandError(
                    f"В папке нет изображений: {folder}\n"
                    f"Ожидаются подкаталоги {', '.join(CLASS_SLUGS)} внутри {data_root}"
                )
            per_class[slug] = files

        items: list[tuple[Path, int]] = []
        val_items: list[tuple[Path, int]] = []
        rng = random.Random(42)
        for idx, slug in enumerate(CLASS_SLUGS):
            files = list(per_class[slug])
            rng.shuffle(files)
            n_val = max(1, int(len(files) * float(options["val_ratio"])))
            if len(files) <= 2:
                n_val = 0
            val_files = files[:n_val]
            train_files = files[n_val:]
            if not train_files:
                train_files = files
                val_files = []
            for p in train_files:
                items.append((p, idx))
            for p in val_files:
                val_items.append((p, idx))

        mean = (0.485, 0.456, 0.406)
        std = (0.229, 0.224, 0.225)
        aug: list = [transforms.RandomResizedCrop(224, scale=(0.8, 1.0)), transforms.RandomHorizontalFlip()]
        jitter = float(options["jitter"])
        if jitter > 0:
            aug.append(transforms.ColorJitter(brightness=jitter, contrast=jitter, saturation=jitter))
        rot = float(options["rotation_deg"])
        if rot > 0:
            aug.append(transforms.RandomRotation(degrees=rot))
        affine_deg = float(options["affine_deg"])
        if affine_deg > 0:
            translate = float(options["affine_translate"])
            scale = float(options["affine_scale"])
            aug.append(
                transforms.RandomAffine(
                    degrees=affine_deg,
                    translate=(translate, translate) if translate > 0 else None,
                    scale=(max(0.1, 1.0 - scale), 1.0 + scale) if scale > 0 else None,
                )
            )
        train_tf = transforms.Compose(
            [
                *aug,
                transforms.ToTensor(),
                transforms.Normalize(mean, std),
                transforms.RandomErasing(p=float(options["erase_p"])) if float(options["erase_p"]) > 0 else transforms.Lambda(lambda x: x),
            ]
        )
        val_tf = transforms.Compose(
            [
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean, std),
            ]
        )

        train_ds = _ImageListDataset(items, train_tf)
        val_ds = _ImageListDataset(val_items, val_tf) if val_items else None

        # Балансировка классов (sampler или веса в loss)
        labels = [y for _, y in items]
        counts = Counter(labels)
        min_c = min(counts.values()) if counts else 0
        max_c = max(counts.values()) if counts else 0
        ratio = (max_c / max(1, min_c)) if min_c else 1.0
        balance_mode = str(options["balance"]).lower()
        if balance_mode == "auto":
            balance_mode = "sampler" if ratio >= float(options["imbalance_ratio"]) else "none"

        sampler = None
        class_weights_tensor = None
        if balance_mode == "sampler" and counts:
            # Вес каждого примера = 1 / частота класса
            sample_weights = [1.0 / float(counts[y]) for y in labels]
            sampler = torch.utils.data.WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)
            self.stdout.write(self.style.NOTICE(f"Балансировка: sampler (imbalance_ratio={ratio:.2f})"))
        elif balance_mode == "loss" and counts:
            # Вес в loss = inv freq, нормализуем по среднему чтобы масштаб оставался привычным
            inv = [1.0 / float(counts.get(i, 1)) for i in range(NUM_CONDITION_CLASSES)]
            mean_inv = sum(inv) / max(1, len(inv))
            inv = [x / mean_inv for x in inv]
            class_weights_tensor = torch.tensor(inv, dtype=torch.float32)
            self.stdout.write(self.style.NOTICE(f"Балансировка: loss weights (imbalance_ratio={ratio:.2f})"))
        else:
            self.stdout.write(self.style.NOTICE(f"Балансировка: none (imbalance_ratio={ratio:.2f})"))

        train_loader = DataLoader(
            train_ds,
            batch_size=int(options["batch_size"]),
            shuffle=(sampler is None),
            sampler=sampler,
            num_workers=0,
            pin_memory=False,
        )
        val_loader = (
            DataLoader(val_ds, batch_size=int(options["batch_size"]), shuffle=False, num_workers=0, pin_memory=False)
            if val_ds
            else None
        )

        weights_enum = ConvNeXt_Tiny_Weights.IMAGENET1K_V1
        model = convnext_tiny(weights=weights_enum)
        last = model.classifier[-1]
        in_features = int(last.in_features)
        model.classifier[-1] = nn.Linear(in_features, NUM_CONDITION_CLASSES)

        for name, param in model.named_parameters():
            if not name.startswith("classifier"):
                param.requires_grad = False

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)
        opt = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=float(options["lr"]))
        loss_fn = nn.CrossEntropyLoss(weight=class_weights_tensor.to(device) if class_weights_tensor is not None else None)

        epochs = int(options["epochs"])
        self.stdout.write(self.style.NOTICE(f"Устройство: {device}; train={len(train_ds)} val={len(val_ds) if val_ds else 0}"))
        for epoch in range(1, epochs + 1):
            model.train()
            running = 0.0
            n_seen = 0
            for x, y in train_loader:
                x = x.to(device)
                y = y.to(device)
                opt.zero_grad()
                logits = model(x)
                loss = loss_fn(logits, y)
                loss.backward()
                opt.step()
                running += float(loss.item()) * x.size(0)
                n_seen += x.size(0)
            train_loss = running / max(1, n_seen)

            val_acc = None
            if val_loader is not None:
                model.eval()
                correct = 0
                total = 0
                with torch.no_grad():
                    for x, y in val_loader:
                        x = x.to(device)
                        y = y.to(device)
                        pred = model(x).argmax(dim=1)
                        correct += int((pred == y).sum().item())
                        total += x.size(0)
                val_acc = correct / max(1, total)

            if val_acc is not None:
                self.stdout.write(f"epoch {epoch}/{epochs}  train_loss={train_loss:.4f}  val_acc={val_acc:.4f}")
            else:
                self.stdout.write(f"epoch {epoch}/{epochs}  train_loss={train_loss:.4f}")

        torch.save(
            {
                "state_dict": model.state_dict(),
                "class_slugs": list(CLASS_SLUGS),
                "num_classes": NUM_CONDITION_CLASSES,
                "epochs": epochs,
                "train_samples": len(train_ds),
                "val_samples": len(val_ds) if val_ds else 0,
            },
            out_path,
        )
        self.stdout.write(self.style.SUCCESS(f"Сохранено: {out_path}"))
