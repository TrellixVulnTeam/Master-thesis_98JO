from torch import nn, from_numpy
import torch.nn.functional as F
from networks.net_utils import AbstractNetwork, Flatten, CustomLinear
import numpy as np


class synCNN(AbstractNetwork):

    def build_net(self):

        layers = []
        in_channels = 3
        for x in self.topology:
            layers += [
                nn.Conv2d(in_channels, x, kernel_size=3, padding=1, stride=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(x, x, kernel_size=3, padding=0, stride=1),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(kernel_size=2, stride=2, padding=0),
                nn.Dropout(0.25),
            ]
            in_channels = x

        layers = nn.Sequential(*layers)

        return layers

    def __init__(self, num_tasks, topology=None, incremental=False):
        super().__init__(outputs=num_tasks)

        if topology is None:
            topology = [32, 64]

        self.topology = topology
        self.incremental = incremental

        self.features = self.build_net()

        self.classification_layer = None

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        # x = self.features_processing(x)
        if self.classification_layer is None:
            self.classification_layer = nn.Linear(x.size()[1], self.output_size).to(x.device)

        x = self.classification_layer(x)

        mask = np.zeros(self.output_size)
        if self.incremental:
            for i in self.used_tasks:
                mask[i] = 1
        else:
            if isinstance(self._task, (list, tuple, set)):
                for i in self._task:
                    mask[i] = 1

        if mask.sum() != 0:
            x = x * from_numpy(mask).float().to(x.device)

        return x

    def eval_forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        # x = self.features_processing(x)
        if self.classification_layer is None:
            self.classification_layer = nn.Linear(x.size()[1], self.output_size).to(x.device)

        x = self.classification_layer(x)

        mask = np.zeros(self.output_size)
        if self.incremental:
            for i in self._used_tasks:
                mask[i] = 1
        else:
            if isinstance(self._task, (list, tuple, set)):
                for i in self._task:
                    mask[i] = 1

        if mask.sum() != 0:
            x = x * from_numpy(mask).float().to(x.device)

        return nn.functional.softmax(x, dim=1).max(dim=1)[1]

    def embedding(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        # x = self.features_processing(x)

        return x


class MLP(AbstractNetwork):
    def __init__(self, num_task, hidden_size=400):
        super(MLP, self).__init__(num_task)
        self.build_net(hidden_size=hidden_size)

    def build_net(self, *args, **kwargs):
        hidden_size = kwargs['hidden_size']
        self.fc1 = nn.Linear(28 * 28, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, hidden_size)
        self.fc4 = nn.Linear(hidden_size, self.output_size)

    def eval_forward(self, x, task=None):
        x = self.forward(x)
        return (nn.functional.softmax(x, dim=1).max(dim=1)[1]).cpu().detach().numpy()

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        return x

    def embedding(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        return x
