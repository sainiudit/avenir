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

class AutoEncoder(nn.Module):
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
		defValues["train.data.file"] = (None, "missing training data file")
		defValues["train.data.fields"] = (None, "missing training data field ordinals")
		defValues["train.data.feature.fields"] = (None, "missing training data feature field ordinals")
		defValues["train.data.out.fields"] = (None, "missing training data output field ordinals")
		defValues["train.num.input"] = (None, "missing number of input")
		defValues["train.num.hidden.units"] = (None, "missing number of hidden units for each layer")
		defValues["train.encoder.activations"] = (None, "missing encoder activation")
		defValues["train.decoder.activations"] = (None, "missing encoder activation")
		defValues["train.learning.rate"] = (.0001, None)
		defValues["train.weight.decay"] = (.00001, None)
		defValues["train.betas"] = ("0.9, 0.999", None)
		defValues["train.eps"] = (1e-8, None)
		defValues["train.momentum"] = (0, None)
		defValues["train.dampening"] = (0, None)
		defValues["train.batch.size"] = (128, None)
		defValues["train.momentum.nesterov"] = (False, None)
		defValues["train.noise.scale"] = (1.0, None)
		defValues["train.num.iterations"] = (500, None) 
		defValues["train.optimizer"] = ("adam", None) 
		defValues["train.loss"] = ("mse", None) 
		defValues["train.model.save"] = (False, None)
		defValues["encode.use.saved.model"] = (True, None)
		defValues["encode.data.file"] = (None, "missing enoding data file")
		self.config = Configuration(configFile, defValues)

		super(AutoEncoder, self).__init__()

	# get config object
	def getConfig(self):
		return self.config
        
	def buildModel(self):
		"""
    	Loads configuration and builds the various piecess necessary for the model
		"""
		self.device = self.config.getStringConfig("common.device")[0]
		self.numinp = self.config.getIntConfig("train.num.input")[0]
		self.numHidden = self.config.getStringConfig("train.num.hidden.units")[0].split(",")
		self.numHidden = toIntList(self.numHidden)
		numLayers = len(self.numHidden)
		self.encActivations = self.config.getStringConfig("train.encoder.activations")[0].split(",")
		self.decActivations = self.config.getStringConfig("train.decoder.activations")[0].split(",")
		self.learnRate = self.config.getFloatConfig("train.learning.rate")[0]
		self.batchSize = self.config.getIntConfig("train.batch.size")[0]
		self.weightDecay = self.config.getFloatConfig("train.weight.decay")[0]
		self.betas = self.config.getStringConfig("train.betas")[0]
		self.betas = strToFloatArray(self.betas, ",")
		self.eps = self.config.getFloatConfig("train.eps")[0]
		self.momentum = self.config.getFloatConfig("train.momentum")[0]
		self.dampening = self.config.getFloatConfig("train.dampening")[0]
		self.momentumNesterov = self.config.getBooleanConfig("train.momentum.nesterov")[0]
		self.noiseScale = self.config.getFloatConfig("train.noise.scale")[0]
		self.numIter = self.config.getIntConfig("train.num.iterations")[0]
		self.optimizer = self.config.getStringConfig("train.optimizer")[0]
		self.loss = self.config.getStringConfig("train.loss")[0]
		self.modelSave = self.config.getBooleanConfig("train.model.save")[0]
		self.useSavedModel = self.config.getBooleanConfig("encode.use.saved.model")[0]
		
		#featData = self.prepTrainingData()
		#self.featData = torch.from_numpy(featData)
		#self.dataloader = DataLoader(self.featData, batch_size=self.batchSize, shuffle=True)
		
		#encoder
		inSize = self.numinp
		enModules = list()
		for i in range(numLayers):
			outSize = self.numHidden[i]
			enModules.append(nn.Linear(inSize, outSize))
			act = self.encActivations[i]
			activation = self.createActivation(act)
			if activation:
				enModules.append(activation)
			inSize = outSize
		self.encoder = nn.ModuleList(enModules)
			
        #decoder
		deModules = list()
		j = 0
		for i in reversed(range(numLayers)):
			inSize = self.numHidden[i]
			if i > 0:
				outSize = self.numHidden[i-1]
			else:
				outSize = self.numinp
			deModules.append(nn.Linear(inSize, outSize))
			act = self.decActivations[j]
			j = j + 1
			activation = self.createActivation(act)
			if activation:
				deModules.append(activation)
		self.decoder = nn.ModuleList(deModules)

	def createActivation(self, act):
		"""
		create activation
		"""
		activation = None
		if act == "relu":
			activation = nn.ReLU()
		elif act == "sigmoid":
			activation = nn.Sigmoid()
		elif act == "noact":
			activation = None
		else:
			raise ValueError("invalid activation type")
	
	def forward(self, x):
		"""
		forward pass
		"""
		y = x
		for em in self.encoder:
			y = em(y)
		for dm in self.decoder:
			y = dm(y)
		return y

	def prepTrainingData(self):
		"""
		loads and prepares training data
		"""
		#training data
		dataFile = self.config.getStringConfig("train.data.file")[0]
		featData = np.loadtxt(dataFile, delimiter=",",dtype=np.float32)
		if (self.config.getStringConfig("common.preprocessing")[0] == "scale"):
			featData = sk.preprocessing.scale(featData)
		#print(type(featData))
		return featData

	def encode(self):
		"""
		encode
		"""
		if (self.useSavedModel):
			# load saved model
			print ("...loading saved model")
			modelFilePath = self.getModelFilePath()
			self.load_state_dict(torch.load(modelFilePath))
			self.eval()
		else:
			self.trainAe()
			
		dataFile = self.config.getStringConfig("encode.data.file")[0]
		enData = np.loadtxt(dataFile, delimiter=",", dtype=np.float32)
		enData = torch.from_numpy(enData)
		for x in enData:
			y = x
			for em in self.encoder:
				y = em(y)
			print(y)
	
	def getParams(self):
		"""
		get model parameters
		"""
		if (self.useSavedModel):
			# load saved model
			print ("...loading saved model")
			modelFilePath = self.getModelFilePath()
			self.load_state_dict(torch.load(modelFilePath))
			self.eval()
		else:
			self.trainAe()
	
	
		print("Model's state dict:")
		for paramTensor in self.state_dict():
			print(paramTensor)
			for te in self.state_dict()[paramTensor]:
				print(te)
				
	def getModelFilePath(self):
		""" 
		get model file path 
		"""
		modelDirectory = self.config.getStringConfig("common.model.directory")[0]
		modelFile = self.config.getStringConfig("common.model.file")[0]
		if modelFile is None:
			raise ValueError("missing model file name")
		modelFilePath = modelDirectory + "/" + modelFile
		return modelFilePath
		
	def trainAe(self):
		"""
		train model
		"""
		featData = self.prepTrainingData()
		self.featData = torch.from_numpy(featData)
		self.dataloader = DataLoader(self.featData, batch_size=self.batchSize, shuffle=True)

		if self.device == "cpu":
			model = self.cpu()
			
		# optimizer
		if model.optimizer == "adam":
			betas = (model.betas[0], model.betas[1]) 
			optimizer = torch.optim.Adam(model.parameters(), lr=model.learnRate, betas=betas, eps = model.eps,\
				weight_decay=model.weightDecay)
		elif model.optimizer == "sgd":
			optimizer = torch.optim.SGD(model.parameters(), momentum=model.momentum, dampening=model.dampening,\
				weight_decay=model.weightDecay, nesterov=model.momentumNesterov)
		else:
			raise ValueError("invalid optimizer type")
			
		# loss function
		if self.loss == "mse":
			criterion = nn.MSELoss()
		elif self.loss == "ce":
			criterion = nn.CrossEntropyLoss()
		else:
			raise ValueError("invalid loss function")
		
		for it in range(model.numIter):
			for data in self.dataloader:
				noisyData = data + model.noiseScale * torch.randn(*data.shape)
				output = model(noisyData)
				loss = criterion(output, data)
				optimizer.zero_grad()
				loss.backward()
				optimizer.step()
			print('epoch [{}/{}], loss {:.4f}'.format(it + 1, model.numIter, loss.data))

		if model.modelSave:
			modelFilePath = model.getModelFilePath()
			torch.save(model.state_dict(), modelFilePath)
		