import re

from collections import OrderedDict as od
from argparse import ArgumentParser as ap
from dataclasses import dataclass


@dataclass
class ParameterData:
    mis_per_item = od()
    support_difference_constraint: float = 0
    min_confidence: float = 0

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
                        if param_data.mis_per_item[key] == None:
                            param_data.mis_per_item[key] = float(pps[1])
                else:
                    param_data.mis_per_item[mis_decl] = float(pps[1])
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
            transaction_db.append(set(transaction.split(",")))
            for item in transaction.split(","): # insert any items into the param db
                if item not in param_data.mis_per_item:
                    param_data.mis_per_item[item] = None


def compare_with_key(result: str, check: str):
    return False


def generate_rules():
    ...


def msapriori():
    ...


def candidate_generation():
    ...


if __name__ == "__main__":
    parser = ap()
    parser.add_argument("-t", "--transactions", help="The input for database transactions.")
    parser.add_argument("-p", "--params", help="Parameters input")

    args = parser.parse_args()

    transaction_db = []
    params = ParameterData()
    
    # initialize data for apriori
    parse_transactions_file(args.transactions, transaction_db, params)
    params_db = parse_params_cfg(args.params, params)

    print(transaction_db)
    print(params)