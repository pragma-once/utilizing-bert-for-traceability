import os
import pathlib
import sys

def copy_jsonl_file(source_path: str, destination_path: str):
    input_file = open(source_path, 'r')
    text = input_file.read()
    input_file.close()

    output_file = open(destination_path, 'w+', encoding="utf-8")
    output_file.write(text)
    output_file.close()

def main(input_directory: str, output_directory: str):
    jsonl_paths = list(pathlib.Path(input_directory).glob("*.jsonl"))
    train_paths = [str(path) for path in jsonl_paths if str(path).endswith(".train.jsonl")]
    valid_paths = [str(path) for path in jsonl_paths if str(path).endswith(".valid.jsonl")]
    test_paths = [str(path) for path in jsonl_paths if str(path).endswith(".test.jsonl")]
    for train_path in train_paths:
        formatless_path = train_path[:-len(".train.jsonl")]
        valid_path = formatless_path + ".valid.jsonl"
        test_path = formatless_path + ".test.jsonl"
        formatless_name = formatless_path[formatless_path.replace('\\', '/').rfind("/") + 1:]
        train_name = train_path[train_path.replace('\\', '/').rfind("/") + 1:]
        valid_name = valid_path[valid_path.replace('\\', '/').rfind("/") + 1:]
        test_name = test_path[test_path.replace('\\', '/').rfind("/") + 1:]
        if valid_path in valid_paths and test_path in test_paths:
            print(formatless_name + "...")
            train_dir = os.path.join(output_directory, formatless_name, "train")
            valid_dir = os.path.join(output_directory, formatless_name, "valid")
            test_dir = os.path.join(output_directory, formatless_name, "test")
            os.makedirs(train_dir)
            os.makedirs(valid_dir)
            os.makedirs(test_dir)
            copy_jsonl_file(train_path, os.path.join(train_dir, train_name))
            copy_jsonl_file(valid_path, os.path.join(valid_dir, valid_name))
            copy_jsonl_file(test_path, os.path.join(test_dir, test_name))

if __name__ == "__main__":
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print("Parameters: <input-divided-jsonl-files-directory> <output-data-directory-to-export-dirs-to>")
