import ast
import pandas as pd
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
import sklearn

MAX_LEN = 512

def count_scores_sentence_level(gold, predictions):
    """
    counts scores per text region
    :param predictions: list of strings
    :param gold: list of strings
    :return: dict
    """

    pairs = [(t, p) for t, p in zip(gold, predictions) if t != 'O' or p != 'O']

    #print(pairs)

    tp = sum(1 for t, p in pairs if t == p and t != 'O')
    fp = sum(1 for t, p in pairs if p != 'O' and t != p)
    fn = sum(1 for t, p in pairs if t != 'O' and t != p)

    support = sum(1 for t, p in pairs if t != 'O')

    return tp, fp, fn, support


def is_o_label(gold_entry):
    """
    True if every label in the gold tuple is 'O' (i.e., no real event).
    """
    return all(label == 'O' for label in gold_entry)


def count_non_adjudicated_scores_sentence_level(gold, predictions):
    """
    counts scores per text region
    :param predictions: list of strings
    :param gold: list of tuples of strings (up to 4 labels each, 'O' treated as any other label)
    :return: dict
    """

    # Filter out rows where gold is entirely 'O'
    pairs = [(t, p) for t, p in zip(gold, predictions) if not is_o_label(t)]
    #print(pairs)

    support = len(pairs)

    tp = sum(1 for t, p in pairs if p != 'O' and p in t)
    fp = sum(1 for t, p in pairs if p != 'O' and p not in t)
    fn = sum(1 for t, p in pairs if p=='O' and p not in t)

    return tp, fp, fn, support

def count_class_scores_sentence_level(gold, predictions, eventclasses):
    """
    counts scores per text region
    :param predictions: list of strings
    :param gold: list of strings
    :return: dict
    """

    pairs = [(t, p) for t, p in zip(gold, predictions) if t != 'O' or p != 'O']
    #print(pairs)

    tp = sum(1 for t, p in pairs if t in eventclasses and p in eventclasses)
    fp = sum(1 for t, p in pairs if p in eventclasses and t not in eventclasses)
    fn = sum(1 for t, p in pairs if t in eventclasses and p not in eventclasses)

    support = tp+fn

    return tp, fp, fn, support

def count_class_scores_non_adjudicated_sentence_level(gold, predictions, eventclasses):
    """
    counts scores per text region, restricted to a given set of event classes
    :param predictions: list of strings
    :param gold: list of tuples of strings (up to 4 labels each, 'O' treated as any other label)
    :param eventclasses: set/list of class labels to evaluate on
    :return: dict
    """
    # Filter out rows where gold is entirely 'O'
    #print(gold)
    pairs = [(t, p) for t, p in zip(gold, predictions) if not is_o_label(t)]
    #print(pairs)

    tp = sum(1 for t, p in pairs if p in eventclasses and p in t)
    fp = sum(1 for t, p in pairs if p in eventclasses and p not in t)
    fn = sum(
        1 for t, p in pairs
        if any(label in eventclasses for label in t) and p not in t
    )

    support = sum(1 for t, p in pairs if any(label in eventclasses for label in t))

    return tp, fp, fn, support

def get_data(path):
    """
    extracts labels from tsv file
    :param path: string
    :return: lists
    """
    df = pd.read_csv(path, delimiter='\t')

    # Drop rows where tupled_annos is  '\n'
    df = df[df['word'].notna()]
    df = df[~df['word'].astype(str).isin(['\\n', '\n', ''])]
    df = df[df['word'].astype(str).str.strip() != '']

    tokens = df['word'].tolist()
    adj_labels = df['manual_resolve'].tolist()
    labels = df['tupled_annos'].tolist()

    literal_labels = []
    for entry in labels:
        literal_labels.append(ast.literal_eval(entry))

    return tokens, adj_labels, literal_labels

def get_data_per_text_region(path):
    """
    extracts tokens and labels from tsv file, splitting into separate lists
    whenever a '\n' marker row is encountered
    :param path: string
    :return: lists of lists
    """
    df = pd.read_csv(path, delimiter='\t')
    df.to_csv('check_1092.csv')

    all_tokens = []
    all_adj_labels = []
    all_literal_labels = []

    current_tokens = []
    current_adj_labels = []
    current_literal_labels = []

    for i, (token, adj_label, entry) in enumerate(zip(df['word'].tolist(), df['manual_resolve'].tolist(), df['tupled_annos'].tolist())):
        entry_str = str(entry)

        # Check if this row is a separator ('\n', literal '\n', blank, or NaN)
        if pd.isna(entry) or entry_str.strip() == '' or entry_str in ('\\n', '\n'):
            if current_tokens:  # only start a new list if the current one has content
                all_tokens.append(current_tokens)
                all_adj_labels.append(current_adj_labels)
                all_literal_labels.append(current_literal_labels)
                current_tokens = []
                current_adj_labels = []
                current_literal_labels = []
            continue

        try:
            parsed = ast.literal_eval(entry)
        except (ValueError, SyntaxError) as e:
            print(f"Row {i} in {path}: skipping unparseable entry: {entry!r} ({e})")
            continue

        current_tokens.append(str(token))
        current_adj_labels.append(adj_label)
        current_literal_labels.append(parsed)

    # Append the last chunk if there's leftover data after the final separator
    if current_tokens:
        all_tokens.append(current_tokens)
        all_adj_labels.append(current_adj_labels)
        all_literal_labels.append(current_literal_labels)

    return all_tokens, all_adj_labels, all_literal_labels

def get_all_data(paths):
    """
    extracts labels from tsv files
    :param paths: list of strings
    :return: lists
    """
    adj_labels = []
    labels = []
    tokens = []

    for path in paths:
        df = pd.read_csv(path, delimiter='\t')

        # Drop rows where tupled_annos is  '\n'
        df = df[df['word'].notna()]
        df = df[~df['word'].astype(str).isin(['\\n', '\n', ''])]
        df = df[df['word'].astype(str).str.strip() != '']

        adj_labels.extend(df['manual_resolve'].tolist())
        labels.extend(df['tupled_annos'].tolist())
        tokens.extend(df['word'].tolist())

    literal_labels = []
    for entry in labels:
        literal_labels.append(ast.literal_eval(entry))

    return tokens, adj_labels, literal_labels

def get_all_data_per_text_region(paths):

    """
    extracts tokens and labels from tsv files, splitting into separate lists
    whenever a '\n' marker row is encountered. Chunks from all files are
    combined into one set of lists of lists.
    :param paths: list of strings
    :return: lists of lists
    """
    all_tokens = []
    all_adj_labels = []
    all_literal_labels = []

    for path in paths:
        df = pd.read_csv(path, delimiter='\t')

        current_tokens = []
        current_adj_labels = []
        current_literal_labels = []

        for i, (token, adj_label, entry) in enumerate(zip(df['word'].tolist(), df['manual_resolve'].tolist(), df['tupled_annos'].tolist())):
            entry_str = str(entry)

            # Check if this row is a separator ('\n', literal '\n', blank, or NaN)
            if pd.isna(entry) or entry_str.strip() == '' or entry_str in ('\\n', '\n'):
                if current_tokens:  # only close off a chunk if it has content
                    all_tokens.append(current_tokens)
                    all_adj_labels.append(current_adj_labels)
                    all_literal_labels.append(current_literal_labels)
                    current_tokens = []
                    current_adj_labels = []
                    current_literal_labels = []
                continue

            try:
                parsed = ast.literal_eval(entry)
            except (ValueError, SyntaxError) as e:
                print(f"Row {i} in {path}: skipping unparseable entry: {entry!r} ({e})")
                continue

            # take out Miscellaneous and None labels
            
            new_parsed = []
            for label in parsed:
                if label == 'B-None' or label == 'I-None' or label == 'B-Miscellaneous' or label == 'I-Miscellaneous':
                    new_parsed.append('O')
                else: 
                    new_parsed.append(label)
            
            parsed = tuple(new_parsed)

            current_tokens.append(str(token))
            current_adj_labels.append(adj_label)
            current_literal_labels.append(parsed)

        # Append the last chunk of this file if there's leftover data after the final separator
        if current_tokens:
            all_tokens.append(current_tokens)
            all_adj_labels.append(current_adj_labels)
            all_literal_labels.append(current_literal_labels)

    return all_tokens, all_adj_labels, all_literal_labels


def get_metrics(gold, predictions, eval_level, eventclasses=['B-Translocation'], evaluation_type = 'adjudicated'):
    all_tp = []
    all_fp = []
    all_fn = []
    support_count = 0
    for i in range(0, len(gold)):
        if eval_level == 'general':
            if evaluation_type == 'adjudicated':    
                tp, fp, fn, support = count_scores_sentence_level(gold[i], predictions[i])

                all_tp.append(tp)
                all_fp.append(fp)
                all_fn.append(fn)
                support_count+=support

            elif evaluation_type == 'non_adjudicated':
                tp, fp, fn, support = count_non_adjudicated_scores_sentence_level(gold[i], predictions[i])

                all_tp.append(tp)
                all_fp.append(fp)
                all_fn.append(fn)
                support_count+=support
            
        elif eval_level == 'eventclass':
            if evaluation_type == 'adjudicated':
                tp, fp, fn, support = count_class_scores_sentence_level(gold[i], predictions[i], eventclasses)

                all_tp.append(tp)
                all_fp.append(fp)
                all_fn.append(fn)
                support_count+=support

            elif evaluation_type == 'non_adjudicated':
                tp, fp, fn, support = count_class_scores_non_adjudicated_sentence_level(gold[i], predictions[i], eventclasses)

                all_tp.append(tp)
                all_fp.append(fp)
                all_fn.append(fn)
                support_count+=support

    #return(sum(all_tp), sum(all_fp), sum(all_fn))

    #print(all_tp)

    precision = sum(all_tp) / (sum(all_tp) + sum(all_fp)) if (sum(all_tp) + sum(all_fp)) > 0 else 0
    recall = sum(all_tp) / (sum(all_tp) + sum(all_fn)) if (sum(all_tp) + sum(all_fn)) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return(precision, recall, f1, support_count)

def get_sklearn_metrics(gold, predictions, eval_level, eventclasses=['B-Translocation']):

    all_gold = []
    all_predicted = []
    for i in range(0, len(gold)):
        all_gold.extend(gold[i])
        all_predicted.extend(predictions[i])

    labels = ['B-Leaving', 'B-Occupation', 'B-BeingDead', 'B-Arriving', 'B-BeingAtAPlace',
                'B-SocialInteraction', 'B-Giving', 'B-BeingInARelationship', 'B-Request', 'B-HavingInPossession',
                'B-StartingConflict', 'B-Trade', 'B-Transportation', 'B-Getting', 'B-Enslaving', 'B-BeingEmployed',
                'B-InternalChange', 'B-BeingInDebt', 'B-Translocation', 'B-Buying', 'B-HavingContractualAgreement',
                'B-Selling', 'B-Decreasing', 'B-BeingLeader', 'B-Replacing', 'B-Increasing', 'B-FallingIll',
                'B-Visit', 'B-HavingInternalState-', 'B-BeginningARelationship', 'B-AlteringARelationship', 'B-EndingARelationship',
                'B-BeingInConflict', 'B-LosingPossession', 'B-Damaging', 'B-BeingDamaged',
                'B-Destroying', 'B-StartingAWar', 'B-Dying', 'B-TakingUnderControl', 'B-ViolentContest', 'B-Collaboration',
                'B-Killing', 'B-ForceToAct', 'B-Attacking', 'B-ChangeOfPossession', 'B-FinancialTransaction', 'B-EndingContractualAgreement',
                'B-LeavingAnOrganization', 'B-Mutiny', 'B-SocialStatusChange', 'B-Encounter', 'B-Voyage', 'B-Communication',
                'B-Repairing', 'B-BeginningContractualAgreement', 'B-BeingAtPeace', 'B-BeingDestroyed', 'B-HavingInternalState+',
                'B-Mismanagement', 'B-HavingAMedicalCondition', 'B-Besieging', 'B-Invasion', 'B-EndingConflict', 'B-Sinking',
                'B-ExtendingContractualAgreement', 'B-QuantityChange', 'B-Production', 'B-Unrest', 'B-Uprising', 'B-ScalarChange',
                'B-Punishing', 'B-JoiningAnOrganization', 'B-Healing', 'B-RelationshipChange', 'I-Leaving', 'I-Occupation', 'I-BeingDead', 
                'I-Arriving', 'I-BeingAtAPlace', 'I-SocialInteraction', 'I-Giving', 'I-BeingInARelationship', 'I-Request', 'I-HavingInPossession', 
                'I-StartingConflict', 'I-Trade', 'I-Transportation', 'I-Getting', 'I-Enslaving', 'I-BeingEmployed', 'I-InternalChange', 'I-BeingInDebt', 
                'I-Translocation', 'I-Buying', 'I-HavingContractualAgreement', 'I-Selling', 'I-Decreasing', 'I-BeingLeader', 'I-Replacing', 'I-Increasing', 
                'I-FallingIll', 'I-Visit', 'I-HavingInternalState-', 'I-BeginningARelationship', 'I-AlteringARelationship', 'I-EndingARelationship', 
                'I-BeingInConflict', 'I-LosingPossession', 'I-Damaging', 'I-BeingDamaged', 'I-Destroying', 'I-StartingAWar', 
                'I-Dying', 'I-TakingUnderControl', 'I-ViolentContest', 'I-Collaboration', 'I-Killing', 'I-ForceToAct', 'I-Attacking', 'I-ChangeOfPossession', 
                'I-FinancialTransaction', 'I-EndingContractualAgreement', 'I-LeavingAnOrganization', 'I-Mutiny', 'I-SocialStatusChange', 'I-Encounter', 
                'I-Voyage', 'I-Communication', 'I-Repairing', 'I-BeginningContractualAgreement', 'I-BeingAtPeace', 'I-BeingDestroyed', 'I-HavingInternalState+', 
                'I-Mismanagement', 'I-HavingAMedicalCondition', 'I-Besieging', 'I-Invasion', 'I-EndingConflict', 'I-Sinking', 'I-ExtendingContractualAgreement',
                'I-QuantityChange', 'I-Production', 'I-Unrest', 'I-Uprising', 'I-ScalarChange', 'I-Punishing', 
                'I-JoiningAnOrganization', 'I-Healing', 'I-RelationshipChange']
    
    #labels = ['B-Leaving's, 'I-Leaving']

    #labels = ['B-Translocation']
    
    if eval_level == 'general':
        precision, recall, fscore, support = sklearn.metrics.precision_recall_fscore_support(all_gold, all_predicted, labels=labels, average='micro')
   
    #elif eval_level == 'eventclass':


    #for l, z in zip(labels, support):
        #print(l, z)

    #print(sum(support))


    return(precision, recall, fscore, support)


def fix_first_token_bias(labels):
    """
    Heuristic fix: If first token is always an event, it might be a bias.
    Only apply if you're confident this is wrong.
    """
    if len(labels) > 0 and labels[0] != 'O':
        # Check if second token suggests continuation
        if len(labels) > 1 and labels[1] == 'O' or len(labels) == 1 and labels[0] != 'O':
            # Single event at position 0 - might be suspicious
            labels[0] = 'O'

    return labels


def convert_to_bio(labels):
    """
    Convert event labels to BIO scheme.

    Rules:
    - Single event surrounded by 'O' -> B-EventType
    - Consecutive same events -> B-EventType, I-EventType, I-EventType, ...
    - Different event type starts new B- tag
    - 'O' remains 'O'

    Args:
        labels: List of event labels (e.g., ['O', 'Translocation', 'O', ...])

    Returns:
        List of BIO labels (e.g., ['O', 'B-Translocation', 'O', ...])
    """
    bio_labels = []
    previous_label = 'O'

    for current_label in labels:
        if current_label == 'O':
            bio_labels.append('O')
        else:
            # Non-O label
            if previous_label == 'O' or previous_label != current_label:
                # Start of new entity (after O or different event type)
                bio_labels.append(f'B-{current_label}')
            else:
                # Continuation of same entity
                bio_labels.append(f'I-{current_label}')

        previous_label = current_label

    return bio_labels

def predict_and_convert_to_bio(words, model):
    """
    words: List[List[str]] — batch of tokenized sentences
    Returns: List[List[str]] — BIO labels per sentence
    """
    predicted_events = predict_events_aligned(words, model)  # list of lists
    bio_labels = [convert_to_bio(sentence_events) for sentence_events in predicted_events]
    return bio_labels

def predict_events_aligned(words, model, tokenizer):
    """
    handles word-to-subword alignment for a batch of sentences.
    words: List[List[str]] — a list of tokenized sentences
    Returns: List[List[str]] — predicted labels per sentence
    """

    tokenized_inputs = tokenizer(
        words,
        is_split_into_words=True,
        return_tensors="pt",
        add_special_tokens=False,
        padding=True,
        truncation=True,
        max_length=512,
    )

    with torch.no_grad():
        outputs = model(**tokenized_inputs)
    predictions = torch.argmax(outputs.logits, dim=-1)  # shape: (batch_size, seq_len)

    all_predicted_labels = []
    for i in range(len(words)):  # iterate over sentences in the batch
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        predicted_labels = []
        previous_word_id = None
        for word_id, pred_id in zip(word_ids, predictions[i]):
            if word_id is None:
                continue
            if word_id != previous_word_id:
                label = model.config.id2label[pred_id.item()]
                predicted_labels.append(label)
                bio_labels = convert_to_bio(predicted_labels)
                labels = fix_first_token_bias(bio_labels)
            previous_word_id = word_id
        all_predicted_labels.append(labels)



    return all_predicted_labels