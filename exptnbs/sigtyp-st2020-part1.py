# -*- coding: utf-8 -*-
"""SigTyp-st2020-prt1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/pkolachi/geodist2typfeat/blob/master/exptnbs/sigtyp-st2020-part1.ipynb
Imported on 2020/04/13 at 12:20pm
"""

# Commented out IPython magic to ensure Python compatibility.
# %autosave 60
# %matplotlib inline
fpurl   = 'https://raw.githubusercontent.com/sigtyp/ST2020/master/data/train.csv'
# the header from the csv is not properly tab-seperated. hence hard-coding
header  = ['wals_code', 'name', 
           'latitude', 'longitude', 
           'genus', 'family', 'countrycodes', 
           'features'
          ]

CVFOLDS = 2   # default: 2 folds
N = -1        # default: use all samples 
K = 5         # default: use only 5 feature classes
REPEAT  = -1
# turn this on iff running from command-line to test performance across 
# different values for (CVFOLDS, K, REPEAT) 
BATCH = True  

import itertools as it
from collections import Counter, defaultdict
from operator    import itemgetter
from IPython.display import display as pd_displayHTML

"""I hoped the provided train/test dataset is CSV compliant so that loading the dataset is as simple as using *pandas.read_csv*. It turned out not to be the case. The problem is with the header in the provided csv file, which makes inferring the columns using *header=auto* impossible. This is easily handled by hard-coding the column names in the header and skipping the first row when using *pandas.read_csv*."""

import sys
#!{sys.executable} -m pip install -q --user pandas
import pandas as pd
df = pd.read_csv(fpurl, sep='\t', header=None, names=header, 
                #index_col=0, 
                 error_bad_lines=True, skiprows=[0])
"""
# since this pynb will never be run on the held-out test set
if CVFOLDS <= 1:
  trnS, tstS = 0, 0   # dummy values for sizes of train and test partitions
else:
  tstdf = pd.read_csv(tstfpurl, sep='\t', header=None, names=header, 
                      error_bad_lines=True, skiprows=[0])
  trnS, tstS = df.shape[0], tstdf.shape[0]
  df.append(tstdf) 
"""
featsFull = df.iloc[:,0:-1]
clablFull = df.iloc[:,-1]
alablInst = Counter(albl for inst in clablFull for albl in inst.split('|'))
alablTabl = pd.DataFrame([{'name': n, 'id': i, 'freq': f}
                          for i,(n,f) in enumerate(alablInst.most_common())
                         ]).set_index('name')
alablFull = pd.DataFrame([dict(albl.split('=', 1) for albl in inst.split('|'))
                          for inst in clablFull
                         ])
for incol in ['wals_code', 'name', 'genus', 'family', 'countrycodes']:
  featsFull[incol] = featsFull[incol].astype('category')
clablFull = clablFull.astype('category')
alablFull = alablFull.astype('category')

print(featsFull.shape, clablFull.shape, alablFull.shape, alablTabl.shape)

"""Let's plot a few simple statistics about the dataset. 
1.   Histogram of the complex labels in the dataset
2.   Scatterplots of genus vs labels, family vs labels and countrycodes vs labels
"""

clablFull.name
clablFull.index

#!{sys.executable} -m pip install -q --user seaborn 
import seaborn as sns
def plot_datastats(features, clabels, alabels):
  return

if not BATCH:
  plot_datastats(featsFull, clablFull, alablFull)

"""The dataset is loaded into a DataFrame and seperated into two parts: input features and output labels. 

We know a few things about the input features like what are categorical features and what are numerical features. So, we encode the different columns in the feats DataFrame accordingly. *Hopefully this matters* when training different classifiers (especially thinking of decision trees). 

At this point, I'm not looking at best encoding scheme for the labels which are composite labels themselves (more on this later). The training dataset provided has 1109 unique labels for the dataset of 1125 languages. This indicates that there is *an optimal representation* for the label set.
"""

# sub-select data frame to speed-up experiments while debugging
import random
import numpy as np
# because we want sampling without replacement when we work with selected 
# features classes to test, using random makes statistics across runs 
# incomparable -- so use a uniform distribution to select feature classes for 
# comparison across different experiments. 
# to get robust estimates while testing, use random selection
if N < 2 or N > featsFull.shape[0]:
  subsid = list(range(featsFull.shape[0]))
else:
  subsid = list(range(0, featsFull.shape[0], featsFull.shape[0]//N))[:N]

if K < 0 or K > alablFull.shape[1]:
  subfci = list(range(alablFull.shape[1]))
else:
  subfci = list(sorted(random.sample(range(alablFull.shape[1]), K)))
  #subfci = list(range(0, alablFull.shape[1], alablFull.shape[1]//K))[:K])
subfcs = list(alablFull.columns[i] for i in subfci)

featsFull_ = featsFull.iloc[subsid,:]
clablFull_ = clablFull.iloc[subsid]
alablSub_  = alablFull.iloc[subsid,subfci]
alablFull_ = alablFull.iloc[subsid,:]

print(featsFull_.shape, clablFull_.shape, alablFull_.shape, alablSub_.shape)

# it is essential to make deep copies of the data in the dataframe when building
# the numerical matrices used for classification experiments. 
# if not, changes to feature matrices w.r.t. encoding categorial variables are 
# reflected in the original dataframe which results in errors when trying to 
# re-use the dataframes for other experiments
# e.g. lookup in the atomic-label table built above results in errors because 
# the lookup tries to find fnc=lbl-idx where idx is the category code 
X   = featsFull_.copy(deep=False)
ccs = X.select_dtypes(['category']).columns 
X[ccs] = X[ccs].apply(lambda x: x.cat.codes)

Y = clablFull_.copy(deep=False).cat.codes

Y_  = alablFull_.copy(deep=False)
ccs = Y_.select_dtypes(['category']).columns
Y_[ccs] = Y_[ccs].apply(lambda x: x.cat.codes)

subY_ = alablSub_.copy(deep=False)
ccs = subY_.select_dtypes(['category']).columns
subY_[ccs] = subY_[ccs].apply(lambda x: x.cat.codes)

X  = X.to_numpy()
Y  = Y.to_numpy()
Y_ = Y_.to_numpy()
subY_ = subY_.to_numpy()

print(X.shape, Y.shape, Y_.shape, subY_.shape)

"""Let us try a few classifiers using *scikit-learn* at this point. 

For what it is worth, the accuracies can be worse than a coin flip, considering the sparse label set.


 features of languages spoken in close proximity and belonging to the same family should be highly informative in predicting the typographical features for a new language.
"""

#!{sys.executable} -m pip install -q --user sklearn 
from sklearn.model_selection import KFold, RepeatedKFold
#from sklearn.model_selection import StratifiedKFold, RepeatedStratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.gaussian_process.kernels import RBF
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from sklearn.linear_model import RidgeClassifier
from sklearn.dummy import DummyClassifier

classifiers = {'knn':    KNeighborsClassifier(),
              #'lsvm':   SVC(kernel="linear"),
              #'rbfsvm': SVC(gamma=2),
              #'gp':     GaussianProcessClassifier(),
               'dt':     DecisionTreeClassifier(),
               'rf':     RandomForestClassifier(), #default worse than suggested values
               'mlp':    MLPClassifier(), #default worse than suggested values
               'adb':    AdaBoostClassifier(),
               'nb':     GaussianNB(),
              #'qda':    QuadraticDiscriminantAnalysis(),
               'ridge':  RidgeClassifier(),
               '-dumbase-': DummyClassifier(strategy="most_frequent") 
              }

statnames = ['Classifiers', 'Avg. Test-acc', 'Avg. Train-acc', 
             'Std. Test-acc',  'Std. Train-acc',
             'Avg. Test-time', 'Avg. Train-time'
            ]
statcodes = ['clfn', 'mtsts', 'mtrns', 'vtsts', 'vtrns', 'predt', 'trint']

REPEAT  = REPEAT  if REPEAT  >  1 else 1  # sanity-check
CVFOLDS = CVFOLDS if CVFOLDS >= 2 else 2  # sanity-check
# scikit-learn documentation recommends using StratifiedKFold for classification
# problems to preserve class balance across folds. however, in this case, 
# we use KFold and RepeatedKFold because 
#  number of items in a class <= CVFOLDS (works only with 2 folds for entire dataset)
#  there is not much balance to preserve w.r.t. complex labels
cvsplits = list(RepeatedKFold(n_splits=CVFOLDS, 
                              n_repeats=REPEAT, random_state=20200408
                             ).split(X, Y)
               )
print(len(cvsplits))

def plot_accuracies(accdf):
  sns.barplot(x="Classifiers", y="Avg. Test-acc", data=accdf)
  #ax2 = sns.barplot(x="Classifiers", y="Avg. Train accuracy", data=accdf)
  #ax2.set(ylim=(0, 100))
  return

#%%time
from sklearn import model_selection as skms

def trainFullClassifiersCV(classifiers, X, Y):
  clfaccs = []
  for iclf, nclf in enumerate(classifiers):
    clfsce = skms.cross_validate(classifiers[nclf], X, Y, cv=cvsplits, 
                                 return_train_score=True
                                )
    clfnfo = [nclf, 
              100*clfsce['test_score'].mean(), 100*clfsce['train_score'].mean(),
              100*clfsce['test_score'].std(),  100*clfsce['train_score'].std(),
              clfsce['score_time'].mean(), clfsce['fit_time'].mean()
             ]
    clfaccs.append(dict(zip(statnames, clfnfo)))
  return pd.DataFrame(clfaccs)

clfaccs = trainFullClassifiersCV(classifiers, X, Y)
if not BATCH:
  plot_accuracies(clfaccs)

# Commented out IPython magic to ensure Python compatibility.
from sklearn import metrics as skmt

def trainIndClassifiersCV(classifiers, X, matY, return_clfinsts=False):
  lclfinst  = {}  # table to store classifiers for later use
  lclfaccs = np.zeros((matY.shape[-1], len(classifiers), 6))
  avgcaccs = []
  for iclf, nclf in enumerate(classifiers):
    for indY in range(matY.shape[-1]):
      clfsce = skms.cross_validate(classifiers[nclf], X, matY[:,indY], cv=cvsplits,
                                   return_train_score=True, 
                                   return_estimator=return_clfinsts
                                  )
      lclfaccs[indY][iclf] = [100*clfsce['test_score'].mean(), 
                              100*clfsce['train_score'].mean(), 
                              100*clfsce['test_score'].std(),  
                              100*clfsce['train_score'].std(), 
                              clfsce['score_time'].mean(), 
                              clfsce['fit_time'].mean()
                             ]
      if return_clfinsts:
        lclfinst[(nclf, indY)] = clfsce['estimator']
    clfnfo = [nclf, 
              lclfaccs[:,iclf,0].mean(), lclfaccs[:,iclf,1].mean(),
              lclfaccs[:,iclf,2].mean(), lclfaccs[:,iclf,3].mean(),
              lclfaccs[:,iclf,4].sum(),  lclfaccs[:,iclf,5].sum()
             ]
    avgcaccs.append(dict(zip(statnames, clfnfo)))
  if return_clfinsts:
    return (pd.DataFrame(avgcaccs), lclfinst)
  else:
    return pd.DataFrame(avgcaccs)

# %time avgcaccs, lclclfs = trainIndClassifiersCV(classifiers, X, subY_, return_clfinsts=True)
if not BATCH:
  #print(avgcaccs.round(3).to_markdown(showindex=False))
  pd_displayHTML(avgcaccs.style.hide_index())
  plot_accuracies(avgcaccs)

# Commented out IPython magic to ensure Python compatibility.
clablSub = ['|'.join('{0}={1}'.format(k,v) for k,v in row.items() if not pd.isna(v))
            for row in alablSub_.to_dict(orient='records')
           ]
# sanity check to make sure subset of labels have been properly extracted
if all(True if nl=='' or l.find(sf)!=-1 else False
       for l,nl in zip(clablFull.values, clablSub) for sf in nl.split('|')):
  print('Sanity check passed')
else:
  print('Sanity check failed')
clablSub = pd.Series(clablSub, name=header[-1])
subY = clablSub.astype('category').cat.codes
subY = subY.to_numpy()
# %time sclfaccs = trainFullClassifiersCV(classifiers, X, subY)
if not BATCH:
  pd_displayHTML(sclfaccs.style.hide_index())
  plot_accuracies(sclfaccs)

# Commented out IPython magic to ensure Python compatibility.
def skmt_mlmc_accuracy_score(y_true, y_pred):
  "Classification accuracy for multi-label multi-class problems"
  n_samples = y_true.shape[0]
  return sum(1.0 if np.array_equal(y_true[i], y_pred[i]) else 0
             for i in range(n_samples)
            ) / n_samples

def jntTestIndClassifiersCV(classifiers, X, matY, clfinstances=None):
  if not clfinstances:
    _, clfinstances = trainIndClassifiersCV(classifiers, X, matY, return_clfinsts=True)
  trnpids = list(map(itemgetter(0), cvsplits))
  tstpids = list(map(itemgetter(1), cvsplits))
  predsst = lambda clf,sids: clf.predict(X[sids]).reshape((-1, 1))
  jclfaccs = []
  for iclf, nclf in enumerate(classifiers):
    tstpreds, trnpreds = [], []
    for cvid, (trnids,tstids) in enumerate(cvsplits):
      indpreds = list(it.starmap(predsst, [(clfinstances[nclf, indY][cvid], tstids)
                                            for indY in range(matY.shape[-1])
                                          ]))
      tstpreds.append(np.hstack(indpreds))
      indpreds = list(it.starmap(predsst, [(clfinstances[nclf, indY][cvid], trnids)
                                            for indY in range(matY.shape[-1])
                                          ]))  
      trnpreds.append(np.hstack(indpreds))
    
    tstaccs = 100*np.array([skmt_mlmc_accuracy_score(matY[sids], preds)
                            for sids, preds in zip(tstpids, tstpreds)
                           ])
    trnaccs = 100*np.array([skmt_mlmc_accuracy_score(matY[sids], preds)
                            for sids, preds in zip(trnpids, trnpreds)
                           ])
    clfnfo = [nclf, tstaccs.mean(), trnaccs.mean(), tstaccs.std(), trnaccs.std()]
    jclfaccs.append(dict(zip(statnames, clfnfo)))
  return pd.DataFrame(jclfaccs)

# %time jclfaccs = jntTestIndClassifiersCV(classifiers, X, subY_, clfinstances=lclclfs)
if not BATCH:
  pd_displayHTML(jclfaccs.style.hide_index())
  plot_accuracies(jclfaccs)

"""TODO: 

*   test other encoding schemes (one-hot encoding and rest in scikit-learn) 
*   hyper-parameter search and pick 3 classifiers
*   also pick an optimal encoding scheme
*   test some manual feature additions like geographic distances
*   also check l1 regularization and see which features matter the most
*   DT/RF & MLP seem to have non-convex optimizations or some other random seed initialization. can't replicate results when run multiple times.
"""

Ymlbl = np.zeros((Y.shape[0], alablTabl.shape[0]))
filidx = np.array([ (irow, alablTabl.loc['{0}={1}'.format(fcn, lbl), 'id'])
                    for irow, row in enumerate(alablFull_.to_dict(orient='records'))
                    for fcn, lbl in row.items() if not pd.isna(lbl)
                  ])
Ymlbl[[filidx[:,0], filidx[:,1]]] = 1

subYmlbl = np.zeros((Y.shape[0], alablTabl.shape[0]))
filidx = np.array([ (irow, alablTabl.loc['{0}={1}'.format(fcn, lbl), 'id'])
                    for irow, row in enumerate(alablSub_.to_dict(orient='records'))
                    for fcn, lbl in row.items() if not pd.isna(lbl)
                  ])
subYmlbl[[filidx[:,0], filidx[:,1]]] = 1
print(Ymlbl.shape, subYmlbl.shape)

# Commented out IPython magic to ensure Python compatibility.
mlblclasfrs = {'knn': KNeighborsClassifier(),
               'dt':  DecisionTreeClassifier(),
               'rf':  RandomForestClassifier(), #default worse than suggested values
               'mlp': MLPClassifier(), #default worse than suggested values
               '-dumbase-': DummyClassifier(strategy='most_frequent')
              }
# %time mlbclfaccs = trainFullClassifiersCV(mlblclasfrs, X, Ymlbl)
if not BATCH:
  pd_displayHTML(mlbclfaccs.style.hide_index())
  plot_accuracies(mlbclfaccs)

# Commented out IPython magic to ensure Python compatibility.
# %time smlbclaccs = trainFullClassifiersCV(mlblclasfrs, X, subYmlbl)
if not BATCH:
  pd_displayHTML(smlbclaccs.style.hide_index())
  plot_accuracies(smlbclaccs)

expreport = []
try:
  if not BATCH:
    raise UserWarning("Following code in this cell can only be run with BATCH=True from cmd-line")
  from math import factorial
  ncombr = lambda n,r: factorial(n) // factorial(r) // factorial(n-r)
  FRACP = 0.1  # test for 10% of possible choices in feature classes 
  samcount = alablFull.shape[0]
  fnccount = alablFull.shape[1]
  subsid = list(range(samcount))  
  params = ((cvf, reptr, k) for k in range(5, fnccount, 10)
            for cvf in range(2, 6) for reptr in range(1, 4))
  ATTEMPTS = 10
  #params = list(params)[:1]

  # this is to make sure that this block can be run in standalone mode
  featsFull_ = featsFull.iloc[subsid,:]
  clablFull_ = clablFull.iloc[subsid]
  alablFull_ = alablFull.iloc[subsid,:]

  X   = featsFull_.copy(deep=False)
  ccs = X.select_dtypes(['category']).columns 
  X[ccs] = X[ccs].apply(lambda x: x.cat.codes)
  X  = X.to_numpy()
  
  Y = clablFull_.copy(deep=False).cat.codes
  Y  = Y.to_numpy()

  Y_  = alablFull_.copy(deep=False)
  ccs = Y_.select_dtypes(['category']).columns
  Y_[ccs] = Y_[ccs].apply(lambda x: x.cat.codes)
  Y_ = Y_.to_numpy()
  
  Ymlbl = np.zeros((X.shape[0], alablTabl.shape[0]))
  filidx = np.array([ (irow, alablTabl.loc['{0}={1}'.format(fcn, lbl), 'id'])
                    for irow, row in enumerate(alablFull_.to_dict(orient='records'))
                    for fcn, lbl in row.items() if not pd.isna(lbl)
                   ])
  Ymlbl[[filidx[:,0], filidx[:,1]]] = 1

  for expparam in params:
    cvsplits = list(RepeatedKFold(n_splits=expparam[0], 
                                  n_repeats=expparam[1], random_state=20200408
                                 ).split(X, Y))
    expr1 = trainFullClassifiersCV(classifiers, X, Y)
    # run experiment using X,Y
    expreport.extend(dict([('ExpName', 'fulllbl-dense'), 
                           ('CVF', expparam[0]),
                           ('REPEAT', expparam[1]), 
                           ('K', expparam[2]),
                           ('Params', 'default')
                          ] + \
                          list(row.items()))
                     for row in expr1.to_dict(orient='records')
                    ) 
    expr2 = trainFullClassifiersCV(mlblclasfrs, X, Ymlbl)
    expreport.extend(dict([('ExpName', 'fulllbl-sparse'), 
                           ('CVF', expparam[0]),
                           ('REPEAT', expparam[1]), 
                           ('K', expparam[2]),
                           ('Params', 'default')
                          ] + \
                          list(row.items()))
                     for row in expr2.to_dict(orient='records')
                    ) 

    choices = ncombr(fnccount, expparam[2])
    for trial in range(1, ATTEMPTS+1):  #int(FRACP*choices)
      subfci = list(sorted(random.sample(range(fnccount), expparam[2])))
      subfcs = list(alablFull.columns[i] for i in subfci)
      
      alablSub_  = alablFull.iloc[subsid,subfci]

      clablSub = ['|'.join('{0}={1}'.format(k,v)
                           for k,v in row.items() if not pd.isna(v))
                  for row in alablSub_.to_dict(orient='records')
                 ]
      clablSub = pd.Series(clablSub, name=header[-1])
      subY = clablSub.astype('category').cat.codes
      subY = subY.to_numpy()

      subY_ = alablSub_.copy(deep=False)
      ccs = subY_.select_dtypes(['category']).columns
      subY_[ccs] = subY_[ccs].apply(lambda x: x.cat.codes)
      subY_ = subY_.to_numpy()

      subYmlbl = np.zeros((Y.shape[0], alablTabl.shape[0]))
      filidx = np.array([ (irow, alablTabl.loc['{0}={1}'.format(fcn, lbl), 'id'])
                         for irow, row in enumerate(alablSub_.to_dict(orient='records'))
                         for fcn, lbl in row.items() if not pd.isna(lbl)
                       ])
      subYmlbl[[filidx[:,0], filidx[:,1]]] = 1
      
      expr1 = trainFullClassifiersCV(classifiers, X, subY)
      expreport.extend(dict([('ExpName', 'sublbl-dense'), ('CVF', expparam[0]),
                             ('REPEAT', expparam[1]), ('K', expparam[2]),
                             ('TRIAL', 'T{0}'.format(trial)), 
                             ('Params', 'default')
                            ] + \
                            list(row.items()))
                       for row in expr1.to_dict(orient='records')) 
      
      expr2 = trainFullClassifiersCV(mlblclasfrs, X, subYmlbl)
      expreport.extend(dict([('ExpName', 'sublbl-sparse'), ('CVF', expparam[0]),
                             ('REPEAT', expparam[1]), ('K', expparam[2]),
                             ('TRIAL', 'T{0}'.format(trial)), 
                             ('Params', 'default')
                            ] + \
                            list(row.items()))
                       for row in expr2.to_dict(orient='records')) 
      
      expr3, clfs = trainIndClassifiersCV(classifiers, X, subY_, return_clfinsts=True)
      expreport.extend(dict([('ExpName', 'sublbl-dense-ind'), ('CVF', expparam[0]),
                             ('REPEAT', expparam[1]), ('K', expparam[2]),
                             ('TRIAL', 'T{0}'.format(trial)),
                             ('Params', 'default')
                            ] + \
                            list(row.items()))
                       for row in expr3.to_dict(orient='records')) 
      
      expr4 = jntTestIndClassifiersCV(classifiers, X, subY_, clfs)
      expreport.extend(dict([('ExpName', 'sublbl-dense-jnt'), ('CVF', expparam[0]),
                             ('REPEAT', expparam[1]), ('K', expparam[2]),
                             ('TRIAL', 'T{0}'.format(trial)),
                             ('Params', 'default')
                            ] + \
                            list(row.items()))
                       for row in expr4.to_dict(orient='records')) 
  
  pd.DataFrame(expreport).to_html('sigtyp-st2020-part1-batchexps-results.html', index=False)
  pd.DataFrame(expreport).to_json('sigtyp-st2020-part1-batchexps-results.json')
except KeyboardInterrupt:
  pd.DataFrame(expreport).to_html('sigtyp-st2020-part1-batchexps-results-aborted.html', index=False)
  pd.DataFrame(expreport).to_json('sigtyp-st2020-part1-batchexps-results-aborted.json')
except UserWarning as err:
  print(err)
