import ast
import pandas as pd
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
from evaluate import*



def reconcile_labels_with_priority(label_lists, priority='first', priorities=None):
    """
    Reconcile multiple label lists with configurable priority for conflicts.

    Args:
        label_lists: List of label lists, e.g., [['O', 'T', 'O'], ['O', 'M', 'O'], ['B', 'O', 'O']]
        priority: Strategy for handling non-O conflicts:
            - 'list_order': Use explicit list priorities (requires priorities param)

    Returns:
        Single reconciled label list

    This function was written by CLAUDE
    """
    if not label_lists:
        return []

    length = len(label_lists[0])
    assert all(len(lst) == length for lst in label_lists), "All label lists must have same length"

    # If using list_order priority, validate priorities parameter
    if priority == 'list_order':
        if priorities is None:
            raise ValueError("priorities parameter required when priority='list_order'")
        if len(priorities) != len(label_lists):
            raise ValueError("priorities list must match number of label lists")

    reconciled = []

    for i in range(length):
        labels_at_position = [lst[i] for lst in label_lists]

        # Find indices with non-O labels
        non_o_indices = [idx for idx, label in enumerate(labels_at_position) if label != 'O']

        if not non_o_indices:
            # All are 'O'
            reconciled.append('O')
        elif len(non_o_indices) == 1:
            # Only one non-O label, no conflict
            reconciled.append(labels_at_position[non_o_indices[0]])
        else:
            if priority == 'list_order':
                # Take from list with highest priority
                best_idx = max(non_o_indices, key=lambda idx: priorities[idx])
                reconciled.append(labels_at_position[best_idx])

    return reconciled


def predict_events_aligned_me(words, model, tokenizer):
    """
    handles word-to-subword alignment.
    """
    # Tokenize with word-level tracking
    tokenized_inputs = tokenizer(
        words,
        is_split_into_words=True,
        return_tensors="pt",
        add_special_tokens=False,
        padding=True,
        truncation=True,
        max_length=512,
    )
    # Get predictions
    with torch.no_grad():
        outputs = model(**tokenized_inputs)
    predictions = torch.argmax(outputs.logits, dim=-1)[0]

    #####

    # Align predictions to original words
    word_ids = tokenized_inputs.word_ids()
    predicted_labels = []
    previous_word_id = None

    for word_id, pred_id in zip(word_ids, predictions):
        if word_id is None:
            continue
        if word_id != previous_word_id:
            label = model.config.id2label[pred_id.item()]
            predicted_labels.append(label)
        previous_word_id = word_id

    return predicted_labels


def predict_with_me(words, models, tokenizer, priorities):
    """
    predict with multiple models using priorities to get one prediction per token
    """
    # Get predictions
    all_predicted_labels = [] 
    for i in range(len(words)):  # iterate over sentences in the batch
        all_models_predicted = []
        for model in models:
            predicted_events = predict_events_aligned_me(words[i], model, tokenizer)
            all_models_predicted.append(predicted_events)
        predicted_labels = reconcile_labels_with_priority(all_models_predicted, priority='list_order', priorities=priorities)

        bio_labels = convert_to_bio(predicted_labels)
        labels = fix_first_token_bias(bio_labels)
        all_predicted_labels.append(labels)

    return(all_predicted_labels)