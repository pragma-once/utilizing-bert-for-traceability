import os
import pathlib
import sys

def copy_jsonl_file(source_path: str, destination_path: str):
    print("Copy: " + source_path + " --> " + destination_path)

    input_file = open(source_path, 'r')
    text = input_file.read()
    input_file.close()

    output_file = open(destination_path, 'w+', encoding="utf-8")
    output_file.write(text)
    output_file.close()

def main(input_directory: str, input_aug_directory, output_directory: str):
    jsonl_paths = list(pathlib.Path(input_directory).glob("*.jsonl"))
    train_paths = [str(path).replace('\\', '/') for path in jsonl_paths if str(path).endswith(".train.jsonl")]
    valid_paths = [str(path).replace('\\', '/') for path in jsonl_paths if str(path).endswith(".valid.jsonl")]
    test_paths = [str(path).replace('\\', '/') for path in jsonl_paths if str(path).endswith(".test.jsonl")]
    aug_jsonl_paths = list(pathlib.Path(input_aug_directory).glob("*.jsonl"))
    aug_train_paths = [str(path).replace('\\', '/') for path in aug_jsonl_paths if str(path).endswith(".train.jsonl")]
    #aug_valid_paths = [str(path).replace('\\', '/') for path in aug_jsonl_paths if str(path).endswith(".valid.jsonl")]
    #aug_test_paths = [str(path).replace('\\', '/') for path in aug_jsonl_paths if str(path).endswith(".test.jsonl")]
    for train_path in train_paths:
        formatless_path = train_path[:-len(".train.jsonl")]
        valid_path = formatless_path + ".valid.jsonl"
        test_path = formatless_path + ".test.jsonl"
        formatless_name = formatless_path[formatless_path.rfind("/") + 1:]
        aug_formatless_path = os.path.join(input_aug_directory, formatless_name).replace('\\', '/')
        aug_train_path = aug_formatless_path + ".train.jsonl"
        #aug_valid_path = aug_formatless_path + ".valid.jsonl"
        #aug_test_path = aug_formatless_path + ".test.jsonl"
        train_name = train_path[train_path.rfind("/") + 1:]
        valid_name = valid_path[valid_path.rfind("/") + 1:]
        test_name = test_path[test_path.rfind("/") + 1:]
        if (
                    valid_path in valid_paths
                    and test_path in test_paths
                    and aug_train_path in aug_train_paths
                    #and aug_valid_path in aug_valid_paths
                    #and aug_test_path in aug_test_paths
                ):
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
            aug_train_name = formatless_name + ".aug.train.jsonl"
            #aug_valid_name = formatless_name + ".aug.valid.jsonl"
            #aug_test_name = formatless_name + ".aug.test.jsonl"
            copy_jsonl_file(aug_train_path, os.path.join(train_dir, aug_train_name))
            #copy_jsonl_file(aug_valid_path, os.path.join(valid_dir, aug_valid_name))
            #copy_jsonl_file(aug_test_path, os.path.join(test_dir, aug_test_name))

if __name__ == "__main__":
    if len(sys.argv) == 4:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Parameters: <input-divided-jsonl-files-directory> <input-divided-aug-files-directory> <output-data-directory-to-export-dirs-to>")
