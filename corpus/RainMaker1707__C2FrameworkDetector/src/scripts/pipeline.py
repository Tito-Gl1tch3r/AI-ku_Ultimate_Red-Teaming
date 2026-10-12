"""
Compute the Precision, Recall and F1 score from the results of classification.
Then format a string with the separator to eventually save it in a csv
"""
def score_to_csv(true_pos, false_pos, true_neg, false_neg, path, separator=",", thread_id="Tests"):
    scores = score(true_pos, true_neg, false_pos, false_neg)
    to_write = f'{thread_id}{separator}{true_pos}{separator}{true_neg}{separator}{false_pos}{separator}{false_neg}{separator}'
    to_write += f'{scores.get("P")}{separator}{scores.get("R")}{separator}{scores.get("F1")}\n'
    with open(path, 'a') as file:
        file.write(to_write)
        file.close()



"""
Return precision, recall and F1 score from the results of the classification
@params: true_pos: integer 
@params: true_neg: integer
@params: false_pos: integer
@params: false_neg: integer
@returns: dictionary containing the 3 scores 
        KEYS: P for precision, R for recall and F1 for f1-score 
"""
def score(true_pos, true_neg, false_pos, false_neg):
    precision = 1
    recall = 1
    f1_score = 1
    return {"P": precision, "R": recall, "F1": f1_score}


def load_thread(thread_file):
    pass


def pipeline():
    pass

if __name__ == "__main__":
    import argparse
    from utils import *
    parser = argparse.ArgumentParser()
    parser.add_argument("configs")
    parser.add_argument("csv_out")

    args = parser.parse_args()


    configs, client = config(args.configs, args.csv_out)
    score_to_csv(0,1,0,0,args.csv_out)

else:
    from scripts.utils import *

