import ast
import inference
import sys

if len(sys.argv) < 2:
    print("Run this script to test the inference.")
    print("Parameters: <model-path1> [<model-path2> ...]")
else:
    print("Loading models...")
    models = [inference.load_model(model_path) for model_path in sys.argv[1:]]
    print("Models loaded.")
    while True:
        with open("inference-test.txt", 'r') as file:
            text = file.read()
            nlpl = ast.literal_eval(text)
            nl_list = nlpl["nl"]
            pl_list = nlpl["pl"]
        for i in range(len(models)):
            print("MODEL " + str(i) + ": " + sys.argv[i + 1])
        scores_of_models = [inference.get_scores(nl_list, pl_list, model) for model in models]
        for i in range(len(scores_of_models[0])):
            print()
            print("NL: " + nl_list[i])
            print("PL: " + pl_list[i])
            for j in range(len(scores_of_models)):
                scores = scores_of_models[j]
                print("SCORE OF MODEL " + str(j) + ": " + f"{scores[i]:.20f}")
        input("Press enter to score inference-test.txt items again...")
