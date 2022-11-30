import os

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, BertConfig, PreTrainedModel

class TBertS(PreTrainedModel):
    def __init__(self):
        super().__init__(BertConfig())
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
        self.bert = AutoModelForSequenceClassification.from_pretrained("microsoft/codebert-base")

    def forward(self, input_ids, attention_mask, token_type_ids, relation_label=None):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids,
                            labels=relation_label)
        res = dict()
        if relation_label is not None:
            loss = outputs[0]
            res['loss'] = loss
            logits = outputs[1]
            res['logits'] = logits
        else:
            logits = outputs[0]
            res['logits'] = logits
        return res

    def get_sim_score(self, input_ids, attention_mask, token_type_ids):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        logits = outputs[0]
        sim_scores = torch.softmax(logits, 1).data.tolist()
        return [x[1] for x in sim_scores]

    def get_nl_tokenizer(self):
        return self.tokenizer

    def get_pl_tokenizer(self):
        return self.tokenizer

def load_model(path: str):
    if path == None or not os.path.exists(path):
        return None
    model = TBertS()
    model.load_state_dict(torch.load(path, map_location=torch.device('cpu')))
    return model

def get_scores(nl_list, pl_list, model):
    input = {
        "input_ids": [],
        "attention_mask": [],
        "token_type_ids": []
    }
    with torch.no_grad():
        model.eval()
        for i in range(min(len(nl_list), len(pl_list))):
            feature = model.tokenizer.encode_plus(
                text=nl_list[i],
                text_pair=pl_list[i],
                #pad_to_max_length=True, # deprecated
                padding="max_length",
                return_attention_mask=True,
                return_token_type_ids=True,
                max_length=512,
                add_special_tokens=True
            )
            input["input_ids"].append(torch.tensor(feature["input_ids"], dtype=torch.long))
            input["attention_mask"].append(torch.tensor(feature["attention_mask"], dtype=torch.long))
            input["token_type_ids"].append(torch.tensor(feature["token_type_ids"], dtype=torch.long))
        input["input_ids"] = torch.stack(input["input_ids"]).to(model.device)
        input["attention_mask"] = torch.stack(input["attention_mask"]).to(model.device)
        input["token_type_ids"] = torch.stack(input["token_type_ids"]).to(model.device)
        return model.get_sim_score(**input)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Run this script to test the inference.")
        print("Parameters: <model-path1> [<model-path2> ...]")
    else:
        nl_list = [
            "Prints Hello world",
            "Adds the 2 numbers",
            "Prints Hello world",
            "Adds the 2 numbers",
        ]
        pl_list = [
            "public static void main ( String [ ] args ) { System . out . println ( \"Hello world\" ) ; }",
            "public static void main ( String [ ] args ) { System . out . println ( \"Hello world\" ) ; }",
            "public add ( int a , int b ) { return a + b ; }",
            "public add ( int a , int b ) { return a + b ; }",
        ]
        print("Loading models...")
        models = [load_model(model_path) for model_path in sys.argv[1:]]
        print("Models loaded.")
        for i in range(len(models)):
            print("MODEL " + str(i) + ": " + sys.argv[i + 1])
        scores_of_models = [get_scores(nl_list, pl_list, model) for model in models]
        for i in range(len(scores_of_models[0])):
            print()
            print("NL: " + nl_list[i])
            print("PL: " + pl_list[i])
            for j in range(len(scores_of_models)):
                scores = scores_of_models[j]
                print("SCORE OF MODEL " + str(j) + ": " + f"{scores[i]:.20f}")#str(scores[i]))
