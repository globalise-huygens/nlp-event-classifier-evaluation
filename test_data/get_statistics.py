"""
Calculates statistics about the adjudication of the test set
"""

import pandas as pd

import ast


df_1092 = pd.read_csv('test_data/1092.tsv', delimiter='\t')
df_3604 = pd.read_csv('test_data/3604.tsv', delimiter='\t')
df_1812 = pd.read_csv('test_data/1812.tsv', delimiter='\t')


def get_stats(df, tuples_col='tupled_annos', type_col='resolve_type'):
    def parse_tuple(val):
        if isinstance(val, str):
            #print(ast.literal_eval(val))
            return ast.literal_eval(val)
        return val

    def count_nonO(val):
        t = parse_tuple(val)
        if len(t) > 2:
            return sum(1 for x in t if x != 'O')

    a_rows = df[df[type_col] == 'A']
    total_a = len(a_rows)


    m_rows = df[df[type_col] == 'M']
    total_m = len(m_rows)


    single_nonO_count = (a_rows[tuples_col].apply(count_nonO) == 1).sum()
    #percentage = 100 * single_nonO_count / total_a

    return single_nonO_count, total_a, total_m


print("Doc 1092")
single_count_1092, total_a_1092, total_m_1092 = get_stats(df_1092)
pct_a_1092 = 100 * single_count_1092 / total_a_1092
print(f"{pct_a_1092:.2f}% ({single_count_1092} of {total_a_1092}) of 'A' rows had exactly one non-O string")
print()

print('Doc 3604')
single_count_3604, total_a_3604, total_m_3604  = get_stats(df_3604)
pct_a_3604 = 100 * single_count_3604 / total_a_3604
print(f"{pct_a_3604:.2f}% ({single_count_3604} of {total_a_3604}) of 'A' rows had exactly one non-O string")
print()

#print('Doc 1812')
single_count_1812, total_a_1812, total_m_1812 = get_stats(df_1812)

# across documents

all_m = total_m_1092 + total_m_3604 + total_m_1812
all_a = total_a_1092 + total_a_3604 + total_a_1812

print("Percentage of adjudications that could be done automatically through a majority vote")
percentage_automatic = 100 * ( all_a / (all_a+all_m) )
print(percentage_automatic)
print('amount of automatic adjudications: ', all_a, ' amount of manual adjudications: ', all_m)

print("Percentage of adjudications that had to be reviewed manually")
percentage_automatic = 100 * ( all_m / (all_a+all_m) )
print(percentage_automatic)
print('amount of manual adjudications: ', all_m, ' amount of automatic adjudications: ', all_a)


all_single_non_O_count = single_count_1092 + single_count_3604
all_a = total_a_1092 + total_a_3604

print("Percentage of automatic adjudications where the majority vote (three out of four annotations) was O")
percentage_majority_null_vote_automatic = 100 * all_single_non_O_count / all_a
print(percentage_majority_null_vote_automatic)
print('amount of rows where three out of four annotations was O: ', all_single_non_O_count, ' amount of automatic adjudications: ', all_a)


# percentage manual resolution was by taxonomic resolution

# percentage manual resolution was by static resolution

def get_ontological_stats(df, tuples_col='tupled_annos', type_col='ontological_resolve'):
    def parse_tuple(val):
        return ast.literal_eval(val)

    t_rows = df[df[type_col] == 'T']
    total_t = len(t_rows)

    s_rows = df[df[type_col] == 'S']
    total_s = len(s_rows)

    return total_t, total_s


total_t_1092, total_s_1092 = get_ontological_stats(df_1092)
total_t_3604, total_s_3604 = get_ontological_stats(df_3604)
total_t_1812, total_s_1812 = get_ontological_stats(df_1812)

all_s = total_s_1092 + total_s_3604 + total_s_1812
all_t = total_t_1092 + total_t_3604 + total_t_1812


print("Percentage of manual adjudications that could be made on ontological basis")
percentage_ontological_resolved = 100 * (all_s + all_t) / all_m
print(percentage_ontological_resolved)
print('amount of ontological adjudications: ', all_s+all_t, ' amount of manual adjudications: ', all_m)