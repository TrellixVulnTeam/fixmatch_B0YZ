import yaml
import torch.nn as nn
import torch.nn.functional as F
from torch import logsumexp
import torch
import numpy as np
import matplotlib.pyplot as plt
import pytorch_lightning as pl
import wandb

from PIL import Image
from mpl_toolkits.axes_grid1 import ImageGrid
from torch.utils.data import DataLoader

from paths import Path_Handler
from evaluation import pred_label_fraction, calculate_fid
from config import load_config

# Define paths
paths = Path_Handler()
path_dict = paths._dict()


config = load_config()


def entropy(p, eps=0.0000001, loss=False):
    """
    Calculate the entropy of a binary classification prediction given a probability for either of the two classes.

    Keyword arguments:
    eps -- small additive factor to avoid log(0)
    loss -- boolean value determines whether to return detached value for inference (False) or differentiable value for training (True)
    """
    H_i = -torch.log(p + eps) * p
    H = torch.sum(H_i, 1).view(-1)

    if not loss:
        # Clamp to avoid negative values due to eps
        H = torch.clamp(H, min=0)
        return H.detach().cpu().numpy()

    H = torch.mean(H)

    return H


def fig2img(fig):
    """Convert a Matplotlib figure to a PIL Image and return it"""
    import io

    buf = io.BytesIO()
    fig.savefig(buf, bbox_inches="tight")
    buf.seek(0)
    img = Image.open(buf)
    return img


def dset2tens(dset):
    """Return a tuple (x, y) containing the entire input dataset (carefuwith large datasets)"""
    return next(iter(DataLoader(dset, int(len(dset)))))


def flip(labels, p_flip):
    """Flip a number of labels"""
    n_labels = labels.shape[0]
    n_flip = int(p_flip * n_labels)
    if n_flip:
        idx = torch.randint(labels.shape[0], (n_flip))
    else:
        return labels


def compute_mu_sig(dset):
    """Compute mean and standard variance of a dataset (careful with large datasets)"""
    x, _ = dset2tens(dset)
    return torch.mean(x), torch.std(x)


def batch_eval(fn_dict, dset, batch_size=200):
    """
    Take functions which acts on data x,y and evaluates over the whole dataset in batches, returning a list of results for each calculated metric
    """
    n = len(dset)
    loader = DataLoader(dset, batch_size)

    # Fill the output dictionary with empty lists
    outs = {}
    for key in fn_dict.keys():
        outs[key] = []

    for x, y in loader:
        # Take only weakly augmented sample if passing through unlabelled data
        #        if strong_T:
        #            x = x[0]

        # Append result from each batch to list in outputs dictionary
        for key, fn in fn_dict.items():
            outs[key].append(fn(x, y))

    return outs
