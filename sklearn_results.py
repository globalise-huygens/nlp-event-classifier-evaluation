"""
Since I use my own function to calculate p, r and f1, I check it against an implementation of sklearn to make sure I get the same scores
"""

import ast
import pandas as pd
from transformers import AutoTokenizer, AutoModelForTokenClassification
from evaluate import*

gold_paths = ['test_data/3604.tsv', 'test_data/1812.tsv', 'test_data/1092.tsv']

tokens, gold_adj, gold = get_all_data_per_text_region(gold_paths)


##### predict section
model = AutoModelForTokenClassification.from_pretrained('globalise/GloBERTise-event-classifier-general')
tokenizer = AutoTokenizer.from_pretrained('globalise/GloBERTise-event-classifier-general', add_prefix_space=True)

predicted_events = predict_events_aligned(tokens, model, tokenizer)
##### 

print('sklearn scores')

p_ete, r_ete, f1_ete, support = get_sklearn_metrics(gold_adj, predicted_events, eval_level='general')

print('end-to-end ', p_ete, r_ete, f1_ete, support)
