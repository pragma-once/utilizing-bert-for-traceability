import json
import sys

def main(input_filename: str, output_filename: str, word_set_similarity_threshold: float):
    print("Input file: " + input_filename)
    print("Output file: " + output_filename)
    print("Similarity threshold: " + str(word_set_similarity_threshold))
    print()
    print("Reading " + input_filename + "...")
    with open(input_filename, 'r') as file:
        input_lines = [line.strip() for line in file.readlines()]
    print("Filtering out adjacent rows with similar NL data...")
    output_lines = []
    last_not_removed_nl_set = set([])
    for line in input_lines:
        json_obj = json.loads(line)
        nl = ' '.join(json_obj["docstring_tokens"])
        nl = nl[:nl.find("<p >")]
        if len(nl.split()) < 10:
            continue
        #pl = ' '.join([' '.join(token.split()) for token in json_obj["code_tokens"]])
        nl_set = set(nl.split())
        if len(last_not_removed_nl_set) != 0 and \
                (float(len(nl_set.intersection(last_not_removed_nl_set))) / float(min(len(nl_set), len(last_not_removed_nl_set)))) \
                    >= word_set_similarity_threshold:
            continue
        output_lines.append(line)
        last_not_removed_nl_set = nl_set
    print("Input rows: " + str(len(input_lines)))
    print("Output rows: " + str(len(output_lines)) + " (" + str(100 * float(len(output_lines)) / float(len(input_lines))) + "%)")
    print("Writing to " + output_filename + "...")
    file = open(output_filename, "w+", encoding="utf-8")
    file.write('\n'.join(output_lines))
    file.close()

if __name__ == "__main__":
    if len(sys.argv) == 4:
        main(sys.argv[1], sys.argv[2], float(sys.argv[3]))
    else:
        print("Usage: python filter-intermediate-test-data.py <input-jsonl-filename> <output-jsonl-filename> <word-set-similarity-threshold>")
