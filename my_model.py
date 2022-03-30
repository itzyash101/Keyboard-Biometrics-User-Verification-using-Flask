import numpy as np
from random import uniform, randint

class fuzzy:

    def generate_dataset(self, key_data):
        dataset = []
        key_data1 = key_data.copy()
        for j in range(10):
            key_data_new = key_data1
            print("Key-Data:", key_data)
            for i in range(key_data_new.size):
                if randint(0, 1) == 0:
                    key_data_new[i] += uniform(0.005, 0.008)
                else:
                    key_data_new[i] -= uniform(0.005, 0.008)
            key_data_new[0] = 0
            key_data_new[-1] = 1
            dataset.append(key_data_new.copy())
            print("Generated Patterns:", dataset[j])
        self.dataset = dataset
    
    def threshold(self, key_data):
        stnd = []
        print("Key-data:", key_data)
        print("Dataset:", self.dataset[0])
        key_data = key_data.ravel()
        for pattern in self.dataset:
            print(key_data, pattern, sep = '\n')
            unit = np.vstack((key_data, pattern))
            print(unit)  #Perform vstacking
            s_dev = np.std(unit, axis = 0, dtype=float)
            #print(s_dev)
            stnd.append(np.mean(s_dev))
        print("Mean Std Deviations:", stnd)
        print("Mean of mean std deviations:", np.mean(np.array(stnd)))
        m_of_m = np.mean(np.array(stnd))
        print("Estimated Threshold Value:", m_of_m * 2)
        return m_of_m * 2
    
    def confidence(self, test_data, thresh):
        stnd = []
        tester = test_data.astype(float)
        for pattern in self.dataset:
            print(tester.shape[0], pattern.shape[0])
            unit = np.vstack((tester, pattern))  #Perform vstacking
            s_dev = np.std(unit, axis = 0)
            stnd.append(np.mean(s_dev))
        m_of_m = np.mean(np.array(stnd))
        if 1.5 * thresh >= m_of_m:
            confidence = 100
        else:
            thresh = float(thresh)
            if m_of_m < (3.0 * thresh):
                confidence = 100 - ((m_of_m / thresh) - 1) * 100 * 0.5 # Error is here
            else:
                confidence = 0
        return confidence