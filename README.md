# Code to evaluate classifiers for event classification

## folders

### test_data
Contains adjudicated and non-adjudicated labels for the three documents used by GLOBALISE as test data for event classification

### results
Contains all scores for precision, recall and f1 metrics for different classifiers. These results can be obtained by running _get_tables.py_

### genllm
Contains code to use and evaluate gpt5.1

## models evaluated
All classifiers evaluated were uploaded to Huggingface:
- https://huggingface.co/collections/StellaVerkijk/robe-event-classifiers-for-globalise
- https://huggingface.co/collections/StellaVerkijk/event-classifiers-trained-on-synthetically-augmented-data
