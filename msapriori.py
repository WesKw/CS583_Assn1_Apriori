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
        


def parse_params_cfg(path: str) -> ParameterData:
    data = ParameterData()

    with open(path) as params_file:
        for line in params_file:
            pps = "".join(line.split()).split("=") # remove whitespace and split by =

            if "MIS" in pps[0]:
                items = re.findall(r"[\d.]+", pps[0] + pps[1]) # find both item name and MIS value
                print(items)
                data.mis_per_item[items[0]] = items[1]
            elif "SDC" in pps[0]:
                data.support_difference_constraint = float(pps[1])
            elif "minconf" in pps[0]:
                data.min_confidence = int(pps[1][:-1]) / 100 # min confidence is given as a percentage

    return data


def parse_transactions_file(path: str):
    ...


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
    
    # initialize data for apriori
    # with open(args.transactions) as transactions_file:
        # transaction = "".join(transactions_file.readline().split()).split(",")

    params_db = parse_params_cfg(args.params)