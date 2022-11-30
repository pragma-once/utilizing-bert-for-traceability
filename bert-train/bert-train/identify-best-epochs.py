import ast
import os
import pathlib
import sys

def join_if_exists(path1, path2):
    result = os.path.join(path1, path2)
    if not os.path.exists(result):
        return None
    return result

def main(dir: str):
    checkpoint_dirs = [str(item) for item in list(pathlib.Path(dir).glob("checkpoint-epoch-*"))]
    if len(checkpoint_dirs) == 0:
        print("No 'checkpoint-epoch-*' found in the directory.")
        return
    epochs = {}
    max_metrics = {
        "valid_accuracy": (0, []),
        "(valid) precision@3": (0, []),
        "(valid) best_f1": (0, []),
        "(valid) MAP (@3)": (0, [])
    }
    for checkpoint_dir in checkpoint_dirs:
        if not os.path.isdir(checkpoint_dir):
            continue
        valid_results_path = join_if_exists(checkpoint_dir, "valid-results.txt")
        if valid_results_path == None:
            continue
        tbert_path = join_if_exists(checkpoint_dir, "t_bert.pt")
        optimizer_path = join_if_exists(checkpoint_dir, "optimizer.pt")
        with open(valid_results_path, 'r') as file:
            valid_results = ast.literal_eval(file.read())
        for metric in max_metrics:
            if valid_results[metric] > max_metrics[metric][0]:
                max_metrics[metric] = (valid_results[metric], [ checkpoint_dir ])
            elif valid_results[metric] == max_metrics[metric][0]:
                max_metrics[metric][1].append(checkpoint_dir)
        epochs[checkpoint_dir] = {
            "tbert_path": tbert_path,
            "optimizer_path": optimizer_path,
            "valid_results_path": valid_results_path,
            "valid_results": valid_results
        }
    best_epochs_metrics = {}
    for metric in max_metrics:
        for epoch in max_metrics[metric][1]:
            if epoch not in best_epochs_metrics:
                best_epochs_metrics[epoch] = {}
            best_epochs_metrics[epoch][metric] = max_metrics[metric][0]
    not_best_epochs = set(epochs.keys()) - set(best_epochs_metrics.keys())
    print()
    print("BEST EPOCHS:")
    print()
    for epoch in best_epochs_metrics:
        print(epoch + " by " + str(best_epochs_metrics[epoch]))
    print()
    print("NOT BEST EPOCHS:")
    print()
    for epoch in not_best_epochs:
        print(epoch)
    to_remove = []
    for epoch in not_best_epochs:
        tbert_path = epochs[epoch]["tbert_path"]
        optimizer_path = epochs[epoch]["optimizer_path"]
        if tbert_path != None:
            to_remove.append(tbert_path)
        if optimizer_path != None:
            to_remove.append(optimizer_path)
    if len(to_remove) != 0:
        remove_command = "rm -v"
        for item in to_remove:
            remove_command += ' ' + item
        print()
        print("REMOVE COMMAND:")
        print()
        print(remove_command)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Params: <output-models-directory>")
    else:
        main(sys.argv[1])
