"""
Implementation of the MS-Apriori algorithm. Rule generation only requires 1 consequent on the RHS.

Author: Wesley Kwiecinski
Last updated: 2/18/2026
CS 583 - Data Mining - Assignment 1
"""

import re

from decimal import Decimal,getcontext
from collections import OrderedDict as od
from argparse import ArgumentParser as ap
from dataclasses import dataclass
from itertools import combinations

getcontext().prec = 5


@dataclass
class ItemData:
    """
    Stores counts and tail counts for a frequent itemset.
    """
    count: Decimal = Decimal(0)
    tail_count: Decimal = Decimal(0)


@dataclass
class Rule:
    """
    Stores a rule for a given frequent itemset.
    """
    antecedent: tuple
    consequent: tuple
    confidence: Decimal


@dataclass
class ParameterData:
    """
    Stores the list of parameter data given from a parameters input file.

    The parameter input file is of this form:
        MIS(1) = 0.02
        MIS(2) = 0.04
        …
        MIS(rest) = 0.01
        SDC = 0.003
        minconf = 30%
    """
    mis_per_item = od()
    support_difference_constraint: Decimal = Decimal(0)
    min_confidence: Decimal = Decimal(0)

    def sort_mis_dict_by_value(self):
        """
        Sorts the saved list of MIS values per item by the MIS value.
        
        :param self: Self
        """
        self.mis_per_item = od(sorted(self.mis_per_item.items(), key=lambda x: (x[1], x[0])))

    def __str__(self) -> str:
        """
        Neatly prints the parameter file to the console.
        """
        to_str = (f"SDC = {self.support_difference_constraint}\n" + 
                  f"Min confidence = {self.min_confidence}\n")
        
        for key,value in self.mis_per_item.items():
            to_str += f"\nMIS({key}) = {value}"

        return to_str
        

def print_itemsets(k_itemset: od, items_per_line=10):
    """
    Prints a given frequent itemset.
    
    :param k_itemset: The itemset to print.
    :type k_itemset: od
    :param items_per_line: The number of items in the itemset to print per line.
    """
    items = 0
    print("{", end="")
    for item,_ in k_itemset.items():
        print(f"{item},", end="")
        items += 1
        if items >= items_per_line:
            print()
            items = 0
    print("}")


def parse_params_cfg(path: str, param_data: ParameterData) -> ParameterData:
    """
    Parses a parameter configuration file.
    
    :param path: The path to the file
    :type path: str
    :param param_data: The class instance to save the parsed parameters in.
    :type param_data: ParameterData
    :return: The filled class instance of ParameterData.
    :rtype: ParameterData
    """
    with open(path) as params_file:
        for line in params_file:
            pps = "".join(line.split()).split("=") # remove whitespace and split by =

            if "MIS" in pps[0]:
                mis_decl = re.findall(r"MIS\([\d\D]+\)", pps[0])[0].replace("MIS(", "").replace(")", "")
                if mis_decl == "rest":
                    # fill any values in the dictionary that do not have a MIS
                    for key,value in param_data.mis_per_item.items():
                        if value == None:
                            param_data.mis_per_item[key] = Decimal(pps[1])
                            # print(f"set {key} MIS to {pps[1]}")
                else:
                    # print(f"set {mis_decl} MIS to {pps[1]}")
                    param_data.mis_per_item[int(mis_decl)] = Decimal(pps[1])
            elif "SDC" in pps[0]:
                param_data.support_difference_constraint = Decimal(pps[1])
            elif "minconf" in pps[0]:
                param_data.min_confidence = Decimal(int(pps[1][:-1])) / Decimal(100) # min confidence is given as a percentage

    # sort the MIS based on value (total order)
    return param_data


def parse_transactions_file(path: str, transaction_db: list, param_data: ParameterData):
    """
    Parses a transactions file. Each file is a list of transactions separated by newlines. A
    transaction is a comma separated list of integers.

    :param path: The path to the transactions file.
    :type path: str
    :param transaction_db: Where to store the list of transactions.
    :type transaction_db: list
    :param param_data: The parameter data for a list of given transactions.
    :type param_data: ParameterData
    """
    with open(path) as transactions_file:
        for line in transactions_file:
            transaction = "".join(line.split())
            transaction_db.append([int(item) for item in (transaction.split(","))])
            for item in transaction.split(","): # insert any items into the param db
                item = int(item)
                if item not in param_data.mis_per_item:
                    param_data.mis_per_item[item] = None


def generate_rules(frequent_itemsets: od, support_counts: od) -> od:
    """
    Generates rules for a given set of frequent itemsets and support counts.

    :param frequent_itemsets: The ordered dict containing all frequent itemsets
    :type frequent_itemsets: od
    :param support_counts: The ordered dict containing all support counts for every frequent itemset candidate
    :type support_counts: od
    :return: Returns the ordered dictionary containing every possible rule from the list of given frequent itemsets
    :rtype: OrderedDict[Any, Any]
    """
    rules = od()
    for k,itemset in frequent_itemsets.items():
        if k > 1:
            rules[k] = od()
            for item in itemset:
                for idx,element in enumerate(item):
                    consequent = element
                    antecedent = tuple([i for i in item if i != consequent])
                    itemset_count = support_counts[item].count if item in support_counts.keys() else 0
                    confidence = 0
                    antecedent_count = 0

                    # if the consequent of the rule is the head of the frequent itemset, then we need to use the tail count to measure the confidence of the
                    # rule instead of searching for the support of the antecedent in the support counts.
                    if consequent == item[0]:
                        # head item problem solution
                        antecedent_count = support_counts[item].tail_count
                    else: # otherwise we can do rule generation like normal.
                        antecedent_count = support_counts[antecedent].count if antecedent in support_counts.keys() else 0

                    confidence = 0 if antecedent_count == 0 else itemset_count / antecedent_count
                    potential_rule = Rule(antecedent=antecedent, consequent=consequent, confidence=Decimal(confidence))
                    if item not in rules:
                        rules[item] = []
                    rules[item].append(potential_rule)

    return rules


def level2_candidate_generation(level_1_candidates_dict: dict, transaction_db: list, param_db: ParameterData) -> od:
    """
    Generates frequent 2-itemsets.
    
    :param level_1_candidates_dict: The set of 1-frequent itemsets
    :type level_1_candidates_dict: dict
    :param transaction_db: The list of transactions
    :type transaction_db: list
    :param param_db: The list of parameters for the set of transactions
    :type param_db: ParameterData
    :return: The ordered dict containing all level 2 candidates.
    :rtype: OrderedDict[Any, Any]
    """
    candidate_2_set = od()
    n_trans = len(transaction_db)
    candidates = level_1_candidates_dict["seeds"]
    supports = level_1_candidates_dict["supports"]

    # candidates = L.items()
    for idx,l in enumerate(candidates):
        # check MIS count
        candidate_support = Decimal(supports[l].count) / Decimal(n_trans)
        if candidate_support >= param_db.mis_per_item[l[0]]: # check if the candidate meets the minimum support
            for h in candidates[idx+1:]: # for each item in the candidate list after the current candidate
                item_support = Decimal(supports[h].count) / Decimal(n_trans)
                if item_support >= param_db.mis_per_item[l[0]] and (abs(item_support - candidate_support) <= param_db.support_difference_constraint): # if the items meet the SDC then combine and add
                    candidate_2_set[(l[0], h[0])] = None

    return candidate_2_set


# generates a pair in the frequent itemset where the two items differ in last value only, and the last value MIS of the second item is greater than the first,
# and the supports satisfy the support difference constraint.
# note that all items are sorted by their MIS value so we can easily generate candidates.
# returns None when there are no more pairs.
def _generate_pair(frequent_itemsets: od, n_transactions, sdc: Decimal, supports: dict):
    current_index = 0
    stop_index = 0
    itemsets = list(frequent_itemsets.keys())
    while current_index != len(itemsets):
        # get the location of the next frequent itemset that has a different first value
        while stop_index < len(itemsets) and itemsets[current_index][0] == itemsets[stop_index][0]:
            stop_index += 1

        # slice the array to get a chunk of "similar" items to iterate over
        itemset_chunk = itemsets[current_index:stop_index]
        for idx,itemset in enumerate(itemset_chunk):
            subiter = idx
            while subiter < len(itemset_chunk):
                check_pair = itemset_chunk[subiter]
                failed = False
                for j in range(len(itemset)-1): # check that all items in the itemset are the same except for last
                    if itemset[j] != check_pair[j]:
                        failed = True
                        break

                # if the last two items are different
                if not failed and itemset[-1] != check_pair[-1]:
                    i_support = supports[(itemset[-1],)].count / Decimal(n_transactions)
                    i_prime_support = supports[(check_pair[-1],)].count / Decimal(n_transactions)
                    # then we check the SDC and yield the pair if it passes
                    if (abs(i_support - i_prime_support) <= sdc):
                        yield tuple(list(itemset) + [check_pair[-1]])

                subiter += 1

        current_index = stop_index


def ms_candidate_generation(last_set_frequent_candidates, transaction_db: list, param_db: ParameterData, supports: dict) -> od:
    candidate_k_set = od()
    n_trans = len(transaction_db)
    sdc = param_db.support_difference_constraint
    # insert join step candidates into candidate set
    for joined_pair in _generate_pair(last_set_frequent_candidates, n_trans, param_db.support_difference_constraint, supports):
        candidate_k_set[joined_pair] = None

    # then prune candidates by looking through each size k-1 subset of a candidate if candidates exist
    if candidate_k_set:
        subset_size = len(list(candidate_k_set.keys())[0]) - 1
        for c in candidate_k_set:
            for subset in combinations(c, subset_size):
                # check if first item is in subset or MIS values match c1 and c2
                if c[0] in subset or param_db.mis_per_item[c[0]] == param_db.mis_per_item[c[1]]:
                    if subset not in set(last_set_frequent_candidates.keys()):
                        del candidate_k_set[c]

    return candidate_k_set


# initial pass steps:
# 1) Find support counts of each item
# 2) Follow sorted MIS order to develop frequent 1-itemsets
def initial_pass(transactions: list, params: ParameterData) -> dict:
    # step 1: record the support counts of each item for all transactions.
    candidate_db = od()
    for transaction in transactions:
        for item in transaction:
            if ((item,)) not in candidate_db:
                candidate_db[(item,)] = ItemData()
            candidate_db[(item,)].count += 1

    # print("Getting candidate items through minimum supports...")
    k1_frequent_itemsets = []
    initial_item = None
    # use tuples to make itemsets hashable
    for item,mis in params.mis_per_item.items():
        # find the first item in the sorted order that meets the minimum support threshold
        if initial_item == None and candidate_db[(item,)].count / len(transactions) >= mis: # what is the minimum support fraction for a given item in the sorted MIS dict
            k1_frequent_itemsets.append((item,))
            initial_item = item
        elif initial_item != None and candidate_db[(item,)].count / len(transactions) >= params.mis_per_item[initial_item]:
            k1_frequent_itemsets.append((item,))

    # we can return the seeds and support counts
    return {"seeds": k1_frequent_itemsets, "supports": candidate_db}


def msapriori(transaction_db: list, param_db: ParameterData):
    param_db.sort_mis_dict_by_value() # first, we sort the mis dict by the values of the minimum supports to create a total order.
    candidates_dict = initial_pass(transaction_db, param_db) # get 1-frequent candidates
    candidate_counts = od()
    # develop the first set of 1-frquent itemsets
    frequent_items = od({1: od()})
    for item in candidates_dict["seeds"]:
        if candidates_dict["supports"][item].count / len(transaction_db) >= param_db.mis_per_item[item[0]]:
            frequent_items[1][item] = None

    # this is duplicated code but thats okay
    for transaction in transaction_db:
        for item in frequent_items[1].keys():
            if item not in candidate_counts:
                candidate_counts[item] = ItemData(Decimal(0), Decimal(0))

            if set(item).issubset(transaction):
                candidate_counts[item].count += 1

            if set(item[1:]).issubset(transaction):
                candidate_counts[item].tail_count += 1

    # next we generate frequent itemsets until we can't no mo'
    k_frequency = 2
    last_itemset = frequent_items[k_frequency-1]
    n_transactions = len(transaction_db)
    while(len(last_itemset) != 0):
        frequent_items[k_frequency] = od()
        level_k_candidates = set()
        # if k is 2 we use a special candidate generation function
        if k_frequency == 2:
            level_k_candidates = level2_candidate_generation(candidates_dict, transaction_db, param_db)
        else:
            level_k_candidates = ms_candidate_generation(last_itemset, transaction_db, param_db, candidates_dict["supports"])

        for transaction in transaction_db:
            for candidate in level_k_candidates:
                # add the candidate if it does not exist
                if candidate not in candidate_counts:
                    candidate_counts[candidate] = ItemData(Decimal(0), Decimal(0))

                if set(candidate).issubset(transaction): # if the candidate is in the transaction
                    candidate_counts[candidate].count += 1

                if set(candidate[1:]).issubset(transaction): # if the tail is in the transaction
                    candidate_counts[candidate].tail_count += 1

        # update the frequent candidates list 
        for c in level_k_candidates:
            if Decimal(candidate_counts[c].count) / Decimal(n_transactions) >= param_db.mis_per_item[c[0]]:
                frequent_items[k_frequency][c] = None

        # move to next frequency
        k_frequency += 1
        last_itemset = frequent_items[k_frequency-1]

    return frequent_items,candidate_counts


def output_itemsets_and_rules(frequent_itemsets: od, support_counts: od, rules: od, minimum_conf: Decimal):
    for idx,itemset in frequent_itemsets.items():
        if idx == 1:
            print(f"(Length-{idx} {len(itemset)}")
            for item in itemset:
                formatted = " ".join(f"{i}" for i in item)
                print(f"\t({formatted}) : {support_counts[item].count} : {support_counts[item].tail_count}")
            print(")")
        elif len(itemset) > 0:        
            print(f"(Length-{idx} {len(itemset)}")
            for item in itemset:
                formatted = " ".join(f"{i}" for i in item)
                print(f"\t({formatted}) : {support_counts[item].count} : {support_counts[item].tail_count}")
                for rule in rules[item]:
                    if rule.confidence >= minimum_conf:
                        ant = rule.antecedent
                        cons = rule.consequent
                        formatted_rule = "(" + f" ".join([f"{i}" for i in ant]) + " -> " + f"{cons})"
                        formatted = f"\t{formatted_rule} : {rule.confidence*100}%"
                        print(formatted)
            print(")")


if __name__ == "__main__":
    parser = ap()
    parser.add_argument("transactions", help="The input for database transactions.")
    parser.add_argument("params", help="Parameters input")
    parser.add_argument("--test", help="Test file to check output against", default="")

    args = parser.parse_args()

    transaction_db = []
    params = ParameterData()
    
    # initialize data for apriori
    parse_transactions_file(args.transactions, transaction_db, params)
    params = parse_params_cfg(args.params, params)
    params.sort_mis_dict_by_value()

    frequent_items,candidate_counts = msapriori(transaction_db=transaction_db, param_db=params)
    rules = generate_rules(frequent_itemsets=frequent_items, support_counts=candidate_counts)
    output_itemsets_and_rules(frequent_items, candidate_counts, rules, minimum_conf=params.min_confidence)
    