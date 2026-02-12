import re

from decimal import Decimal,getcontext
from collections import OrderedDict as od
from argparse import ArgumentParser as ap
from dataclasses import dataclass
from itertools import combinations

getcontext().prec = 5


@dataclass
class ItemData:
    count: Decimal = Decimal(0)


@dataclass
class ParameterData:
    mis_per_item = od()
    support_difference_constraint: Decimal = Decimal(0)
    min_confidence: Decimal = Decimal(0)

    def sort_mis_dict_by_value(self):
        self.mis_per_item = od(sorted(self.mis_per_item.items(), key=lambda x: (x[1], x[0])))

    def __str__(self) -> str:
        to_str = (f"SDC = {self.support_difference_constraint}\n" + 
                  f"Min confidence = {self.min_confidence}\n")
        
        for key,value in self.mis_per_item.items():
            to_str += f"\nMIS({key}) = {value}"

        return to_str
        

def print_itemsets(k_itemset: od, items_per_line=10):
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
                            print(f"set {key} MIS to {pps[1]}")
                else:
                    print(f"set {mis_decl} MIS to {pps[1]}")
                    param_data.mis_per_item[int(mis_decl)] = Decimal(pps[1])
            elif "SDC" in pps[0]:
                param_data.support_difference_constraint = Decimal(pps[1])
            elif "minconf" in pps[0]:
                param_data.min_confidence = Decimal(int(pps[1][:-1])) / Decimal(100) # min confidence is given as a percentage

    # sort the MIS based on value (total order)
    return param_data


def parse_transactions_file(path: str, transaction_db: list, param_data: ParameterData):
    with open(path) as transactions_file:
        for line in transactions_file:
            transaction = "".join(line.split())
            transaction_db.append([int(item) for item in (transaction.split(","))])
            for item in transaction.split(","): # insert any items into the param db
                item = int(item)
                if item not in param_data.mis_per_item:
                    param_data.mis_per_item[item] = None


def compare_with_key(result: str, check: str):
    return False


def generate_rules() -> set:
    ...


def level2_candidate_generation(level_1_candidates_dict: dict, transaction_db: list, param_db: ParameterData) -> od:
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
                # print(l[0], h[0])
                # print(f"|{item_support:.05f} - {candidate_support:.05f}| =", abs(item_support - candidate_support), f" <= {param_db.support_difference_constraint:.05f}")
                # print(f"{item_support} >= {param_db.mis_per_item[l[0]]:.05f}")
                if item_support >= param_db.mis_per_item[l[0]] and (abs(item_support - candidate_support) <= param_db.support_difference_constraint): # if the items meet the SDC then combine and add
                    # print(f"Added ({l[0]}, {h[0]})")
                    candidate_2_set[(l[0], h[0])] = None
                # print()

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
        # print(itemset_chunk)
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
                        # print(tuple(list(itemset) + [check_pair[-1]]))
                        # return None
                        # print(f"Found candidate {tuple(list(itemset) + [check_pair[-1]])}")
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
    print("Running initial pass...")
    # step 1: record the support counts of each item for all transactions.
    candidate_db = od()
    for transaction in transactions:
        # print(transaction)
        for item in transaction:
            if ((item,)) not in candidate_db:
                candidate_db[(item,)] = ItemData()
            candidate_db[(item,)].count += 1

    # debug print support count
    print("Here are the initial supports for each item...")
    for item in candidate_db:
        print(f"{item} support = {candidate_db[item].count} / {len(transactions)}")
    print("")

    print("Getting candidate items through minimum supports...")
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
    # develop the first set of 1-frquent itemsets
    frequent_items = {1: od()}
    for item in candidates_dict["seeds"]:
        if candidates_dict["supports"][item].count / len(transaction_db) >= param_db.mis_per_item[item[0]]:
            frequent_items[1][item] = None

    # debug
    print("1-frequent itemsets: ")
    print_itemsets(frequent_items[1])

    # next we generate frequent itemsets until we can't no mo'
    k_frequency = 2
    candidate_counts = od()
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

        print(f"Level {k_frequency} candidates")
        print_itemsets(level_k_candidates)

        for transaction in transaction_db:
            for candidate in level_k_candidates:
                # add the candidate if it does not exist
                if candidate not in candidate_counts:
                    candidate_counts[candidate] = 0

                if candidate[1:] not in candidate_counts:
                   candidate_counts[candidate[1:]] = 0

                if set(candidate).issubset(transaction): # if the candidate is in the transaction
                    # print(candidate, "is a subset of", transaction)                
                    candidate_counts[candidate] += 1

                if set(candidate[1:]).issubset(transaction): # if the tail is in the transaction (todo:: should we be doing this for every set of candidates)
                    # print(candidate[1:], "tail is a subset of", transaction)
                    candidate_counts[candidate[1:]] += 1

        # update the frequent candidates list 
        for c in level_k_candidates:
            # print(f"Candidate: {c}")
            # print(f"{candidate_counts[c]} / {n_transactions} >= {param_db.mis_per_item[c[0]]}")
            if Decimal(candidate_counts[c]) / Decimal(n_transactions) >= param_db.mis_per_item[c[0]]:
                frequent_items[k_frequency][c] = None

        # move to next frequency
        k_frequency += 1
        last_itemset = frequent_items[k_frequency-1]

    return frequent_items,candidate_counts

if __name__ == "__main__":
    parser = ap()
    parser.add_argument("-t", "--transactions", help="The input for database transactions.")
    parser.add_argument("-p", "--params", help="Parameters input")
    parser.add_argument("--test", help="Test file to check output against", default="")

    args = parser.parse_args()

    transaction_db = []
    params = ParameterData()
    
    # initialize data for apriori
    parse_transactions_file(args.transactions, transaction_db, params)
    params = parse_params_cfg(args.params, params)
    params.sort_mis_dict_by_value()

    frequent_items,candidate_counts = msapriori(transaction_db=transaction_db, param_db=params)

    for k,itemsets in frequent_items.items():
        print(f"Itemsets for k={k}:")
        print_itemsets(itemsets)

    print("Ran MS-Apriori with...")
    print("Transactions:")
    print(transaction_db)
    print("Parameter data:")
    print(params)
    print("")

    # if we want to test the output against a specific file
    if args.test != "":
        ...