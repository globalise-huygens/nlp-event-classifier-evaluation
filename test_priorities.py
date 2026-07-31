def reconcile_labels_with_priority(label_lists, priority='first', priorities=None):
    """
    Reconcile multiple label lists with configurable priority for conflicts.

    Args:
        label_lists: List of label lists, e.g., [['O', 'T', 'O'], ['O', 'M', 'O'], ['B', 'O', 'O']]
        priority: Strategy for handling non-O conflicts:
            - 'list_order': Use explicit list priorities (requires priorities param)

    Returns:
        Single reconciled label list
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

all_labels = []
labels1 = ['O', 'O', 'Translocation']
labels2 = ['O', 'BeingInConflict', 'BeingInConflict']
labels3 = ['O', 'BeingInConflict', 'TakingUnderControl']
all_labels.append(labels1)
all_labels.append(labels2)
all_labels.append(labels3)

priorities = [1, 2, 3]

reconciled = reconcile_labels_with_priority(all_labels, priority='list_order', priorities=priorities)

print(reconciled)