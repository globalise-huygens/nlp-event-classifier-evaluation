import ast
import pandas as pd
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
from evaluate import*
from evaluate_me import predict_with_me
from apply_lexicon import*
import json
import os
import glob

gold_paths = ['test_data/3604.tsv', 'test_data/1812.tsv', 'test_data/1092.tsv']
tokens, gold_adj, gold = get_all_data_per_text_region(gold_paths)

all_gold = []
for sentence in gold_adj:
    for label in sentence:
        all_gold.append(label)
all_classes_in_gold = set(all_gold)

def get_ROBE_results(tokens):
    """
    load appropriate models, gather predictions and calculate scores.
    returns dictionary with performance metrics
    """
    tokenizer = AutoTokenizer.from_pretrained('globalise/GloBERTise', add_prefix_space=True)
    model_10_30 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-1')
    model_violence = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-2')
    model_30_100 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-3')
    model_100_200 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-4')
    model_possession = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-5')
    model_300_400 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-6')
    model_translocation = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-7')
    model_over_700 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-8')

    #models = [model_communication, model_largeclasses, model_mediumclasses, model_smallclasses, model_possession, model_translocation] # order of simplified version of ROBE
    models = [model_over_700, model_translocation, model_300_400, model_possession, model_100_200, model_30_100, model_violence, model_10_30]
    priorities = [1,2,3,4,5,6,7,8]

    predicted_events = predict_with_me(tokens, models, tokenizer, priorities)


    return(predicted_events)

def get_ROBE_plus_results(tokens):
    """
    load appropriate models, gather predictions and calculate scores.
    returns dictionary with performance metrics
    """

    tokenizer = AutoTokenizer.from_pretrained('globalise/GloBERTise', add_prefix_space=True)
    model_10_30 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-1')
    model_violence = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-2')
    model_30_100 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-3')
    model_100_200 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-4')
    model_possession = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-5')
    model_300_400 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-6')
    model_translocation = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-7')
    model_over_700 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-8')
    model_general = AutoModelForTokenClassification.from_pretrained('globalise/GloBERTise-event-classifier-general')

    models = [model_general, model_over_700, model_translocation, model_300_400, model_possession, model_100_200, model_30_100, model_violence, model_10_30]
    priorities = [1,2,3,4,5,6,7,8,9]

    predicted_events = predict_with_me(tokens, models, tokenizer, priorities)


    return(predicted_events)


robe_predictions = get_ROBE_results(tokens)
robe_plus_predictions = get_ROBE_plus_results(tokens)

zipped = zip(robe_predictions, tokens)

#for l1, l2 in zipped:
#    if 'B-HavingInternalState+' in l1:
#        #print(l1, l2)
#        zipped = zip(l1, l2)
#        for t1, t2 in zipped:
#            print(t1, t2)




print()

zipped2 = zip(robe_plus_predictions, tokens)

for l1, l2 in zipped2:
    if 'B-HavingInternalState+' in l1:
        zipped = zip(l1, l2)
        for t1, t2 in zipped:
            print(t1, t2)