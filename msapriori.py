import re

from collections import OrderedDict as od
from argparse import ArgumentParser as ap
from dataclasses import dataclass


@dataclass
class ItemData:
    count: int = 0


@dataclass
class ParameterData:
    mis_per_item = od()
    support_difference_constraint: float = 0
    min_confidence: float = 0

    def sort_mis_dict_by_value(self):
        self.mis_per_item = od(sorted(self.mis_per_item.items(), key=lambda x: (x[1], x[0])))

    def __str__(self) -> str:
        to_str = (f"SDC = {self.support_difference_constraint}\n" + 
                  f"Min confidence = {self.min_confidence}\n")
        
        for key,value in self.mis_per_item.items():
            to_str += f"\nMIS({key}) = {value}"

        return to_str
        

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
                            param_data.mis_per_item[key] = float(pps[1])
                else:
                    param_data.mis_per_item[int(mis_decl)] = float(pps[1])
            elif "SDC" in pps[0]:
                param_data.support_difference_constraint = float(pps[1])
            elif "minconf" in pps[0]:
                param_data.min_confidence = int(pps[1][:-1]) / 100 # min confidence is given as a percentage

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
    candidate_set = od()
    n_trans = len(transaction_db)
    candidates = level_1_candidates_dict["seeds"]
    supports = level_1_candidates_dict["supports"]
    # candidates = L.items()
    for idx,candidate in enumerate(candidates):
        # check MIS count
        candidate_support = supports[candidate].count / n_trans
        if candidate_support >= param_db.mis_per_item[candidate[0]]: # check if the candidate meets the minimum support
            for item in candidates[idx+1:]: # for each item in the candidate list after the current candidate
                item_support = supports[item].count / n_trans
                if item_support and (abs(item_support - candidate_support) <= param_db.support_difference_constraint): # if the items meet the SDC then combine and add
                    candidate_set[(candidate[0], item[0])] = None

    return candidate_set


def ms_candidate_generation(level_k_candidates, param_db: ParameterData) -> set:
    ...


# initial pass steps:
# 1) Find support counts of each item
# 2) Follow sorted MIS order to develop frequent 1-itemsets
def initial_pass(transactions: list, params: ParameterData) -> dict:
    print("Running initial pass...")
    # step 1: record the support counts of each item for all transactions.
    candidate_db = od()
    for transaction in transactions:
        print(transaction)
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

    print("Seeds obtained from minimum supports...")
    print(k1_frequent_itemsets)

    # we can return the seeds and support counts
    return {"seeds": k1_frequent_itemsets, "supports": candidate_db}


def msapriori(transaction_db: list, param_db: ParameterData):
    param_db.sort_mis_dict_by_value() # first, we sort the mis dict by the values of the minimum supports to create a total order.
    candidates_dict = initial_pass(transaction_db, param_db) # get 1-frequent candidates
    # develop the first set of 1-frquent itemsets
    frequent_items = od({1: od()})
    for item in candidates_dict["seeds"]:
        if candidates_dict["supports"][item].count / len(transaction_db) >= param_db.mis_per_item[item[0]]:
            frequent_items[1][item] = None

    # debug
    print("1-frequent itemsets: ")
    print(frequent_items)

    # next we generate frequent itemsets until we can't no mo'
    k_frequency = 2
    last_itemset = frequent_items[k_frequency-1]
    while(len(last_itemset) != 0):
        frequent_items[k_frequency] = od()
        level_k_candidates = set()
        # if k is 2 we use a special candidate generation function
        if k_frequency == 2:
            level_k_candidates = level2_candidate_generation(candidates_dict, transaction_db, param_db)
            print("Level 2 candidates:")
            for candidate in level_k_candidates:
                print(candidate)
        else:
            level_k_candidates = ms_candidate_generation(last_itemset, param_db)

        for transaction in transaction_db:
            for candidate in level_k_candidates:
                if candidate in transaction: # if the candidate is in the transaction
                    ...

                if candidate[1:] in transaction: # if the tail is in the transaction
                    ...

        # update the frequent candidates list 

        # move to next frequency
        k_frequency += 1

if __name__ == "__main__":
    parser = ap()
    parser.add_argument("-t", "--transactions", help="The input for database transactions.")
    parser.add_argument("-p", "--params", help="Parameters input")

    args = parser.parse_args()

    transaction_db = []
    params = ParameterData()
    
    # initialize data for apriori
    parse_transactions_file(args.transactions, transaction_db, params)
    params = parse_params_cfg(args.params, params)
    params.sort_mis_dict_by_value()

    msapriori(transaction_db=transaction_db, param_db=params)

    print("Ran MS-Apriori with...")
    print("Transactions:")
    print(transaction_db)
    print("Parameter data:")
    print(params)
    print("")