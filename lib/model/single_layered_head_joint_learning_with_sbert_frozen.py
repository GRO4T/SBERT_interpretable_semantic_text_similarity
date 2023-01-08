from pytorch_lightning import LightningModule
import torch
import numpy as np

from lib.utils import TYPES_MAP
from lib.params import SBERT_EMBEDDING_WIDTH


class SingleLayeredHeadJointLearningWithSBERTFrozen(LightningModule):
    def __init__(
        self, sbert_model: str = "all-mpnet-base-v2", learning_rate: float = 0.001
    ):
        super().__init__()
        self._scoring_head = torch.nn.Linear(
            in_features=SBERT_EMBEDDING_WIDTH * 2, out_features=1
        )
        self._class_head = torch.nn.Linear(
            in_features=SBERT_EMBEDDING_WIDTH * 2, out_features=len(TYPES_MAP)
        )
        self._learning_rate = learning_rate
        self.save_hyperparameters()

    def _step(self, batch, batch_idx, id: str):
        x, y = batch
        y_hat = self.forward(x)
        return self.loss(y, y_hat, id)

    def forward(self, x):
        score = torch.reshape(self._scoring_head(x), (-1,))
        cls = torch.nn.functional.softmax(self._class_head(x), dim=1)

        return cls, score

    def loss(self, y, y_hat, id):
        # Klasa i ocena uczone razem
        scoring_loss = torch.nn.functional.mse_loss(y_hat[1], y[1])
        class_loss = torch.nn.functional.binary_cross_entropy_with_logits(
            y_hat[0], y[0]
        )
        return scoring_loss + class_loss

    def training_step(self, batch, batch_idx):
        loss = self._step(batch, batch_idx, "train")
        return loss

    def validation_step(self, batch, batch_idx):
        loss = self._step(batch, batch_idx, "val")
        return loss

    def test_step(self, batch, batch_idx):
        loss = self._step(batch, batch_idx, "test")
        return loss

    def predict_step(self, batch, batch_idx):
        x, y = batch
        types, scores = self.forward(x)

        return torch.argmax(types, dim=1), torch.clamp(
            torch.round(scores).int(), min=0, max=5
        )

    def configure_optimizers(self):
        return torch.optim.AdamW(self.parameters(), lr=self._learning_rate)