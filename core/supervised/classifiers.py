### Daniel Kronovet
### dbk2123@columbia.edu

'''
This is the classifiers module of the library.

All functions currently operate on a pandas DataFrame or Series.

Definitions:
class: one of the discrete values we assign to a data point.
label: a specific assignment of a class to a data point.
'''

import math
import random
random.seed('Abracadabra')

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.linalg import sqrtm


LABEL_COL = 0 # 0 is the name of the sole column in the labels dataframe

class Classifier(object):
    '''Classifier parent class.
    All children must implement a classify() method which takes in a single
    data point as a pd.Series and returns a class prediction.
    '''
    def __init__(self, X_train, label_train, X_test=None, label_test=None, Q=None):
        self.X_train = X_train
        self.label_train = self.to_series(label_train)
        self.X_test = X_test if X_test is not None else X_train
        self.label_test = self.to_series(label_test if label_test is not None else label_train)
        self.Q = Q
        self.classes = list(set(self.label_train))
        self.predictions = None
        self.confusion_matrix = None
        self.misclassifications = []

    def to_series(self, obj):
        return obj[0] if isinstance(obj, pd.DataFrame) else obj

    def run_all(self):
        self.classify_all()
        print self.get_confusion_matrix()
        return self.prediction_accuracy()

    def classify_all(self, X_test=None):
        '''Classify all data points in matrix X_test.'''
        # self.predictions = X.T.apply(self.classify)
        X_test = X_test if X_test is not None else self.X_test
        self.predictions = pd.Series(index=X_test.index)
        for i in X_test.index:
            if not i % 100: print 'Predicting value for x_{}'.format(i)
            self.predictions.ix[i] = self.classify(X_test.ix[i])
        return self.predictions

    def get_confusion_matrix(self, label_test=None):
        '''Create confusion matrix for classifier.
                   predicted_class
        true_class      value
        '''
        label_test = label_test if label_test is not None else self.label_test
        predictions = self.predictions

        if predictions is None:
            print 'Need predictions to generate confusion matrix!'
            return
        assert len(label_test) == len(predictions), 'Test and prediction not aligned!'
            
        classes = self.classes
        cm = pd.DataFrame([classes for _ in classes], columns=classes, index=classes) - classes
        for i in predictions.index:
            prediction = predictions[i]
            label = label_test[i]
            cm[prediction][label] += 1
            if prediction != label:
                m = {'i': i, 'label': label, 'prediction': prediction}
                self.misclassifications.append(m)
        self.confusion_matrix = cm
        return cm

    def prediction_accuracy(self):
        return self.get_trace(self.confusion_matrix) / float(len(self.label_test))

    def get_trace(self, matrix):
        return sum([matrix[i][i] for i in matrix.index])

    def get_class_data(self, _class):
        return self.X_train[self.get_class_index(_class)]

    def get_class_index(self, _class):
        return self.label_train == _class

    def dimensions(self, sample=None):
        sample = sample if sample is not None else self.X_train
        return sample.iloc[0].index

    def draw_image(self, x):
        image = self.Q.dot(x).reshape(28, 28)
        plt.imshow(image)


######################
### KNN Classifier ###
######################
class KNN(Classifier):
    def __init__(self, *args, **kwargs):
        super(KNN, self).__init__(*args, **kwargs)
        self.k = 3

    def classify(self, x):
        centered_X = self.X_train - x
        # distances = centered_X.T.apply(get_euclidean_norm)
        distances = (centered_X ** 2).T.sum().apply(math.sqrt)
        distances.sort()
        knn = distances.iloc[:self.k].index
        labels = self.label_train.ix[knn]
        counts = labels.groupby(labels).count()
        counts.sort()
        return counts.index[0]

### Norms and distances
def get_euclidean_distance(u, v):
    '''u, v are vectors of equal length'''
    # return math.sqrt(sum([(ui - vi) ** 2 for ui, vi in zip(u, v)]))
    return math.sqrt(((u - v) ** 2).sum())

def get_ln_norm(u, n):
    # return math.sqrt(sum([ui ** n for ui in u]))
    return math.sqrt((u ** n).sum())

def get_euclidean_norm(u):
    return get_ln_norm(u, 2)

########################
### Bayes Classifier ###
########################
class Bayes(Classifier):
    def __init__(self, *args, **kwargs):
        super(Bayes, self).__init__(*args, **kwargs)

    def _get_pi_hat(self, c):
        labels = self.label_train
        pi_hat = labels[labels == c].count() / float(len(labels))
        return pi_hat

    def _get_MLE_mean(self, sample):
        return sample.mean()

    def _get_MLE_cov(self, sample):
        mu = self._get_MLE_mean(sample)
        dim = self.dimensions(sample)
        n = len(dim)
        cov = pd.DataFrame(np.zeros(n**2).reshape(n,n), index=dim, columns=dim) 
        for x in sample.index:
            error = pd.DataFrame(sample.ix[x] - mu)
            cov += (error.dot(error.T))
        cov /= len(sample)
        return cov


class MultiClassBayes(Bayes):
    def __init__(self, *args, **kwargs):
        super(MultiClassBayes, self).__init__(*args, **kwargs)
        self.class_distributions = self.generate_class_distributions()

    def classify(self, x):
        densities = {
            self.likelihood_for_class(x, c): c 
            for c in self.class_distributions
            }
        return densities[max(densities)]

    def likelihood_for_class(self, x, _class):
        params = self.class_distributions[_class]
        pi, mu, Sigma = params['pi'], params['mu'], params['Sigma']
        error = (x - mu)
        exp = math.e ** (-0.5 * (error.T.dot(np.linalg.inv(Sigma)).dot(error)))
        inv_det_cov = 1. / math.sqrt(np.linalg.det(Sigma))
        return pi * inv_det_cov * exp

    def generate_class_distributions(self):
        return {c: self.generate_class_distribution(c) for c in self.classes}

    def generate_class_distribution(self, _class):
        train_class = self.get_class_data(_class)
        return {
            'pi': self._get_pi_hat(_class),
            'mu': self._get_MLE_mean(train_class),
            'Sigma': self._get_MLE_cov(train_class),
        }


class BinaryBayes(Bayes):
    def __init__(self, *args, **kwargs):
        super(BinaryBayes, self).__init__(*args, **kwargs)
        self.w = self.generate_w_vectors(combine=True)

    def generate_w_vectors(self, combine=False):
        k1 = self.get_class_data(1).drop(0, axis=1)
        k0 = self.get_class_data(-1).drop(0, axis=1)

        pi_k1 = self._get_pi_hat(1)
        pi_k0 = self._get_pi_hat(-1)
        mu_k1 = self._get_MLE_mean(k1)
        mu_k0 = self._get_MLE_mean(k0)
        Sigma = self._get_MLE_cov(k1.append(k0))

        w = self.calculate_w(mu_k0, mu_k1, Sigma)
        w0 = self.calculate_w0(pi_k0, pi_k1, mu_k0, mu_k1, Sigma)

        if combine:
            return pd.Series(np.insert(w, 0, w0))
        else:
            return w, w0

    def calculate_w(self, mu_0, mu_1, Sigma):
        return np.linalg.inv(Sigma).dot(mu_1 - mu_0)

    def calculate_w0(self, pi_0, pi_1, mu_0, mu_1, Sigma):
        return (np.log(pi_1 / pi_0)
                - (0.5 * ((mu_1 + mu_0).T.dot(np.linalg.inv(Sigma)).dot(mu_1 - mu_0))))

    def classify(self, x):
        fx = x.dot(self.w)
        return 1 if fx >= 0 else -1

    def classify_all(self, X_test=None):
        X_test = X_test if X_test is not None else self.X_test
        fX = X_test.dot(self.w)
        fX[fX >= 0] = 1
        fX[fX < 0] = -1
        self.predictions = fX
        return fX


#################################################
### Multiclass Logistic Regression Classifier ###
#################################################
class Logit(Classifier):
    def __init__(self, *args, **kwargs):
        super(Logit, self).__init__(*args, **kwargs)
        # self.eta = 0.1 / 50000
        self.eta = 0.1 / 5000
        self.X_train['w0'] = 1 # Absorb w0 intercept
        self.X_test['w0'] = 1 # Absorb w0 intercept
        self.W = self.prepare_W()
        self.log_likelihood_by_step = []

    def prepare_W(self):
        return pd.DataFrame({c: self.create_blank_w() for c in self.classes})

    def create_blank_w(self):
        return pd.Series(0, index=self.dimensions())

    def iterative_update(self, iterations=100):
        for i in range(iterations):
            if not i % 10: print 'Iteration {} of {}'.format(i, iterations)
            self.update_W()
            self.log_likelihood_by_step.append(self.log_likelihood())

    def update_W(self):
        '''w_t -> w_t+1'''
        for c in self.classes:
            class_data = self.X_train[self.label_train == c]
            gradient_likelihood = self.get_gradient_likelihood(class_data, c)
            self.W[c] += self.eta * gradient_likelihood

    def get_gradient_likelihood(self, class_data, _class):
        # Sum[x * (1 - (e**xTw / Sum[e**xTw)])]
        xTw = class_data.dot(self.W)
        softmax = self.softmax(xTw, _class)
        gradient_likelihoods = class_data.mul((1 - softmax), axis=0)
        return gradient_likelihoods.sum() 
        
    def softmax(self, xTw, _class):
        '''Give likelihood that data comes from _class

        num: e ^ xTw, with w coming from _class
        denom: Sum[e ^ xTw], summing across w from all classes
        '''
        beta = xTw.max(axis=1)
        num = math.e ** (xTw[_class] - beta)
        denom = (math.e ** (xTw.sub(beta, axis=0))).sum(axis=1)
        return num / denom

    def log_likelihood(self):
        XTW = self.X_train.dot(self.W) # d x c matrix (5000 x 10)
        log_sums = (math.e ** XTW).sum(axis=1).apply(math.log)
        ll = 0
        for c in self.classes:
            cindex = self.get_class_index(c)
            lls = XTW[cindex][c].sub(log_sums[cindex], axis=0)
            ll += lls.sum()
        return ll

    def classify_all(self, X_test=None):
        X_test = not X_test is None or self.X_test
        self.predictions = pd.Series(index=X_test.index)
        XTW = self.X_test.dot(self.W) # d x c matrix (5000 x 10)
        sums = (math.e ** XTW).sum(axis=1)
        class_odds = XTW.div(sums, axis=0)
        for i in class_odds.index:
            x_odds = class_odds.ix[i].copy()
            x_odds.sort(ascending=False)
            prediction = x_odds.index[0]
            self.predictions[i] = prediction

    # def update_W(self):
    #     '''w_t -> w_t+1'''
    #     for c in self.classes:
    #         print 'Updating w_{}'.format(c)
    #         self.W[c] += self.eta * self.get_gradient_likelihood(c)
    #     self.log_likelihood_by_step.append(self.log_likelihood())

    # def get_gradient_likelihood(self, _class):
    #     class_train = self.get_class_data(_class)
    #     gradient_likelihood = self.create_blank_w()
    #     for i in class_train.index:
    #         x = class_train.ix[i]
    #         gradient_likelihood += x * (1 - self.softmax(x, _class))
    #     return gradient_likelihood

    # def softmax(self, x, _class):
    #     num = math.e ** (x.dot(self.W[_class]))
    #     denom = self.total_probability(x)
    #     return num / denom

    # def total_probability(self, x):
    #     return sum([math.e ** (x.dot(w)) for w in self.W.values()])      

    # def log_likelihood(self):
    #     likelihood = 0
    #     for c in self.classes:
    #         class_data = self.get_class_data(c)
    #         for i in class_data.index:
    #             likelihood += self._log_likelihood_for_x(class_data.ix[i], c)
    #     return likelihood

    # def _log_likelihood_for_x(self, x, _class):
    #     return x.dot(self.W[_class]) - math.log(self.total_probability(x))

##################################
### Binary Logistic Regression ###
##################################
class BinaryLogit(Classifier):
    def __init__(self, *args, **kwargs):
        super(BinaryLogit, self).__init__(*args, **kwargs)
        self.w = self.prepare_w()
        self.train()

    def prepare_w(self):
        return pd.Series(0, index=self.dimensions())

    def train(self, n=1000):
        # self.eta = 0.1/50000
        self.eta = 0.1
        for i in range(n):
            if not i % 10: print 'Iteration {} of {}'.format(i, n)
            self.update_w()

    def update_w(self):
        X, y = self.X_train, self.label_train
        yX = X.mul(y, axis=0)
        step = yX.mul((1 - self.sigma(yX)), axis=0).sum()
        self.w += self.eta * step

    def sigma(self, x):
        return 1 / (1 + (math.e ** -(x.dot(self.w))))

    def classify_all(self, X=None):
        X = X if X is not None else self.X_test
        fX = self.sigma(X)
        fX[fX >= 0.5] = 1
        fX[fX < 0.5] = -1
        self.predictions = fX
        return fX


class OnlineBinaryLogit(BinaryLogit):
    def __init__(self, *args, **kwargs):
        super(OnlineBinaryLogit, self).__init__(*args, **kwargs)

    def prepare_w(self):
        return pd.Series(0, index=self.dimensions())

    def update_w(self, i):
        x, y = self.X_train.ix[i], self.label_train.ix[i]
        step = (1 - self.sigma(y*x)) * (y*x)
        self.w += (self.eta * step)

    def train(self):
        self.eta = 0.1
        self.stream = list(self.X_train.index)
        random.shuffle(self.stream)
        while self.stream:
            self.step()

    def step(self):
        i = self.stream.pop()
        self.update_w(i)




