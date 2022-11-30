import sys

def main(input_filename: str, train_proportion, valid_proportion, test_proportion = None):
    if not input_filename.endswith(".jsonl"):
        print("This is not a .jsonl file.")
    if train_proportion + valid_proportion > 1:
        print("Wrong parameters: train_proportion + valid_proportion > 1")
        return
    if test_proportion != None and train_proportion + valid_proportion + test_proportion > 1:
        print("Wrong parameters: train_proportion + valid_proportion + test_proportion > 1")
        return
    train_filename = input_filename[:-len(".jsonl")] + ".train.jsonl"
    valid_filename = input_filename[:-len(".jsonl")] + ".valid.jsonl"
    test_filename = input_filename[:-len(".jsonl")] + ".test.jsonl"
    file = open(input_filename, "r")
    lines = [line.strip() for line in file.readlines()]
    file.close()
    lines_count = len(lines)
    train_count = round(lines_count * train_proportion)
    valid_count = round(lines_count * valid_proportion)
    test_count = lines_count - (train_count + valid_count) if test_proportion == None else min(
        round(lines_count * test_proportion), lines_count - (train_count + valid_count)
    )
    print("input file: " + input_filename)
    print("output files: " + train_filename + ", " + valid_filename + ", " + test_filename)
    print("total: " + str(lines_count))
    print("train: " + str(train_count) + " (" + str(float(train_count) / lines_count * 100) + "%)")
    print("valid: " + str(valid_count) + " (" + str(float(valid_count) / lines_count * 100) + "%)")
    print("test: " + str(test_count) + " (" + str(float(test_count) / lines_count * 100) + "%)")
    train_lines = []
    valid_lines = []
    test_lines = []
    print("Separating train, valid and test...")
    for i in range(test_count):
        test_lines.append(lines.pop(0))
    for i in range(valid_count):
        valid_lines.append(lines.pop(0))
    for i in range(train_count):
        train_lines.append(lines.pop(0))
    print("Writing to " + train_filename + "...")
    file = open(train_filename, "w+", encoding="utf-8")
    file.write('\n'.join(train_lines))
    file.close()
    print("Writing to " + valid_filename + "...")
    file = open(valid_filename, "w+", encoding="utf-8")
    file.write('\n'.join(valid_lines))
    file.close()
    print("Writing to " + test_filename + "...")
    file = open(test_filename, "w+", encoding="utf-8")
    file.write('\n'.join(test_lines))
    file.close()
    if len(lines) != 0:
        print(
            "[ATTENTION] There are "
            + str(len(lines))
            + " remaining lines that are not in the outputs. You can use 2 proportion parameters to use all of them."
        )

if __name__ == "__main__":
    if len(sys.argv) == 4:
        main(sys.argv[1], float(sys.argv[2]) / 100, float(sys.argv[3]) / 100)
    elif len(sys.argv) == 5:
        main(sys.argv[1], float(sys.argv[2]) / 100, float(sys.argv[3]) / 100, float(sys.argv[4]) / 100)
    else:
        print("Parameters: <jsonl-filename> <train-proportion-percent> <valid-proportion-percent> [<test-proportion-percent>]")
