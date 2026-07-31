import ast

import pandas as pd

def parse_lexicon(path_to_lexicon: object) -> object:
    """
    Reads a csv and parses the lexicon (semicolons separating tokens, different columns separating tokens and type)
    """
    df = pd.read_csv(path_to_lexicon)
    tokens = df['tokens'].tolist()
    labels = df['label'].tolist()
    relationtypes = df['relationtype'].tolist()
    zipped_ref = zip(tokens, labels, relationtypes)

    # create dictionary of lexicon
    new_dict = {}
    for t, l, r in zipped_ref:
        if ';' in t:
            new_dict[t.split('; ')[0]] = [r, 'B-'+l]
            new_dict[t.split('; ')[1]] = [r, 'B-'+l]
            for i in range(2, 20):
                try:
                    new_dict[t.split('; ')[i]] = [r, 'B-'+l]
                except IndexError:
                    x = 0
        else:
            new_dict[t] = [r, 'B-'+l]
    return(new_dict)


def label_with_lexicon(lexicon, tokens):
    """
    reads the lexicon (csv) and returns labels for a list of tokens
    """
    labels = []
    for t in tokens:
        if t in lexicon.keys():
            labels.append(lexicon[t][1])
        else:
            labels.append("O")

    return(labels)

def evaluate_baseline_per_class(labels, gold, ev_class):
    """
    Calculates precision, recall and f1 for binary event detection using lexical baseline
    """
    tp_e = 0
    fp_e = 0
    fn_e = 0

    for i in range(0, len(gold)):
        zipped = zip(labels[i], gold[i])
        for tuple in zipped:
            if tuple[0] == tuple[1] and tuple[0] == ev_class:
                tp_e+=1
            if tuple[0] != tuple[1] and tuple[0] == 'O':
                fn_e+=1
            if tuple[0] != tuple[1] and tuple[0] == ev_class:
                fp_e+=1
    try:
        precision_e = tp_e / (tp_e + fp_e)
        recall_e = tp_e / (tp_e + fn_e)
        f1_e = 2 * (precision_e * recall_e) / (precision_e + recall_e)
    except ZeroDivisionError:
        precision_e = 0
        recall_e = 0
        f1_e = 0

    return(precision_e, recall_e, f1_e)

def get_all_test_tokens(path):
    all_tokens= []
    with open(path, 'r') as infile:
        data = infile.readlines()
        for line in data:
            tokens= ast.literal_eval(line)['words']
            all_tokens.append(tokens)

    return(all_tokens)

def get_all_gold(path):
    all_tokens= []
    with open(path, 'r') as infile:
        data = infile.readlines()
        for line in data:
            tokens= ast.literal_eval(line)['events']
            all_tokens.append(tokens)

    return(all_tokens)


