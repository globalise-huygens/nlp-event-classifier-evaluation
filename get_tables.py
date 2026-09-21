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

CLASSES = ['Communication', 'Translocation', 'HavingInPossession', 'BeingAtAPlace', 'Arriving', 'Transportation', 'Leaving', 
            'Getting', 'Giving', 'BeingEmployed', 'Request', 'Trade', 'TakingUnderControl', 
            'Collaboration', 'BeingInConflict', 'HavingInternalState-', 'Attacking',
            'BeingDamaged', 'ForceToAct', 'Voyage', 'Buying', 'ViolentContest', 'BeingInDebt', 'LosingPossession', 'Unrest', 
            'HavingInternalState+'] # organized according to representation in training data


def average_results(result_dict):

    p = []
    r = []
    f1 = []
    support = []
    for key, value in result_dict.items():
        if value['support'] != 0:
            p.append(value['p'])
            r.append(value['r'])
            f1.append(value['f1'])
            support.append(value['support'])
    precision = sum(p) / len(p)
    recall = sum(r) / len(r)
    f1 = sum(f1) / len(f1)

    return precision, recall, f1, sum(support)


def calculate_scores(gold_adj, gold, predicted_events):
    
    result_dict = {}
    
    p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='general', evaluation_type='adjudicated')
    result_dict['gen_res_adj'] = {'p': p, 'r': r, 'f1': f1, 'support': support}
    #p, r, f1, support = get_metrics(gold, predicted_events, eval_level='general', evaluation_type='non_adjudicated')
    #result_dict['gen_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1, 'support': support}

    for c in CLASSES:
        duo = ['B-'+c, 'I-'+c]
        p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='eventclass', eventclasses = duo, evaluation_type='adjudicated')
        result_dict[c+'_res_adj'] = {'p': p, 'r': r, 'f1': f1,  'support': support}
        #p, r, f1, support = get_metrics(gold, predicted_events, eval_level='eventclass', eventclasses = duo, evaluation_type='non_adjudicated')
        #result_dict[c+'_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1,  'support': support}

    translo_classes = ['B-Translocation', 'B-Voyage', 'B-Transportation', 'B-Leaving', 'B-Arriving', 'B-BeingAtAPlace']
    translo_classes_inclusive = ['B-Translocation', 'B-Voyage', 'B-Transportation', 'B-Leaving', 'B-Arriving', 'B-BeingAtAPlace', 'I-Translocation', 'I-Voyage', 'I-Transportation', 'I-Leaving', 'I-Arriving', 'I-BeingAtAPlace']
    #p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='eventclass', eventclasses = translo_classes, evaluation_type='adjudicated')
    #result_dict['translo_res_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}
    #p, r, f1, support = get_metrics(gold, predicted_events, eval_level='eventclass', eventclasses=translo_classes, evaluation_type='non_adjudicated')
    #result_dict['translo_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}
    p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='eventclass', eventclasses = translo_classes_inclusive, evaluation_type='adjudicated')
    result_dict['translo_inclusive_res_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}
    #p, r, f1, support = get_metrics(gold, predicted_events, eval_level='eventclass', eventclasses=translo_classes_inclusive, evaluation_type='non_adjudicated')
    #result_dict['translo_inclusive_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}

    occupation_classes = ['B-TakingUnderControl', 'B-Occupation', 'I-TakingUnderControl', 'I-Occupation']
    p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='eventclass', eventclasses = occupation_classes, evaluation_type='adjudicated')
    result_dict['occup_res_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}
    #p, r, f1, support = get_metrics(gold, predicted_events, eval_level='eventclass', eventclasses=occupation_classes, evaluation_type='non_adjudicated')
    #result_dict['occup_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}

    violence_classes = ['B-TakingUnderControl', 'B-Enslaving', 'B-Unrest', 'B-Attacking', 'B-StartingAWar', 'B-Killing',
                    'B-BeingInConflict', 'B-ViolentContest', 'B-ForceToAct', 'B-Occupation', 'I-TakingUnderControl', 'I-Enslaving', 'I-Unrest', 
                    'I-Attacking', 'I-StartingAWar', 'I-Killing', 'I-BeingInConflict', 'I-ViolentContest', 'I-ForceToAct', 'I-Occupation']
    p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='eventclass', eventclasses = violence_classes, evaluation_type='adjudicated')
    result_dict['viol_res_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}
    #p, r, f1, support = get_metrics(gold, predicted_events, eval_level='eventclass', eventclasses=violence_classes, evaluation_type='non_adjudicated')
    #result_dict['viol_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}

    #for c in CLASSES:
    #    begin = ['B-'+c]
    #    p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='eventclass', eventclasses = begin, evaluation_type='adjudicated')
    #    result_dict['B-'+c+'_res_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}
    #    p, r, f1, support = get_metrics(gold, predicted_events, eval_level='eventclass', eventclasses = begin, evaluation_type='non_adjudicated')
    #    result_dict['B-'+c+'_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}

    # evaluation on lowest representation group -------------------------------------------------------------------------------------------------------------------------------------------------------------

    lowest_rep_classes = ['Buying', 'BeginningARelationship', 'ViolentContest', 'BeingInDebt', 'Replacing', 'LosingPossession', 'ChangeOfPossession', 'JoiningAnOrganization', 'Unrest',
                        'HavingInternalState+', 'Mismanagement', 'HavingAMedicalCondition', 'BeingAtPeace', 'QuantityChange']

    collected_scores_low_rep_adj = {}
    collected_scores_low_rep_non_adj = {}

    for cl in lowest_rep_classes:
        duo = ['B-'+cl, 'I-'+cl]
        p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='eventclass', eventclasses = duo, evaluation_type='adjudicated')
        collected_scores_low_rep_adj[cl+'_res_adj'] = {'p': p, 'r': r, 'f1': f1,  'support': support}
        #p, r, f1, support = get_metrics(gold, predicted_events, eval_level='eventclass', eventclasses=duo, evaluation_type='adjudicated')
        #collected_scores_low_rep_non_adj[cl+'_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1,  'support': support}
    
    #print("SCORES LOWER FREQUENCY PER CATEGORY")
    #print(collected_scores_low_rep_adj)
    #print()
    #print(collected_scores_low_rep_non_adj)
    #print()

    #-------------------------------------------------------------------------------------------------------------------------------------------------------------

    return(result_dict)


def get_ete_results(tokens, gold_adj, gold):
    """
    load appropriate models, gather predictions and calculate scores.
    returns dictionary with performance metrics
    """

    model = AutoModelForTokenClassification.from_pretrained('globalise/GloBERTise-event-classifier-general')
    tokenizer = AutoTokenizer.from_pretrained('globalise/GloBERTise-event-classifier-general', add_prefix_space=True)
    predicted_events = predict_events_aligned(tokens, model, tokenizer)
    result_dict = calculate_scores(gold_adj, gold, predicted_events)

    return(result_dict)

def get_simplified_ROBE_results(tokens, gold_adj, gold):
    """
    load appropriate models, gather predictions and calculate scores.
    returns dictionary with performance metrics
    """

    tokenizer = AutoTokenizer.from_pretrained('globalise/GloBERTise', add_prefix_space=True)
    model_translocation = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-7')
    model_300_400 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-6')
    model_10_30 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-1')
    model_30_100 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-3')
    model_100_200 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-4')
    model_over_700 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-8')

    models = [model_over_700, model_100_200, model_30_100, model_10_30, model_300_400, model_translocation] # original order
    priorities = [1,2,3,4,5,6]

    predicted_events = predict_with_me(tokens, models, tokenizer, priorities)

    result_dict = calculate_scores(gold_adj, gold, predicted_events)

    return(result_dict)


def get_ROBE_results(tokens, gold_adj, gold):
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

    result_dict = calculate_scores(gold_adj, gold, predicted_events)

    return(result_dict)


def get_ROBE_synth_results(tokens, gold_adj, gold):
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
    model_translocation = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-7-synthetic')
    model_over_700 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-8')

    #models = [model_communication, model_largeclasses, model_mediumclasses, model_smallclasses, model_possession, model_translocation] # order of simplified version of ROBE
    models = [model_over_700, model_translocation, model_300_400, model_possession, model_100_200, model_30_100, model_violence, model_10_30]
    priorities = [1,2,3,4,5,6,7,8]

    predicted_events = predict_with_me(tokens, models, tokenizer, priorities)

    result_dict = calculate_scores(gold_adj, gold, predicted_events)

    return(result_dict)
    

def get_ROBE_plus_results(tokens, gold_adj, gold):
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

    result_dict = calculate_scores(gold_adj, gold, predicted_events)

    return(result_dict)


def get_ROBE_plus_synth_results(tokens, gold_adj, gold):
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
    model_translocation = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-7-synthetic')
    model_over_700 = AutoModelForTokenClassification.from_pretrained('globalise/ROBE-8')
    model_general = AutoModelForTokenClassification.from_pretrained('globalise/GloBERTise-event-classifier-general')

    models = [model_general, model_over_700, model_translocation, model_300_400, model_possession, model_100_200, model_30_100, model_violence, model_10_30]
    priorities = [1,2,3,4,5,6,7,8,9]


    predicted_events = predict_with_me(tokens, models, tokenizer, priorities)

    result_dict = calculate_scores(gold_adj, gold, predicted_events)

    return(result_dict)


def get_ete_synth_results(tokens, gold_adj, gold):
    """
    load appropriate models, gather predictions and calculate scores.
    returns dictionary with performance metrics
    """

    tokenizer = AutoTokenizer.from_pretrained('globalise/GloBERTise', add_prefix_space=True)
    model = AutoModelForTokenClassification.from_pretrained('globalise/GloBERTise-event-classifier-general-synthetic')

    predicted_events = predict_events_aligned(tokens, model, tokenizer)

    result_dict = calculate_scores(gold_adj, gold, predicted_events)

    return(result_dict)

def get_ROBE_plus_lex_results(tokens, gold_adj, gold):
    """

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

    #get lexical predictions
    lexicon = parse_lexicon('lexicon_release2.csv')
    
    lex_labels = []
    for l in tokens:      
        labels = label_with_lexicon(lexicon, l)   
        lex_labels.append(labels)

    print(lex_labels)

    combined_predictions = []
    for i in range(0, len(predicted_events)):
        combined_predictions_reg = []
        zipped = zip(predicted_events[i], lex_labels[i])
        for model_pred, lex in zipped:
            if model_pred != 'O':
                combined_predictions_reg.append(model_pred)
            elif model_pred != 'O' and lex != 'O':
                print("BOTH CAUGHT SOMETHING")
                print(lex)
                combined_predictions_reg.append(lex)
            elif model_pred == 'O' and lex != 'O':
                print("LEX CAUGHT SOMETHING")
                print(lex)
                combined_predictions_reg.append(lex)
            elif model_pred == 'O' and lex == 'O':
                combined_predictions_reg.append('O')
        combined_predictions.append(combined_predictions_reg)
    
    #sanity check
    assert len(predicted_events) == len(lex_labels) 
    assert len(predicted_events) == len(combined_predictions)

    result_dict = calculate_scores(gold_adj, gold, combined_predictions)

    return(result_dict)


def get_lex_results(tokens, gold_adj, gold):
    """
    load appropriate models, gather predictions and calculate scores.
    returns dictionary with performance metrics
    """

    lexicon = parse_lexicon('lexicon_release2.csv')
    
    all_labels = []
    for l in tokens:      
        labels = label_with_lexicon(lexicon, l)   
        all_labels.append(labels)

    print(all_labels)

    result_dict = calculate_scores(gold_adj, gold, all_labels)

    return(result_dict)


def process_results(tokens, gold_adj, gold):

    results_ete = get_ete_results(tokens, gold_adj, gold)
    results_ROBE = get_ROBE_results(tokens, gold_adj, gold)
    results_ROBE_synth = get_ROBE_synth_results(tokens, gold_adj, gold)
    results_ROBE_plus = get_ROBE_plus_results(tokens, gold_adj, gold)
    results_ROBE_plus_synth = get_ROBE_plus_synth_results(tokens, gold_adj, gold)
    results_ete_synthetic = get_ete_synth_results(tokens, gold_adj, gold)
    results_lexicon = get_lex_results(tokens, gold_adj, gold)
    results_ROBE_plus_lex = get_ROBE_plus_lex_results(tokens, gold_adj, gold)

    
    all_results = {
    'results_ete': results_ete,
    'results_ROBE': results_ROBE,
    'results_ROBE_synth': results_ROBE_synth,
    'results_ROBE_plus': results_ROBE_plus,
    'results_ROBE_plus_synth': results_ROBE_plus_synth,
    'results_ete_synthetic': results_ete_synthetic,
    'results_lexicon': results_lexicon,
    'results_ROBE_plus_lex': results_ROBE_plus_lex
    }


    for name, data in all_results.items():
        with open(f'results/{name}.json', 'w') as f:
            json.dump(data, f, indent=2)

    
def process_simplified_ROBE_results(tokens, gold_adj, gold):

    results_simplified_ROBE = get_simplified_ROBE_results(tokens, gold_adj, gold)

    
    all_results = {
    'results_simplified_ROBE': results_simplified_ROBE,
    }


    for name, data in all_results.items():
        with open(f'results/{name}.json', 'w') as f:
            json.dump(data, f, indent=2)


def construct_tables(list_of_filepaths):

    output = {}

    for filepath in list_of_filepaths:
        filename = os.path.basename(filepath)          # e.g. 'results_me_plus.json'
        name = os.path.splitext(filename)[0]            # e.g. 'results_me_plus'
        key = name.replace('results_', '', 1)            # e.g. 'me_plus'

        with open(filepath, 'r') as infile:
            data = json.load(infile)

        #output[key] = {'adjudicated': {'overall': data['gen_res_adj'], 'translocation': data['translo_inclusive_res_adj'], 'violence': data['viol_res_adj']}, 
        #                     'non_adjudicated': {'overall': data['gen_res_NOT_adj'], 'translocation': data['translo_inclusive_res_NOT_adj'], 'violence': data['viol_res_NOT_adj']}}#'lowest_frequency_non_adj': data['lowest_frequency_group_non_adj']}}

        output[key] = {'overall': data['gen_res_adj'], 'translocation': data['translo_inclusive_res_adj'], 'violence': data['viol_res_adj']}, 
                             
    return(output)      


## MAIN ##

gold_paths = ['test_data/3604.tsv', 'test_data/1812.tsv', 'test_data/1092.tsv']
tokens, gold_adj, gold = get_all_data_per_text_region(gold_paths)

all_gold = []
for sentence in gold_adj:
    for label in sentence:
        all_gold.append(label)
all_classes_in_gold = set(all_gold)

# uncomment following line to run code to get all results and write them to the 'results' folder
process_results(tokens, gold_adj, gold)

json_files = glob.glob(os.path.join('results', '*.json'))

output_main_results = construct_tables(['results/results_lexicon.json', 'results/results_ete.json', 'results/results_ete_synthetic.json', 'results/results_ROBE.json', 'results/results_ROBE_plus.json'])
output_robe_plus_lex = construct_tables(['results/results_ROBE_plus_lex.json'])

# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

##### simplified ROBE results only on part of test set

gold_paths = ['test_data/3604.tsv']
tokens, gold_adj, gold = get_all_data_per_text_region(gold_paths)

# uncomment following line to run code to get results of the simplified ROBE system on the part of the dataset that was validated by external historians and write them to the 'results' folder
process_simplified_ROBE_results(tokens, gold_adj, gold)

#output_simplified_ROBE = construct_tables(['results/results_simplified_ROBE.json'])

# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

print()

print(output_main_results)

print()

print(output_robe_plus_lex)

    

