import os
import httpx
import json
import asyncio
from datasets import Dataset
from difflib import SequenceMatcher


def read_test_data(path):
    test_data = Dataset.from_json(path)
    return test_data


def hit_api_request(row):

    try: 
        response = httpx.post(
            "http://localhost:5000/api/deeppass2",
            data = row["document"],
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        
        if response.status_code == 200:
            json_response = response.json()
            print(json_response)
            try:
                row["BERT"] = json_response["Success"][1]["BERT_secrets"][0]["secret"]
                
            except Exception as e:
                row["BERT"] = ["No Secret"]
                
            
            try:
                row["LLM"] = json_response["Success"][2]["LLM_scanning"][0]["Extracted_Credentials"]
            except Exception as e:
                row["LLM"] = ["No Secret"]
                
        else:
            row["LLM"] = ["API-FAIL"]
            row["BERT"] = ["API-FAIL"]
    except Exception as e:
        row["LLM"] = ["API-TIMED-OUT"]
        row["BERT"] = ["API-TIMED-OUT"]
        print(e)

    return row


def _string_overlap_ratio(s1, s2, min_ratio=0.5):
    if not s1 or not s2:
        return s1 == s2  # Both empty or one empty
    similarity = SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
    return similarity >= min_ratio


def _areEqualOverlapStrings(y_true, y_pred, min_overlap=0.5, string_min_ratio=0.5):
    if not y_true and not y_pred:
        return True

    if not y_true or not y_pred:
        return False

    # Find matches between strings in the lists
    matches = 0
    used_pred_indices = set()

    for true_item in y_true:
        best_match_idx = None
        best_similarity = 0

        for pred_idx, pred_item in enumerate(y_pred):
            if pred_idx in used_pred_indices:
                continue

            # Check if strings are similar enough
            if _string_overlap_ratio(true_item, pred_item, string_min_ratio):
                similarity = SequenceMatcher(
                    None, true_item.lower(), pred_item.lower()
                ).ratio()

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_idx = pred_idx

        if best_match_idx is not None:
            matches += 1
            used_pred_indices.add(best_match_idx)

    # Calculate overall overlap
    longer_length = max(len(y_true), len(y_pred))
    overlap_ratio = matches / longer_length

    return overlap_ratio >= min_overlap


def _calculate_accuracy(
    y_true,
    y_pred,
    type="strict",
    min_overlap=0.5,
    string_min_ratio=0.5,
    method="sequence",
):
    correct = 0
    tot = 0
    length = len(y_true)

    if type == "strict":
        for i in range(length):
            if y_pred[i] == ["No Secret"]:
                y_pred[i] =[]
            if len(y_true[i]) == len(y_pred[i]) and set(y_true[i]) == set(y_pred[i]):
                correct += 1
        accuracy = correct / length
    elif type == "string_overlap":
        for i in range(length):
            if y_pred[i] == ["No Secret"]:
                y_pred[i] =[]
            if _areEqualOverlapStrings(
                y_true[i], y_pred[i], min_overlap, string_min_ratio
            ):
                correct += 1
        accuracy = correct / length
    elif type == "number":
        for i in range(length):
            tot += len(y_true[i])
            if y_pred[i] == ["No Secret"]:
                y_pred[i]=[]
            for pred in y_pred[i]:
                if pred in y_true[i]:
                    correct += 1
        accuracy = correct / tot

    return accuracy


def _calculate_confusionmetrics(y_true, y_pred):
    length = len(y_true)
    tn = 0
    tp = 0
    fp = 0
    fn = 0
    overlaping_tp=0

    tp_list = []
    fp_list = []
    fn_list = []
    overlaping_tp_list=[]
    for i in range(length):
        if y_pred[i] == ["API-FAIL"] or y_pred[i] == ["API-TIMED-OUT"]:
            continue
        if y_true[i] == [] and y_pred[i] == []:
            tn +=1
        elif set(y_true[i]) == set(y_pred[i]):
            tp += len(y_true[i])
            tp_list.extend(y_pred[i])
        else:
            for pred in y_pred[i]:
                if pred in y_true:
                    tp +=1
                    tp_list.extend(pred)
                elif sum([_string_overlap_ratio(pred, gt,0.3) for gt in y_true[i]])==0:
                    fp +=1
                    fp_list.append(pred)
                else:
                    overlaping_tp_list.append(pred)
                    overlaping_tp+=1
            
            for gt in y_true[i]:
                if gt not in y_pred[i] and sum([_string_overlap_ratio(gt, pred,0.3) for pred in y_pred[i]])==0:
                    fn +=1
                    fn_list.append(gt)

    return tn, tp, fp, fn,overlaping_tp, tp_list, fp_list, fn_list, overlaping_tp_list


def calculate_metrics(y_true, y_pred):
    accuracy_strict = _calculate_accuracy(y_true, y_pred, type="strict")
    accuracy_overlap = _calculate_accuracy(y_true, y_pred, type="string_overlap")

    accuracy_number = _calculate_accuracy(y_true, y_pred, type="number")

    tn, tp, fp, fn,overlaping_tp, tp_list, fp_list, fn_list, overlaping_tp_list = _calculate_confusionmetrics(y_true, y_pred)

    results = {
        "accuracy_strict": accuracy_strict,
        "accuracy_overlap": accuracy_overlap,
        "accuracy_number": accuracy_number,
        "tn": tn,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "overlaping_tp": overlaping_tp,

        ## Uncomment if you need to see the actual examples. However, this will cause an explosion of data.

        # "tp_list": tp_list,
        # "fp_list": fp_list,
        # "fn_list": fn_list,
        # "overlaping_tp_list": overlaping_tp_list
    }

    return results

def save_results(path, metrics):
    with open(path, 'w') as f:
        json.dump(metrics, f, indent=2)


def run_evaluation(path):
    
    test_data_with_preds = read_test_data("evaluation_results/deeppass2/preds_1.json")
    performance_bert = calculate_metrics(
        test_data_with_preds["cred"], test_data_with_preds["BERT"]
    )
    print(f"BERT performance:\n Strict accuracy: {performance_bert}")
    save_results("evaluation_results/deeppass2/BERT_performance.json", performance_bert)

    performance_LLM = calculate_metrics(
        test_data_with_preds["cred"], test_data_with_preds["LLM"]
    )
    print(f"LLM performance:\n {performance_LLM}")
    save_results("evaluation_results/deeppass2/LLM_performance.json", performance_LLM)

if __name__ =="__main__":
    run_evaluation("./Dataset/test/test_plain.json")
