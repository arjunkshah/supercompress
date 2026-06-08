#!/usr/bin/env python3
"""Train the bundled SuperCompress checkpoint (~30s with --fast)."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from supercompress.features import FEATURE_DIM, build_feature_tensor
from supercompress.model import EvictionPolicyNetwork
from supercompress.oracle import build_token_records
from supercompress.simulator import generate_long_context


def generate_batch(n_contexts: int, rng: random.Random, np_rng) -> tuple[torch.Tensor, torch.Tensor]:
    xs, ys = [], []
    for _ in range(n_contexts):
        lines, question = generate_long_context(rng, target_tokens=rng.randint(200, 500))
        records = build_token_records(lines, question, np_rng)
        feats = build_feature_tensor(records, len(records))
        labels = torch.tensor([1.0 if r.is_oracle_important else 0.0 for r in records])
        xs.append(feats)
        ys.append(labels)
    max_len = max(x.shape[0] for x in xs)
    pad_x = torch.zeros(len(xs), max_len, FEATURE_DIM)
    pad_y = torch.zeros(len(xs), max_len)
    mask = torch.zeros(len(xs), max_len)
    for i, (x, y) in enumerate(zip(xs, ys)):
        pad_x[i, : x.shape[0]] = x
        pad_y[i, : y.shape[0]] = y
        mask[i, : x.shape[0]] = 1.0
    return pad_x, pad_y, mask


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Quick train (~30s)")
    parser.add_argument("--epochs", type=int, default=None)
    args = parser.parse_args()

    epochs = args.epochs or (40 if args.fast else 200)
    batch_contexts = 8 if args.fast else 16

    rng = random.Random(42)
    np_rng = np.random.default_rng(42)
    model = EvictionPolicyNetwork(feature_dim=FEATURE_DIM, hidden_dim=64)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    loss_fn = nn.BCEWithLogitsLoss(reduction="none")

    out = ROOT / "checkpoints" / "default.pt"
    out.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(epochs):
        x, y, mask = generate_batch(batch_contexts, rng, np_rng)
        opt.zero_grad()
        logits = model(x)
        loss = loss_fn(logits, y)
        loss = (loss * mask).sum() / mask.sum()
        loss.backward()
        opt.step()
        if (epoch + 1) % 10 == 0:
            print(f"epoch {epoch + 1}/{epochs} loss={loss.item():.4f}")

    torch.save(model.state_dict(), out)
    print(f"Saved checkpoint: {out}")


if __name__ == "__main__":
    main()
