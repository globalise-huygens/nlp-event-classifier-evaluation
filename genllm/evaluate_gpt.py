from evaluate import*
import ast


gold_paths = ['../test_data/3604.tsv', '../test_data/1812.tsv', '../test_data/1092.tsv']
tokens, gold_adj, gold = get_all_data_per_text_region(gold_paths)

with open('gpt5-1_output-2.json', 'r') as infile:
    predicted_events = ast.literal_eval(infile.read())

print(predicted_events)


for i in range(20, 50):
    print(len(tokens[i]), len(gold_adj[i]), len(predicted_events[i]))




data = {}

p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='general', evaluation_type='adjudicated')
data['gen_res_adj'] = {'p': p, 'r': r, 'f1': f1, 'support': support}
#p, r, f1, support = get_metrics(gold, predicted_events, eval_level='general', evaluation_type='non_adjudicated')
#data['gen_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1, 'support': support}

translo_classes_inclusive = ['B-Translocation', 'B-Voyage', 'B-Transportation', 'B-Leaving', 'B-Arriving', 'B-BeingAtAPlace', 'I-Translocation', 'I-Voyage', 'I-Transportation', 'I-Leaving', 'I-Arriving', 'I-BeingAtAPlace']

p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='eventclass', eventclasses = translo_classes_inclusive, evaluation_type='adjudicated')
data['translo_inclusive_res_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}
#p, r, f1, support = get_metrics(gold, predicted_events, eval_level='eventclass', eventclasses = translo_classes_inclusive, evaluation_type='non_adjudicated')
#data['translo_inclusive_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}

violence_classes = ['B-TakingUnderControl', 'B-Enslaving', 'B-Unrest', 'B-Attacking', 'B-StartingAWar', 'B-Killing',
                    'B-BeingInConflict', 'B-ViolentContest', 'B-ForceToAct', 'B-Occupation', 'I-TakingUnderControl', 'I-Enslaving', 'I-Unrest', 
                    'I-Attacking', 'I-StartingAWar', 'I-Killing', 'I-BeingInConflict', 'I-ViolentContest', 'I-ForceToAct', 'I-Occupation']

p, r, f1, support = get_metrics(gold_adj, predicted_events, eval_level='eventclass', eventclasses = violence_classes, evaluation_type='adjudicated')
data['viol_res_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}
#p, r, f1, support = get_metrics(gold, predicted_events, eval_level='eventclass', eventclasses = violence_classes, evaluation_type='non_adjudicated')
#data['viol_res_NOT_adj'] = {'p': p, 'r': r, 'f1': f1, 'support':support}


#metrics_gpt = {'adjudicated': {'overall': data['gen_res_adj'], 'translocation': data['translo_inclusive_res_adj'], 'violence': data['viol_res_adj']},
#                             'non_adjudicated': {'overall': data['gen_res_NOT_adj'], 'translocation': data['translo_inclusive_res_NOT_adj'], 'violence': data['viol_res_NOT_adj']}}


metrics_gpt = {'overall': data['gen_res_adj'], 'translocation': data['translo_inclusive_res_adj'], 'violence': data['viol_res_adj']}

print(metrics_gpt)