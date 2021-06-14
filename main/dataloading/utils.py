import torch
import torchvision
import numpy as np
import torchvision.transforms as T
import pytorch_lightning as pl
from torchvision.datasets import MNIST
from torch.utils.data import DataLoader, random_split
from pytorch_lightning.trainer.supporters import CombinedLoader
from randaugmentmc import RandAugmentMC
import torch.utils.data as D

from config import load_config
from paths import Path_Handler


class Circle_Crop(torch.nn.Module):
    """
    Set all values outside largest possible circle that fits inside image to 0
    """

    def __init__(self):
        super().__init__()

    def forward(self, img):
        """
        !!! Support for multiple channels not implemented yet !!!
        """
        H, W, C = img.shape[-1], img.shape[-2], img.shape[-3]
        assert H == W
        x = torch.arange(W, dtype=torch.float).repeat(H, 1)
        x = (x - 74.5) / 74.5
        y = torch.transpose(x, 0, 1)
        r = torch.sqrt(torch.pow(x, 2) + torch.pow(y, 2))
        r = r / torch.max(r)
        r[r < 0.5] = -1
        r[r == 0.5] = -1
        r[r != -1] = 0
        r = torch.pow(r, 2).view(C, H, W)
        assert r.shape == img.shape
        img = torch.mul(r, img)
        return img


def label_fraction(dset, label):
    loader = DataLoader(dset, len(dset))
    _, y = next(iter(loader))
    targets = np.asarray(y)
    n = np.count_nonzero(targets == label)
    return n / targets.size


def flip_targets(dset, fraction):
    # Get random flconfigipping indices
    targets = dset.data.targets
    n_targets = len(targets)
    n_flip = int(fraction * n_targets)
    targets = np.asarray(targets)
    flip_idx = np.random.randint(n_targets, size=n_flip)
    flip_labels = targets[flip_idx]

    # Change 1s to 0s and 0s to 1s #
    flipped_labels = (flip_labels - 1) ** 2

    # Reassign subarray with flipped labels and reassign dataset labels #
    targets[flip_idx] = flipped_labels
    dset.data.targets = targets
    return dset


def data_splitter(dset, fraction=1, split=1, val_frac=0.2):
    n = len(dset)
    idx = np.arange(n)
    # Shuffling is inplace
    np.random.shuffle(idx)

    data_dict, idx_dict = {"full": dset}, {"full": idx}

    # Reduce dataset #
    idx_dict["train_val"], idx_dict["rest"] = subindex(idx_dict["full"], fraction)

    # Split into train/val #
    idx_dict["val"], idx_dict["train"] = subindex(idx_dict["train_val"], val_frac)

    # Split into unlabelled/labelled #
    idx_dict["l"], idx_dict["u"] = subindex(idx_dict["train"], split)

    for key, idx in idx_dict.items():
        data_dict[key] = torch.utils.data.Subset(dset, idx)

    return data_dict, idx_dict


def subindex(idx, fraction):
    n = len(idx)
    n_sub = int(fraction * n)
    sub_idx, rest_idx = idx[:n_sub], idx[n_sub:]
    return sub_idx, rest_idx


def subset(dset, size):
    # fraction = fraction
    # length = len(dset)
    idx = np.arange(size)
    subset_idx = np.random.choice(idx, size=size)
    # subset_idx = np.random.choice(idx, size=int(fraction * length))
    return D.Subset(dset, subset_idx)


def size_cut(threshold, dset):
    length = len(dset)
    idx = np.argwhere(dset.sizes > threshold).flatten()
    dset.data = dset.data[idx, ...]
    dset.names = dset.names[idx, ...]
    dset.rgzid = dset.rgzid[idx, ...]
    dset.sizes = dset.sizes[idx, ...]
    dset.mbflg = dset.mbflg[idx, ...]


def mb_cut(dset):
    length = len(dset)
    idx = np.argwhere(dset.mbflg == 0)
    dset.data = dset.data[idx, ...]
    dset.names = dset.names[idx, ...]
    dset.rgzid = dset.rgzid[idx, ...]
    dset.sizes = dset.sizes[idx, ...]
    dset.mbflg = dset.mbflg[idx, ...]
    print(f"RGZ dataset cut to {len(dset)} samples")
