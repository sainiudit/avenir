/*
 * avenir: Predictive analytic based on Hadoop Map Reduce
 * Author: Pranab Ghosh
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); you
 * may not use this file except in compliance with the License. You may
 * obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0 
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 * implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */

package org.avenir.knn;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * @author pranab
 *
 */
public class Neighborhood {
    private String kernelFunction;
    private int kernelParam;
	private List<Neighbor>  neighbors = new ArrayList<Neighbor>();
	private Map<String, Integer> classDistr = new HashMap<String, Integer>();
	private static final int KERNEL_SCALE = 100;
	private static final int PROB_SCALE = 100;
	/**
	 * @param kernelFunction
	 * @param kernelParam
	 */
	public Neighborhood(String kernelFunction, int kernelParam) {
		this.kernelFunction = kernelFunction;
		this.kernelParam = kernelParam;
	}
	
	public void initialize() {
		neighbors.clear();
		classDistr.clear();
	}

	/**
	 * @param entityID
	 * @param distance
	 * @param classValue
	 */
	public void addNeighbor(String entityID, int distance, String classValue) {
		neighbors.add(new Neighbor(entityID, distance, classValue));
	}
	
	/**
	 * calculates class distribution
	 * @return
	 */
	public Map<String, Integer> getClassDitribution() {
		if (kernelFunction.equals("none")) {
			for (Neighbor neighbor : neighbors) {
				Integer count = classDistr.get(neighbor.classValue);
				if (null == count) {
					classDistr.put(neighbor.classValue, 1);
				} else {
					classDistr.put(neighbor.classValue, count + 1);
				}
			}
		} else if (kernelFunction.equals("linearMultiplicative")) {
			for (Neighbor neighbor : neighbors) {
				int currentScore = neighbor.distance == 0 ? (2 * KERNEL_SCALE) : (KERNEL_SCALE / neighbor.distance);
				Integer score = classDistr.get(neighbor.classValue);
				if (null == score) {
					classDistr.put(neighbor.classValue, currentScore);
				} else {
					classDistr.put(neighbor.classValue, score + currentScore);
				}
			}
		} else if (kernelFunction.equals("linearAdditive")) {
			for (Neighbor neighbor : neighbors) {
				int currentScore = (KERNEL_SCALE - neighbor.distance);
				Integer score = classDistr.get(neighbor.classValue);
				if (null == score) {
					classDistr.put(neighbor.classValue, currentScore);
				} else {
					classDistr.put(neighbor.classValue, score + currentScore);
				}
			}
		} else if (kernelFunction.equals("gaussian")) {
			for (Neighbor neighbor : neighbors) {
				double temp = (double)neighbor.distance  / kernelParam;
				double gaussian = Math.exp(-0.5 * temp * temp );
				int currentScore = (int)(KERNEL_SCALE  * gaussian);
				Integer score = classDistr.get(neighbor.classValue);
				if (null == score) {
					classDistr.put(neighbor.classValue, currentScore);
				} else {
					classDistr.put(neighbor.classValue, score + currentScore);
				}
			}
			
		} else if (kernelFunction.equals("sigmoid")) {
			
		}
		
		return classDistr;
	}
	
	/**
	 * Classify and return class attribute value
	 * @return
	 */
	public String classify() {
		int maxScore = 0;
		int thisScore;
		String winningClassVal = null;
		for (String classVal : classDistr.keySet()) {
			thisScore = classDistr.get(classVal);
			if (thisScore  > maxScore) {
				maxScore = thisScore; 
				winningClassVal = classVal;
			}
		}
		return winningClassVal;
	}
	
	/**
	 * return probability for given class attr value
	 * @param classAttrVal
	 * @return
	 */
	public int getClassProb(String classAttrVal) {
		int count = 0;
		for (String classVal : classDistr.keySet()) {
			count += classDistr.get(classVal);
		}		
		return (classDistr.get(classAttrVal) * PROB_SCALE) / count;
	}
	
	/**
	 * @author pranab
	 *
	 */
	private static class Neighbor {
		private String entityID;
		private int distance;
		private String classValue;
		
		public Neighbor(String entityID, int distance, String classValue) {
			this.entityID = entityID;
			this.distance = distance;
			this.classValue = classValue;
		}
		
	}

}