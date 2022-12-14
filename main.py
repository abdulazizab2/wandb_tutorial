import torch
import torch.nn as nn
from torch.autograd import Variable
import torchvision
from torchvision import transforms
import wandb
import os
import argparse

parser = argparse.ArgumentParser(description="wandb tutorial")
parser.add_argument("--wandb_user", type=str, required=True, help="wandb user name or team name")
parser.add_argument("--out_channels_layer1", type=int, default=32, help="out channels for layer")
parser.add_argument("--learning_rate", type=float, default=0.001, help="Learning rate")
args = parser.parse_args()

wandb.init(project="FashionMNIST", entity=args.wandb_user)

device = "cuda" if torch.cuda.is_available() else "cpu"

train_set = torchvision.datasets.FashionMNIST("./data", download=True, transform=
                                                transforms.Compose([transforms.ToTensor()]))
test_set = torchvision.datasets.FashionMNIST("./data", download=True, train=False, transform=
                                               transforms.Compose([transforms.ToTensor()])) 


train_loader = torch.utils.data.DataLoader(train_set,
                                           batch_size=100)
test_loader = torch.utils.data.DataLoader(test_set,
                                          batch_size=100)

def output_label(label):
    output_mapping = {
                 0: "T-shirt/Top",
                 1: "Trouser",
                 2: "Pullover",
                 3: "Dress",
                 4: "Coat", 
                 5: "Sandal", 
                 6: "Shirt",
                 7: "Sneaker",
                 8: "Bag",
                 9: "Ankle Boot"
                 }
    input = (label.item() if type(label) == torch.Tensor else label)
    return output_mapping[input]

class FashionCNN(nn.Module):

    def __init__(self, out_channels):
        super(FashionCNN, self).__init__()

        self.layer1 = nn.Sequential(
            nn.Conv2d(in_channels=1, out_channels=out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2)
        )

        self.layer2 = nn.Sequential(
            nn.Conv2d(in_channels=out_channels, out_channels=out_channels*2, kernel_size=3),
            nn.BatchNorm2d(out_channels*2),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )

        self.fc1 = nn.Linear(in_features=out_channels*2*6*6, out_features=600)
        self.drop = nn.Dropout2d(0.25)
        self.fc2 = nn.Linear(in_features=600, out_features=120)
        self.fc3 = nn.Linear(in_features=120, out_features=10)

    def forward(self, x):
        out = self.layer1(x)
        out = self.layer2(out)
        out = out.view(out.size(0), -1)
        out = self.fc1(out)
        out = self.drop(out)
        out = self.fc2(out)
        out = self.fc3(out)

        return out


model = FashionCNN(out_channels=args.out_channels_layer1)
model.to(device)

error = nn.CrossEntropyLoss()

learning_rate = args.learning_rate
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

num_epochs = 2
count = 0
# Lists for visualization of loss and accuracy
loss_list = []
iteration_list = []
accuracy_list = []

# Lists for knowing classwise accuracy
predictions_list = []
labels_list = []

for epoch in range(num_epochs):
    train_losses = []
    for images, labels in train_loader:
        # Transfering images and labels to GPU if available
        images, labels = images.to(device), labels.to(device)

        train = Variable(images.view(100, 1, 28, 28))
        labels = Variable(labels)

        # Forward pass
        outputs = model(train)
        loss = error(outputs, labels)
        train_losses.append(loss.item())

        # Initializing a gradient as 0 so there is no mixing of gradient among the batches
        optimizer.zero_grad()

        #Propagating the error backward
        loss.backward()

        # Optimizing the parameters
        optimizer.step()

        count += 1

    # Testing the model

        if not (count % 50):    # It's same as "if count % 50 == 0"
            total = 0
            correct = 0
            

            for images, labels in test_loader:
                images, labels = images.to(device), labels.to(device)
                labels_list.append(labels)

                test = Variable(images.view(100, 1, 28, 28))

                outputs = model(test)

                predictions = torch.max(outputs, 1)[1].to(device)
                predictions_list.append(predictions)
                correct += (predictions == labels).sum()

                total += len(labels)

            accuracy = correct * 100 / total
            loss_list.append(loss.data)
            iteration_list.append(count)
            accuracy_list.append(accuracy)

            print("Iteration: {}, Loss: {}, Accuracy: {}%".format(count, loss.data, accuracy))
            # wandb.log("train_loss": loss_list, "validation_accuracy": accuracy)
            wandb.log({"train_loss": loss.data}) # you can log multiple keys in the dictionary to monitor
            wandb.log({"val_acc": accuracy}) # since we are minimizing "val_acc" // log it alone