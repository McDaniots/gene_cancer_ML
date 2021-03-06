import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os.path

import torch
from torch import optim
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset,TensorDataset,DataLoader


from sklearn import preprocessing,utils,decomposition,metrics
from sklearn.preprocessing import LabelEncoder,OneHotEncoder
from sklearn.model_selection import train_test_split



import seaborn as sns

from time import time

###########################################
# load the dataset and drop useless columns
###########################################
print('Dataset loading...')

x = pd.read_csv("../data.csv")
y = pd.read_csv("../labels.csv")

# drop the first column which only contains strings
x = x.drop(x.columns[0], axis=1)
#drop first column, is only index
y = y.drop(y.columns[0], axis=1)

print('Done.')


# drop the first column which only contains strings
min_max_scaler = preprocessing.MinMaxScaler()
x = min_max_scaler.fit_transform(x)

#####################
#encoding y classes
#####################


print('Encoding...')

enc = LabelEncoder()
enc.fit(y)
y = enc.transform(y)
#print(y)

print('Done.')

#####################
#PCA
#####################

pca = decomposition.PCA(n_components=700)
x = pca.fit_transform(x)



##########################################
# split data into training and testing set
##########################################

print('Splitting..')

x_train, x_val, y_train, y_val \
    = train_test_split(x, y, test_size=0.2, random_state=42 ,stratify=y, shuffle=True)
   #
#For example, if variable y is a binary categorical variable with values 0 and 1 and there are 25% of zeros 
#and 75% of ones, stratify=y will make sure that your random split has 25% of 0's and 75% of 1's

print('Done.')


##################################
#Data Preparing for torch
##################################
torch.manual_seed(42)


x_train = torch.Tensor(x_train)
y_train = torch.tensor(y_train)
x_val = torch.Tensor(x_val)
y_val = torch.tensor(y_val)
y_val=y_val.long()
y_train=y_train.long()

##################################
#TensorDataset and DataLoader
##################################


bs=16



train_ds = TensorDataset(x_train, y_train)
val_ds = TensorDataset(x_val, y_val)

train_dl = DataLoader(train_ds, batch_size=bs, shuffle=True) #shuffle -> Shuffling the training data is important
#to prevent correlation between batches and overfitting
val_dl = DataLoader(val_ds, batch_size=bs) 

##################################
#Model defining
##################################

criterion = nn.CrossEntropyLoss()
epochs=200
lr=0.001

def init_weights(m):    # Funzione che inizializza i pesi dei layer nn.Linear() della rete definita con la funzione nn.Sequential()
    if type(m) == torch.nn.Linear:
        torch.nn.init.xavier_uniform_(m.weight)
        m.bias.data.fill_(0.01)

class Net(nn.Module):
    def __init__(self,in_size,n_hidden1,n_hidden2,n_hidden3,out_size,p=0):

        super(Net,self).__init__() #super dichiara di voler ereditare i metodi della classe nn.Module
        
        self.drop=nn.Dropout(p=p) #implementing dropout of p percentage
        
        self.linear1=nn.Linear(in_size,n_hidden1) #Linear -> fully connected layer
        self.linear2=nn.Linear(n_hidden1,n_hidden2)
        self.linear3=nn.Linear(n_hidden2,n_hidden3)
        self.linear4=nn.Linear(n_hidden3,out_size)
        
    def forward(self,x):
        x = x.view(x.size(0), -1) #view -> reshape the x tensor: -1 when you don't know a dimension, rehapes auto.
        x=F.relu(self.linear1(x))
        x=self.drop(x)
        x=F.relu(self.linear2(x))
        x=self.drop(x)
        x=F.relu(self.linear3(x))
        x=self.drop(x)
        x=self.linear4(x)
        return x

def get_model():
    model = Net(len(train_ds[1][0]),50,25,10,5,p=0.2)
    return model, optim.Adam(model.parameters(),betas=(0.9, 0.999), eps=1e-08,  lr=lr)
    #return model, optim.SGD(model.parameters(),  lr=lr,weight_decay=1e-6, momentum=0.9, nesterov=True)

model, opt = get_model()
print(model)


loss_train=[]
loss_val=[]

##################################
#Training
##################################
from IPython.core.debugger import set_trace #for debugging purposes
#(Note that we always call model.train() before training, and model.eval() before inference

start = time()

#weight initialization
model.apply(init_weights)

for epoch in range(epochs):
    
    model.train() #enter model in training mode: consider dropout and other stuff
    
    for xb, yb in train_dl:
        #set_trace() debug
       
        y_pred = model(xb)  # model(x) -> Forward pass: Compute predicted y by passing x to the model
        loss = criterion(y_pred, yb)
        
        loss_train.append(loss)
        print('epoch {}, loss {}'.format(epoch, loss))
         
        loss.backward() # perform a backward pass
        opt.step()      # update the weights
        opt.zero_grad() # Zero gradients
        

print("Training took %.2f seconds." % (time() - start))



##################################
#Confusion Matrix
##################################



with torch.no_grad():
    predict = model(x_val)
    predict = torch.argmax(predict, 1)
    predict=predict.numpy()

# confusion matrix of test set
print(y_val)
r = enc.inverse_transform(y_val)
print(r)
print(predict)
p = enc.inverse_transform(predict)
print(p)

cm = metrics.confusion_matrix(r, p)

# plot the results predictions on test set (confusion matrix)
class_names = ['BRCA', 'COAD', 'KIRC', 'LUAD', 'PRAD']
ax = plt.subplot()
sns.heatmap(cm, annot=True, ax=ax, cmap='Greys')
ax.set_xlabel('Predicted labels')
ax.set_ylabel('True labels')
ax.set_title('Confusion Matrix')
ax.xaxis.set_ticklabels(class_names)
ax.yaxis.set_ticklabels(class_names)
ax.set_xlim(0, 5)
ax.set_ylim(5, 0)

plt.show()

