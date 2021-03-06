#!/usr/bin/python

# avenir-python: Machine Learning
# Author: Pranab Ghosh
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may
# obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0 
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.

# Package imports
import os
import sys
import matplotlib.pyplot as plt
import numpy as np
import torch
import torchvision
from torch import nn
from torch.autograd import Variable
from torch.utils.data import DataLoader
from torchvision import transforms
import sklearn as sk
import matplotlib
import random
import jprops
from random import randint
sys.path.append(os.path.abspath("../lib"))
from util import *
from mlutil import *


class LstmPredictor(nn.Module):
    def __init__(self, configFile):
    	"""
    	In the constructor we instantiate two nn.Linear modules and assign them as
    	member variables.
    	"""
    	defValues = dict()
    	defValues["common.mode"] = ("training", None)
    	defValues["common.model.directory"] = ("model", None)
    	defValues["common.model.file"] = (None, None)
    	defValues["common.preprocessing"] = (None, None)
    	defValues["common.verbose"] = (False, None)
    	defValues["common.device"] = ("cpu", None)
    	defValues["train.data.file"] = (None, "missing training data file path")
    	defValues["train.data.type"] = ("numeric", None)
    	defValues["train.data.col"] = (0, None)
    	defValues["train.input.size"] = (None, "missing  input size")
    	defValues["train.hidden.size"] = (None, "missing  hidden size")
    	defValues["train.output.size"] = (None, "missing  output size")
    	defValues["train.num.layers"] = (1, None)
    	defValues["train.seq.len"] = (1, None)
    	defValues["train.batch.size"] = (1, None)
    	defValues["train.drop.prob"] = (0, None)
    	defValues["train.text.vocab.size"] = (-1, None)
    	defValues["train.text.embed.size"] = (-1, None)
    	defValues["train.optimizer"] = ("adam", None) 
    	defValues["train.learning.rate"] = (.0001, None)
    	defValues["train.betas"] = ("0.9, 0.999", None)
    	defValues["train.eps"] = (1e-8, None)
    	defValues["train.weight.decay"] = (.00001, None)
    	defValues["train.momentum"] = (0, None)
    	defValues["train.momentum.nesterov"] = (False, None)
    	defValues["train.out.activation"] = ("sigmoid", None)
    	defValues["train.loss"] = ("mse", None) 
    	defValues["train.grad.clip"] = (5, None) 
    	defValues["train.num.iterations"] = (500, None) 

    	self.config = Configuration(configFile, defValues)
  
    	super(LstmClassify, self).__init__()
    	
    def getConfig(self):
    	return self.config
    	
    def buildModel(self):
    	"""
    	Loads configuration and builds the various piecess necessary for the model
    	"""
    	self.inputSize = self.config.getIntConfig("train.input.size")[0]
    	self.outputSize = self.config.getIntConfig("train.output.size")[0]
    	self.nLayers = self.config.getIntConfig("train.num.layers")[0]
    	self.hiddenSize = self.config.getIntConfig("train.hidden.size")[0]
    	self.seqLen = self.config.getIntConfig("train.seq.len")[0]
    	self.batchSize = self.config.getIntConfig("train.batch.size")[0]
    	vocabSize = self.config.getIntConfig("train.text.vocab.size")[0]
    	if vocabSize > 0:
    		embedSize = self.config.getIntConfig("train.text.vocab.size")[0]
    		self.embedding = nn.Embedding(vocabSize, embedSize)
    	else:
    		self.embedding = None
    	dropProb = self.config.getFloatConfig("train.drop.prob")[0]
    	self.lstm = nn.LSTM(self.inputSize, self.hiddenSize, self.nLayers, dropout=dropProb, batch_first=True)
    	self.dropout = nn.Dropout(dropProb)
    	self.linear = nn.Linear(self.hiddenSize, self.outputSize)
    	outAct = self.config.getStringConfig("train.out.activation")[0]
    	if outAct == "sigmoid":
    		self.outAct = nn.Sigmoid()
    	else :
    		self.outAct = None
    	

    def forward(self, x, h):
    	"""
    	Forward pass
    	"""
    	if self.embedding:
    		x = self.embedding(x)
    	lstmOut, hout = self.lstm(x,h)
    	lstmOut = lstmOut.contiguous().view(-1, self.hiddenSize)
    	out = self.dropout(lstmOut)
    	out = self.linear(out)
    	if self.outAct:
    		out = self.outAct(out)
    	out = out.view(self.batchSize, -1)
    	out = out[:,-1]
    	return out, hout
    
    def initHidden(self):
    	"""
    	Initialize hidden weights
    	"""
    	self.hiddenCell = (torch.zeros(self.nLayers,self.batchSize,self.hiddenSize),
                            torch.zeros(self.nLayers,self.batchSize,self.hiddenSize))
                            
    def createOptomizer(self):
    	"""
    	Create optimizer
    	"""
    	optimizerName = self.config.getStringConfig("train.optimizer")[0]
    	learnRate = self.config.getFloatConfig("train.learning.rate")[0]
    	weightDecay = self.config.getFloatConfig("train.weight.decay")[0]
    	if optimizerName == "adam":
    		betas = self.config.getStringConfig("train.betas")[0]
    		betas = strToFloatArray(self.betas, ",")
    		betas = (betas[0], betas[1]) 
    		eps = self.config.getFloatConfig("train.eps")[0]
    		optimizer = torch.optim.Adam(self.parameters(), lr=learnRate, betas=betas, eps = eps,
    		weight_decay=weightDecay)
    	elif optimizerName == "sgd":
    		momentum = self.config.getFloatConfig("train.momentum")[0]
    		dampening = self.config.getFloatConfig("train.dampening")[0]
    		momentumNesterov = self.config.getBooleanConfig("train.momentum.nesterov")[0]
    		optimizer = torch.optim.SGD(self.parameters(), momentum=momentum, dampening=dampening,
    		weight_decay=weightDecay, nesterov=momentumNesterov)
    	else:
    		raise ValueError("invalid optimizer type")
    	return optimizer
    	
    def createLossFun(self):
    	"""
    	Create loss function
    	"""
    	loss = self.config.getStringConfig("train.loss")[0]
    	if loss == "mse":
    		criterion = nn.MSELoss()
    	elif loss == "ce":
    		criterion = nn.CrossEntropyLoss()
    	elif loss == "bce":
    		criterion = nn.BCELoss()
    	else:
    		raise ValueError("invalid loss function")
    	return criterion
    	
    def trainLstm(self):
    	"""
    	train lstm
    	"""
    	self.train()
    	dataFile = self.config.getStringConfig("train.data.file")[0]
    	dataType = self.config.getStringConfig("train.data.type")[0]
    	if dataType == "numeric":
    		dataCol = self.config.getIntConfig("train.data.col")[0]
    		trainData = createLabeledSeq(dataFile, ",", dataCol, self.seqLen)
    	else:
    		raise ValueError("invalid data type")
    	trainData = torch.utils.data.TensorDataset(torch.from_numpy(np.array(trainData[0])), torch.from_numpy(np.array(trainData[1])))
    	trainLoader = DataLoader(trainData, shuffle=True, batch_size=self.batchSize)
    	
    	device = self.config.getStringConfig("common.device")[0]
    	self.to(device)
    	optimizer = self.createOptomizer()
    	criterion = self.createLossFun()
    	clip = self.config.getFloatConfig("train.grad.clip")[0]
    	numIter = self.config.getIntConfig("train.num.iterations")[0]
    	for it in range(numIter):
    		hid = model.initHidden()
    		for inputs, labels in trainLoader:
    			hid = tuple([e.data for e in hid])
    			inputs, labels = inputs.to(device), labels.to(device)
    			optimizer.zero_grad()
    			output, hid = model(inputs, hid)
    			loss = criterion(output.squeeze(), labels.float())
    			loss.backward()
    			nn.utils.clip_grad_norm_(model.parameters(), clip)
    			optimizer.step()
			
		
