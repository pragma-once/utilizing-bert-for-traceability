import gensim
import gensim.corpora
import json
import multi_rake
import nltk
import nltk.stem
import nltk.tokenize
import os
import random
import sys
import time

import codfrel_row_transform_functions

POS_TAGS_TO_REMOVE = { "CC", "DT", "EX", "IN", "MD", "PDT", "POS", "PRP", "PRP$", "TO", "UH", "WDT", "WP", "WRB"}

def _filter_pos_tag(tokens: list[str]) -> list[str]:
    tokens = nltk.pos_tag(tokens)
    return [ item[0] for item in tokens if item[1] not in POS_TAGS_TO_REMOVE ]

def _lemmatization(tokens: list[str]) -> list[str]:
    lemmatizer = nltk.stem.WordNetLemmatizer()
    return [ lemmatizer.lemmatize(word) for word in tokens ]

def nl_get_tokens(nl_text: str) -> list[str]:
    # Tokenization
    result = [ word.lower() for word in nltk.tokenize.word_tokenize(nl_text) if word.isalpha() ]
    # POS Tagging
    result = _filter_pos_tag(result)
    # Lemmatization
    result = _lemmatization(result)
    return result

def nl_get_keywords(nl_text: str) -> list[str]:
    result = multi_rake.Rake().apply(nl_text)
    result = nl_get_tokens(' '.join([item[0] for item in result]))
    return result

def _pl_tokenize_name(name: str) -> list[str]:
    words = []
    current_word = ""
    for ch in name:
        if ch.isalpha():
            if len(current_word) != 0 and ch.isupper() and current_word[-1].islower():
                words.append(current_word)
                current_word = ""
            current_word += ch
        elif len(current_word) != 0:
            words.append(current_word)
            current_word = ""
    if len(current_word) != 0:
        words.append(current_word)
        current_word = ""
    return words

def _pl_tokenize_names(names: list[str]) -> list[str]:
    result = []
    for name in names:
        for word in _pl_tokenize_name(name):
            result.append(word)
    return result

JAVA_RESERVED_WORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class", "const",
    "continue", "default", "do", "double", "else", "enum", "extends", "final", "finally", "float",
    "for", "goto", "if", "implements", "import", "instanceof", "int", "interface", "long", "native",
    "new", "package", "private", "protected", "public", "return", "short", "static", "strictfp", "super",
    "switch", "synchronized", "this", "throw", "throws", "transient", "try", "void", "volatile", "while",
    "true", "false", "null",
}

def pl_get_tokens(pl_text: str) -> list[str]:
    # Tokenization 1
    result = ''.join([ ch if ch.isalpha() else ' ' for ch in pl_text ])
    result = result.split()
    # Reserved words removal
    result = [ token for token in result if token not in JAVA_RESERVED_WORDS ]
    # Tokenization 2
    result = [ word.lower() for word in _pl_tokenize_names(result) ]
    # POS Tagging
    result = _filter_pos_tag(result)
    # Lemmatization
    result = _lemmatization(result)
    return result

class NLItemInfo:
    def __init__(self, nl_index: int, tokens: list[str], keywords: list[str]):
        self.nl_index = nl_index
        self.tokens = tokens
        self.keywords = keywords

class PLLineInfo:
    def __init__(self, pl_index: int, line_index: int, global_pl_line_index: int, pl_item_total_lines: int, tokens: list[str]):
        self.pl_index = pl_index
        self.line_index = line_index
        self.global_pl_line_index = global_pl_line_index
        self.pl_item_total_lines = pl_item_total_lines
        self.tokens = tokens

class PopulationItem:
    def __init__(self, pl_lines: list[PLLineInfo], fitness_score: float = 0):
        self.pl_lines = pl_lines
        self.fitness_score = fitness_score

class CodfrelGeneticAlgorithm:
    def __init__(self, nl_list: list[str], pl_list: list[str], population_number_per_NL: int,
                 number_of_parents: int = 7, number_of_children: int = 21,
                 mutation_probability: int = 0.25, additive_mutation_probability: int = 0.5):
        self.nl_raw_items = nl_list
        self.pl_raw_items = pl_list
        self.population_number_per_NL = population_number_per_NL
        self.number_of_parents = number_of_parents
        self.number_of_children = number_of_children
        self.mutation_probability = mutation_probability
        self.additive_mutation_probability = additive_mutation_probability
        self.nl_items: list[NLItemInfo] = []
        self.pl_lines: list[PLLineInfo] = []
        self.pl_lines_containing_keywords: dict[NLItemInfo, list[PLLineInfo]] = {}
        self.populations: dict[NLItemInfo, list[PopulationItem]] = {}
        self.global_iteration_number = 0
        self.iteration_numbers: dict[NLItemInfo, int] = {}
        self.interrupted_via_keyboard_interrupt = False

        # self.nl_items
        for nl_index in range(len(self.nl_raw_items)):
            nl = self.nl_raw_items[nl_index]
            self.nl_items.append(NLItemInfo(nl_index, nl_get_tokens(nl), nl_get_keywords(nl)))

        # self.pl_lines
        for pl_index in range(len(self.pl_raw_items)):
            pl = self.pl_raw_items[pl_index]
            pl_lines_str = pl.splitlines()
            for line_index in range(len(pl_lines_str)):
                line = pl_lines_str[line_index]
                self.pl_lines.append(PLLineInfo(pl_index, line_index, len(self.pl_lines), len(pl_lines_str), pl_get_tokens(line)))

        # self.pl_lines_containing_keywords
        for nl in self.nl_items:
            self.pl_lines_containing_keywords[nl] = []
            for pl_line in self.pl_lines:
                if any(keyword in pl_line.tokens for keyword in nl.keywords):
                    self.pl_lines_containing_keywords[nl].append(pl_line)

        # self.populations
        for nl in self.nl_items:
            self.initialize_population(nl)
            self.iteration_numbers[nl] = 0

    def run(self, stopping_condition):
        try:
            nls_to_iterate = [nl for nl in self.nl_items if not stopping_condition(self, nl)]
            while len(nls_to_iterate) != 0:
                for nl in nls_to_iterate:
                    self.iterate_population(nl)
                self.global_iteration_number += 1
                nls_to_iterate = [nl for nl in self.nl_items if not stopping_condition(self, nl)]
            self.interrupted_via_keyboard_interrupt = False
        except KeyboardInterrupt:
            print("\nKeyboard interrupt. Stopping and finishing GA run...")
            for nl in self.nl_items:
                self._remove_population_duplicates(self.populations[nl])
                self.calculate_population_fitness(nl)
                self._sort_and_trim_population(nl)
            self.interrupted_via_keyboard_interrupt = True

    def _sort_population(self, population: list[PopulationItem]):
        population.sort(key=lambda x: x.fitness_score, reverse=True)

    def _sort_and_trim_population(self, nl: NLItemInfo):
        self._sort_population(self.populations[nl])
        if len(self.populations[nl]) > self.population_number_per_NL:
            self.populations[nl] = self.populations[nl][:self.population_number_per_NL]

    def _sort_item_pl_lines(self, pl_lines: list[PLLineInfo]):
        pl_lines.sort(key=lambda x: x.global_pl_line_index)

    def _is_guided_selection_completely_random(self, nl_item: NLItemInfo):
        return len(self.pl_lines_containing_keywords[nl_item]) == 0

    def _get_guided_selection_list(self, nl_item: NLItemInfo) -> list[PLLineInfo]:
        completely_random = self._is_guided_selection_completely_random(nl_item)
        return self.pl_lines if completely_random else self.pl_lines_containing_keywords[nl_item]

    def _select_new_guided_random_lines(self, selection_list: list[PLLineInfo]) -> list[PLLineInfo]:
        selection_center = random.choice(selection_list)
        lines_before = random.randrange(0, selection_center.line_index + 1)
        lines_after = random.randrange(0, selection_center.pl_item_total_lines - selection_center.line_index)
        start = selection_center.global_pl_line_index - lines_before
        stop = selection_center.global_pl_line_index + lines_after + 1
        lines = self.pl_lines[start:stop]
        # Remove empty lines
        i = 0
        while i < len(lines):
            if len(lines[i].tokens) == 0:
                lines.pop(i)
            else:
                i += 1
        return lines

    def _remove_population_duplicates(self, population: list[PopulationItem]):
        population_keys = set()
        i = 0
        while i < len(population):
            key = ",".join([str(item.global_pl_line_index) for item in population[i].pl_lines])
            if key not in population_keys: # New
                population_keys.add(key)
                i += 1
            else: # Repetitive
                population.pop(i)
                # No i increment

    def initialize_population(self, nl_item: NLItemInfo):
        if self._is_guided_selection_completely_random(nl_item):
            print("[Warning]: No PL line containing the NL keywords of NL[" + str(nl_item.nl_index) + "]. Randomly choosing for initialization.")
        population: list[PopulationItem] = []
        self.populations[nl_item] = population
        selection_list = self._get_guided_selection_list(nl_item)
        for i in range(self.population_number_per_NL):
            item_pl_lines = self._select_new_guided_random_lines(selection_list)
            # Already sorted, no need to _sort_item_pl_lines.
            population.append(PopulationItem(item_pl_lines))
        self._remove_population_duplicates(population)
        self.calculate_population_fitness(nl_item)
        self._sort_population(population)

    def calculate_population_fitness(self, nl_item: NLItemInfo):
        population = self.populations[nl_item]
        texts: list[list[str]] = []
        # PL items
        for item in population:
            text: list[str] = []
            for line in item.pl_lines:
                text += line.tokens
            texts.append(text)
        # NL item
        texts.append(nl_item.tokens)
        # LSI
        dictionary = gensim.corpora.Dictionary(texts)
        corpus = [dictionary.doc2bow(text) for text in texts]
        lsi_model = gensim.models.LsiModel(
            corpus=corpus, id2word=dictionary, num_topics=20
        )
        nl_vec = lsi_model[dictionary.doc2bow(nl_item.tokens)]
        for i in range(len(population)):
            cossim = gensim.matutils.cossim(
                nl_vec,
                lsi_model[dictionary.doc2bow(texts[i])]
            )
            population[i].fitness_score = (cossim + 1) / 2 # in range [0, 1]

    def iterate_population(self, nl_item: NLItemInfo):
        last_population = self.populations[nl_item].copy()
        score_sum = 0
        for item in last_population:
            score_sum += item.fitness_score
        if score_sum == 0:
            last_population_selection_weights = [1 / len(last_population) for item in last_population]
        else:
            last_population_selection_weights = [item.fitness_score / score_sum for item in last_population]
        selection_list = self._get_guided_selection_list(nl_item)
        population = self.populations[nl_item]
        # 1. Wheel selection, select parents with fitness/fitness_sum as probability
        parents = random.choices(last_population, last_population_selection_weights, k=self.number_of_parents)
        for i in range(self.number_of_children):
            parents_pair = random.choices(parents, k=2)
            # 2. Fusion
            child_pl_lines = set(parents_pair[0].pl_lines).union(parents_pair[1].pl_lines)
            # 3. Mutation
            if random.random() < self.mutation_probability:
                if random.random() < self.additive_mutation_probability:
                    child_pl_lines = child_pl_lines.union(set(self._select_new_guided_random_lines(selection_list)))
                elif len(child_pl_lines) >= 2:
                    number_of_removed_lines = random.randrange(1, int(len(child_pl_lines) / 2) + 1)
                    for i in range(number_of_removed_lines):
                        child_pl_lines.remove(random.choice(list(child_pl_lines)))
            # Final child construction
            child_pl_lines = list(child_pl_lines)
            self._sort_item_pl_lines(child_pl_lines)
            child = PopulationItem(child_pl_lines)
            population.append(child)
        # Remove duplicates
        self._remove_population_duplicates(population)
        # Calculate population fitness
        self.calculate_population_fitness(nl_item)
        # Sort and trim population
        self._sort_and_trim_population(nl_item)
        self.iteration_numbers[nl_item] += 1

class Dataset:
    def __init__(self,
                 jsonl_file_path: str,
                 nl_transform_func,
                 pl_transform_func,
                 max_nl_count: int|None = None,
                 max_pl_count: int|None = None,
                 max_link_count: int|None = None):
        self.nl_items: list[str] = []
        self.pl_items: list[str] = []
        self.nl_to_pl_links: dict[int, set[int]] = {}
        self.links_count = 0
        lines = []
        with open(jsonl_file_path) as file:
            lines = file.readlines()
        nl_to_id = {}
        pl_to_id = {}
        for line in lines:
            # Check link count
            if max_link_count != None and self.links_count >= max_link_count:
                break
            # Load strs from the row
            json_obj = json.loads(line)
            nl = nl_transform_func(json_obj)
            pl = pl_transform_func(json_obj)
            if nl == None or pl == None:
                continue
            # Check nl/pl counts
            if nl not in nl_to_id:
                if max_nl_count != None and len(self.nl_items) >= max_nl_count:
                    continue
            if pl not in pl_to_id:
                if max_pl_count != None and len(self.pl_items) >= max_pl_count:
                    continue
            # Determine indices (find or add)
            if nl in nl_to_id:
                nl_index = nl_to_id[nl]
            else:
                nl_index = len(self.nl_items)
                self.nl_items.append(nl)
                nl_to_id[nl] = nl_index
            if pl in pl_to_id:
                pl_index = pl_to_id[pl]
            else:
                pl_index = len(self.pl_items)
                self.pl_items.append(pl)
                pl_to_id[pl] = pl_index
            # Add link
            if nl_index not in self.nl_to_pl_links:
                self.nl_to_pl_links[nl_index] = set()
            self.nl_to_pl_links[nl_index].add(pl_index)
            self.links_count += 1

    def are_linked(self, nl_index: int, pl_index: int):
        return pl_index in self.nl_to_pl_links[nl_index]

class EvalMetrics:
    def __init__(self, rows: list[tuple[int, int, bool, bool, float, int, int]]):
        self.rows = rows

        self.tp = len([item for item in rows if item[2] and item[3]])
        self.fp = len([item for item in rows if not item[2] and item[3]])
        self.tn = len([item for item in rows if not item[2] and not item[3]])
        self.fn = len([item for item in rows if item[2] and not item[3]])

        if (self.tp + self.fp) == 0:
            self.precision = None
        else:
            self.precision = self.tp / (self.tp + self.fp)

        if (self.tp + self.fn) == 0:
            self.recall = None
        else:
            self.recall = self.tp / (self.tp + self.fn)

        if self.precision == None or self.recall == None or (self.precision + self.recall) == 0:
            self.f1 = None
            self.f2 = None
        else:
            self.f1 = 2 * ((self.precision * self.recall) / (self.precision + self.recall))
            self.f2 = (1 + 2 * 2) * ((self.precision * self.recall) / (2 * 2 * (self.precision + self.recall)))

        self.map_at: dict[int, float] = {}

    def get_rows_csv(self):
        text = "nl_index,pl_index,label,prediction,prediction_max_fitness_score,pl_pred_lines,pl_total_lines"
        for row in self.rows:
            text += '\n' + str(row[0]) \
                  + ',' + str(row[1]) \
                  + ',' + str(1 if row[2] else 0) \
                  + ',' + str(1 if row[3] else 0) \
                  + ',' + str(row[4]) \
                  + ',' + str(row[5]) \
                  + ',' + str(row[6])
        return text

    def calculate_map_metrics(self):
        if len(self.map_at) == 0:
            AT_STOP = 11
            ap_sum_at = {}
            for i in range(1, AT_STOP):
                ap_sum_at[i] = 0
            nl_to_pl: dict[int, list[tuple[int, bool, float]]] = {}
            for row in self.rows:
                if row[0] not in nl_to_pl:
                    nl_to_pl[row[0]] = []
                nl_to_pl[row[0]].append((row[1], row[2], row[4]))
            for nl in nl_to_pl:
                nl_to_pl[nl].sort(key=lambda x: (x[2], -x[0]), reverse=True)
            for nl in nl_to_pl:
                top_pl_indices = []
                r = {} # Relevance
                for (pl, label, pred) in nl_to_pl[nl]:
                    top_pl_indices.append(pl)
                    if pred == 0.0: # Not in the population
                        # Without this, the rows that are not in the population will count too,
                        # which would usually result in slightly lower MAP scores,
                        # because of including r=1 items with pred=0.0 sparsely, slightly lowering the APs.
                        r[len(top_pl_indices)] = 0
                    else:
                        r[len(top_pl_indices)] = 1 if label else 0
                    if len(top_pl_indices) >= AT_STOP - 1:
                        break
                if len(top_pl_indices) < AT_STOP - 1:
                    for i in range(len(top_pl_indices) + 1, AT_STOP):
                        r[i] = 0
                p_at = {}
                ap_at = {}
                relevant_count = 0
                ap_sum = 0
                for i in range(1, AT_STOP):
                    relevant_count += r[i]
                    p_at[i] = relevant_count / i
                    ap_sum += p_at[i] * r[i]
                    if relevant_count == 0:
                        ap_at[i] = 0
                    else:
                        ap_at[i] = ap_sum / relevant_count
                    ap_sum_at[i] += ap_at[i]
            self.map_at: dict[int, float] = {}
            for i in range(1, AT_STOP):
                self.map_at[i] = ap_sum_at[i] / len(nl_to_pl)

    def __str__(self):
        self.calculate_map_metrics()
        output_dict = {
            "tp": self.tp,
            "fp": self.fp,
            "tn": self.tn,
            "fn": self.fn,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "f2": self.f2
        }
        for i in self.map_at:
            output_dict["MAP@" + str(i)] = self.map_at[i]
        return str(output_dict)

class EvalMAPMetricsFromPopulation:
    def __init__(self, ga: CodfrelGeneticAlgorithm, dataset: Dataset):
        AT_STOP = 11
        ap_sum_at = {}
        for i in range(1, AT_STOP):
            ap_sum_at[i] = 0
        for nl in ga.nl_items:
            population = ga.populations[nl]
            top_pl_indices = []
            top_pl_indices_set = set()
            for item in population:
                for line in item.pl_lines:
                    if line.pl_index not in top_pl_indices_set:
                        top_pl_indices.append(line.pl_index)
                        top_pl_indices_set.add(line.pl_index)
                    if len(top_pl_indices) >= AT_STOP - 1:
                        break
                if len(top_pl_indices) >= AT_STOP - 1:
                    break
            r = {} # Relevance
            for i in range(1, AT_STOP):
                if i <= len(top_pl_indices):
                    r[i] = 1 if dataset.are_linked(nl.nl_index, top_pl_indices[i - 1]) else 0
                else:
                    r[i] = 0
            p_at = {}
            ap_at = {}
            relevant_count = 0
            ap_sum = 0
            for i in range(1, AT_STOP):
                relevant_count += r[i]
                p_at[i] = relevant_count / i
                ap_sum += p_at[i] * r[i]
                if relevant_count == 0:
                    ap_at[i] = 0
                else:
                    ap_at[i] = ap_sum / relevant_count
                ap_sum_at[i] += ap_at[i]
        self.map_at: dict[int, float] = {}
        for i in range(1, AT_STOP):
            self.map_at[i] = ap_sum_at[i] / len(ga.nl_items)

    def __str__(self):
        output_dict = {}
        for i in self.map_at:
            output_dict["MAP@" + str(i)] = self.map_at[i]
        return str(output_dict)

def number_to_vertical_box_drawing_bar(number):
    if number <= 0:
        return ' '
    if number <= 0.125:
        return '▁'
    if number <= 0.25:
        return '▂'
    if number <= 0.375:
        return '▃'
    if number <= 0.5:
        return '▄'
    if number <= 0.625:
        return '▅'
    if number <= 0.75:
        return '▆'
    if number <= 0.875:
        return '▇'
    else:
        return '█'

def number_to_horizontal_box_drawing_bar(number):
    if number <= 0:
        return ' '
    if number <= 0.125:
        return '▏'
    if number <= 0.25:
        return '▎'
    if number <= 0.375:
        return '▍'
    if number <= 0.5:
        return '▌'
    if number <= 0.625:
        return '▋'
    if number <= 0.75:
        return '▊'
    if number <= 0.875:
        return '▉'
    else:
        return '█'

CODFREL_EVAL_DIR = "codfrel_eval"
def codfrel_eval(name: str,
                 jsonl_file_path: str,
                 dataset_type: str,
                 max_links_count: int|None,
                 stopping_condition,
                 population_number_per_NL: int = 1000,
                 number_of_parents: int = 7,
                 number_of_children: int = 21,
                 max_nl_count: int|None = None,
                 max_pl_count: int|None = None):
    if max_links_count != None and max_links_count <= 0:
        max_links_count = None
    if max_nl_count != None and max_nl_count <= 0:
        max_nl_count = None
    if max_pl_count != None and max_pl_count <= 0:
        max_pl_count = None
    # Checks
    if not os.path.isfile(jsonl_file_path):
        print("No such file: " + jsonl_file_path)
        return
    if dataset_type not in codfrel_row_transform_functions.nl_transforms:
        print("No dataset type found: " + dataset_type)
        print("Defined dataset types: " + ', '.join([key for key in codfrel_row_transform_functions.nl_transforms]))
        return
    if not os.path.exists(CODFREL_EVAL_DIR):
        os.mkdir(CODFREL_EVAL_DIR)
    elif not os.path.isdir(CODFREL_EVAL_DIR):
        print(CODFREL_EVAL_DIR + " exists, but is not a directory.")
        return
    results_dir = os.path.join(CODFREL_EVAL_DIR, name)
    if not os.path.exists(results_dir):
        os.mkdir(results_dir)
    elif not os.path.isdir(results_dir):
        print(results_dir + " exists, but is not a directory.")
        return
    # Params info
    print("Name: " + name)
    print("Dataset file: " + jsonl_file_path)
    print("Dataset type: " + dataset_type)
    print("Links count limit: " + str(max_links_count))
    print("NL count limit: " + str(max_nl_count))
    print("PL count limit: " + str(max_pl_count))
    print("GA population per NL item: " + str(population_number_per_NL))
    print("Number of parents per iteration: " + str(number_of_parents))
    print("Number of children per iteration: " + str(number_of_children))
    # Transform funcs
    nl_transform = codfrel_row_transform_functions.nl_transforms[dataset_type]
    pl_transform = codfrel_row_transform_functions.pl_transforms[dataset_type]
    # Load
    t = [ 0 ]
    times = {}
    def start_time():
        t[0] = time.time()
    def report_time(name):
        duration = time.time() - t[0]
        times[name] = duration
        print(name + ": " + str(round(duration, 2)) + "s")
    print("Loading dataset...")
    start_time()
    dataset = Dataset(
        jsonl_file_path=jsonl_file_path,
        nl_transform_func=nl_transform,
        pl_transform_func=pl_transform,
        max_link_count=max_links_count,
        max_nl_count=max_nl_count,
        max_pl_count=max_pl_count
    )
    report_time("Loading dataset")
    print("NL count: " + str(len(dataset.nl_items)))
    print("PL count: " + str(len(dataset.pl_items)))
    print("Links count: " + str(dataset.links_count))
    # GA
    print("Initializing GA...")
    start_time()
    ga = CodfrelGeneticAlgorithm(
        dataset.nl_items,
        dataset.pl_items,
        population_number_per_NL,
        number_of_parents=number_of_parents,
        number_of_children=number_of_children
    )
    report_time("Initializing GA")
    print("Running GA...")
    start_time()
    ga.run(stopping_condition)
    print()
    report_time("Running GA")
    # Eval
    print("Evaluating...")
    start_time()
    map_metrics_from_population = EvalMAPMetricsFromPopulation(ga, dataset)
    report_time("Calculating MAP directly from population")
    print("MAP calculated directly from population:")
    print(map_metrics_from_population)
    start_time()
    config_to_metrics: dict[str, EvalMetrics] = {}
    config_str_to_numbers: dict[str, tuple[float, float]] = {}
    MINIMUM_MIN_FITNESS = 0.5
    MIN_FITNESS_STEPS = 500
    MIN_LINES_RATIO_STEPS = 20
    for min_fitness_i in range(MIN_FITNESS_STEPS):
        print(".", end="", flush=True)
        min_fitness = 0.5 + (min_fitness_i / MIN_FITNESS_STEPS) * (1 - MINIMUM_MIN_FITNESS) # [MINIMUM_MIN_FITNESS, 1)
        #                          dict[nl,  dict[pl,  tuple[set[lines], total_lines_count]]]
        ga_nl_to_pl_to_lines_info: dict[int, dict[int, tuple[set[int], set[float], int]]] = {}
        for nl_i in range(len(dataset.nl_items)):
            ga_nl_to_pl_to_lines_info[nl_i] = {}
            for item in ga.populations[ga.nl_items[nl_i]]:
                for line in item.pl_lines:
                    if line.pl_index not in ga_nl_to_pl_to_lines_info[nl_i]:
                        ga_nl_to_pl_to_lines_info[nl_i][line.pl_index] = (set(), set(), line.pl_item_total_lines)
                    if item.fitness_score > min_fitness:
                        ga_nl_to_pl_to_lines_info[nl_i][line.pl_index][0].add(line.line_index)
                    ga_nl_to_pl_to_lines_info[nl_i][line.pl_index][1].add(item.fitness_score)
        for min_lines_ratio_i in range(MIN_LINES_RATIO_STEPS):
            min_lines_ratio = min_lines_ratio_i / MIN_LINES_RATIO_STEPS # [0, 1)
            rows: list[tuple[int, int, bool, bool, float, int, int]] = []
            for nl_i in range(len(dataset.nl_items)):
                for pl_i in range(len(dataset.pl_items)):
                    if pl_i in ga_nl_to_pl_to_lines_info[nl_i]:
                        pred_lines = len(ga_nl_to_pl_to_lines_info[nl_i][pl_i][0])
                        total_lines = ga_nl_to_pl_to_lines_info[nl_i][pl_i][2]
                        pred = pred_lines / total_lines > min_lines_ratio
                        pred_value = max(ga_nl_to_pl_to_lines_info[nl_i][pl_i][1])
                    else:
                        pred_lines = 0
                        total_lines = 0
                        pred = False
                        pred_value = 0.0
                    rows.append((
                        nl_i,
                        pl_i,
                        dataset.are_linked(nl_i, pl_i),
                        pred,
                        pred_value,
                        pred_lines,
                        total_lines
                    ))
            config = "min_fitness=" + str(min_fitness) + ",min_lines_ratio=" + str(min_lines_ratio)
            config_to_metrics[config] = EvalMetrics(rows)
            config_str_to_numbers[config] = (min_fitness, min_lines_ratio)
    print()
    report_time("Evaluating different configs")
    max_f1 = -1
    max_f1_config = None
    max_f1_metrics = None
    max_f1_zero_min_lines_ratio = -1
    max_f1_zero_min_lines_ratio_config = None
    max_f1_zero_min_lines_ratio_metrics = None
    for config in config_to_metrics:
        if config_to_metrics[config].f1 != None and config_to_metrics[config].f1 > max_f1:
            max_f1 = config_to_metrics[config].f1
            max_f1_config = config
            max_f1_metrics = config_to_metrics[config]
        if config_str_to_numbers[config][1] == 0:
            if config_to_metrics[config].f1 != None and config_to_metrics[config].f1 > max_f1_zero_min_lines_ratio:
                max_f1_zero_min_lines_ratio = config_to_metrics[config].f1
                max_f1_zero_min_lines_ratio_config = config
                max_f1_zero_min_lines_ratio_metrics = config_to_metrics[config]
    #print("Metrics with min requrements:")
    #print(config_to_metrics["min_fitness=0.5,min_lines_ratio=0.0"])
    #print()
    print("Config with best F1:")
    print(max_f1_config)
    print("Metrics with best F1:")
    print(max_f1_metrics)
    #print()
    #print("Config with best F1 and 0 min lines ratio:")
    #print(max_f1_zero_min_lines_ratio_config)
    #print("Metrics with best F1 and 0 min lines ratio:")
    #print(max_f1_zero_min_lines_ratio_metrics)
    print("Writing results...")
    min_conf = "min_fitness=" + str(MINIMUM_MIN_FITNESS) + ",min_lines_ratio=" + str(0 / MIN_LINES_RATIO_STEPS)
    with open(os.path.join(results_dir, "best_f1_rows.csv"), "w+", encoding="utf-8") as file:
        file.write(max_f1_metrics.get_rows_csv())
    with open(os.path.join(results_dir, "best_f1_0_min_lines_ratio_rows.csv"), "w+", encoding="utf-8") as file:
        file.write(max_f1_zero_min_lines_ratio_metrics.get_rows_csv())
    with open(os.path.join(results_dir, "minimum_requirements_rows.csv"), "w+", encoding="utf-8") as file:
        file.write(config_to_metrics[min_conf].get_rows_csv())
    with open(os.path.join(results_dir, "summary.txt"), "w+", encoding="utf-8") as file:
        text = ""
        if ga.interrupted_via_keyboard_interrupt:
            text += "ATTENTION: GA run was interrupted via keyboard interrupt." + '\n'
            text += '\n'
        text += "MAP calculated directly from population:\n" + str(map_metrics_from_population) + '\n'
        text += '\n'
        text += "Config with best F1:\n" + max_f1_config + '\n'
        text += "Metrics with best F1:\n" + str(max_f1_metrics) + '\n'
        text += '\n'
        text += "Config with best F1 and 0 min lines ratio:\n" + max_f1_zero_min_lines_ratio_config + '\n'
        text += "Metrics with best F1 and 0 min lines ratio:\n" + str(max_f1_zero_min_lines_ratio_metrics) + '\n'
        text += '\n'
        text += "Config with minimum requirements:\n" + min_conf + '\n'
        text += "Metrics with minimum requirements:\n" + str(config_to_metrics[min_conf]) + '\n'
        text += '\n'
        text += "Execution times:\n" + str(times) + '\n'
        text += '\n'
        text += "Global iterations:\n" + str(ga.global_iteration_number) + '\n'
        text += "Iterations[nl]:\n{" + ', '.join([str(nl.nl_index) + ": " + str(ga.iteration_numbers[nl]) for nl in ga.iteration_numbers]) + "}" + '\n'
        text += '\n'
        text += "NOTE:" + '\n'
        text += "'MAP calculated directly from population' is the best calculation of MAP." + '\n'
        text += "The other MAP calculations are for testing." + '\n'
        text += "In those calculations, the inclusion of a row in the population is guessed by pred != 0.0" + '\n'
        text += "instead of directly looking up the population." + '\n'
        file.write(text)

def stopping_condition_time_per_NL(ga: CodfrelGeneticAlgorithm, nl_item: NLItemInfo, execution_time_per_NL: float = 1200):
    if nl_item == ga.nl_items[0]:
        if ga.global_iteration_number == 0: # Init
            ga.stopping_condition_start_time = time.time()
        ga.stopping_condition_t = (time.time() - ga.stopping_condition_start_time) / (execution_time_per_NL * len(ga.nl_items))
        if ga.stopping_condition_t <= 1:
            print(number_to_vertical_box_drawing_bar(ga.stopping_condition_t), end="", flush=True)
    return ga.stopping_condition_t > 1

def stopping_condition_iterations(ga: CodfrelGeneticAlgorithm, nl_item: NLItemInfo, iterations: int = 1000):
    if nl_item == ga.nl_items[0]:
        if ga.global_iteration_number <= iterations:
            print(number_to_vertical_box_drawing_bar(ga.global_iteration_number / iterations), end="", flush=True)
    return ga.global_iteration_number > iterations

def stopping_condition_patience_after_top_items_change(
            ga: CodfrelGeneticAlgorithm,
            nl_item: NLItemInfo,
            patience_iterations: int = 100,
            top_items_count: int = 1,
            top_items_allowed_shift: int = 10 # The number of positions the top items are allowed to get lower (ONLY if swapped with the lower items)
            # Sometimes position swaps happen using LSI method, so this is useful.
        ):
    # Test
    #print(nl.nl_index, end=": ")
    #print([(' '.join([str(line.global_pl_line_index) for line in item.pl_lines]), item.fitness_score) for item in ga.populations[nl]][:5])
    if ga.global_iteration_number == 0 and nl_item == ga.nl_items[0]: # Init
        ga.stopping_condition_last_best_items = {}
        ga.stopping_condition_last_best_item_iterations = {}
        for nl in ga.nl_items:
            ga.stopping_condition_last_best_items[nl] = [
                "" for i in range(
                    min(
                        top_items_count + top_items_allowed_shift,
                        len(ga.populations[nl])
                    )
                )
            ]
            ga.stopping_condition_last_best_item_iterations[nl] = 0
        ga.stopping_condition_changed_counter = 0
        ga.stopping_condition_stop_counter = 0
    relative_patience_result = False
    def pl_lines_to_str(pl_lines: list[PLLineInfo]):
        return ' '.join([str(line.global_pl_line_index) for line in pl_lines])
    current_best_items = [
        pl_lines_to_str(ga.populations[nl_item][i].pl_lines) for i in range(
            min(
                top_items_count + top_items_allowed_shift,
                len(ga.populations[nl_item])
            )
        )
    ]
    changed = not (
        # The last top items are in the current top top_items_count+top_items_allowed_shift items
        set(ga.stopping_condition_last_best_items[nl_item][:top_items_count]).issubset(set(current_best_items))
        and
        # The current top items are in the last top top_items_count+top_items_allowed_shift items
        set(current_best_items[:top_items_count]).issubset(set(ga.stopping_condition_last_best_items[nl_item]))
    )
    # Test
    #if not changed and set(current_best_items[:top_items_count]) != set(ga.stopping_condition_last_best_items[nl][:top_items_count]):
    #    print("X", end="", flush=True)
    if changed:
        ga.stopping_condition_last_best_items[nl_item] = current_best_items
        ga.stopping_condition_last_best_item_iterations[nl_item] = ga.iteration_numbers[nl_item]
        ga.stopping_condition_changed_counter += 1
        # Test
        #print(nl.nl_index, end=": ")
        #print([(' '.join([str(line.global_pl_line_index) for line in item.pl_lines]), item.fitness_score) for item in ga.populations[nl]][:5])
    elif ga.iteration_numbers[nl_item] - ga.stopping_condition_last_best_item_iterations[nl_item] > patience_iterations:
        ga.stopping_condition_stop_counter += 1
        relative_patience_result = True
    if nl_item == ga.nl_items[-1]:
        print(number_to_vertical_box_drawing_bar(ga.stopping_condition_changed_counter / len(ga.nl_items)), end="", flush=True)
        print(number_to_horizontal_box_drawing_bar(1 - ga.stopping_condition_stop_counter / len(ga.nl_items)), end="", flush=True)
        if ga.global_iteration_number % 40 == 39:
            print()
        ga.stopping_condition_changed_counter = 0
        ga.stopping_condition_stop_counter = 0
    return relative_patience_result

stopping_condition_patience_after_top_item_change = lambda ga, nl, p: stopping_condition_patience_after_top_items_change(ga, nl, p, 1)
stopping_condition_patience_after_top_2items_change = lambda ga, nl, p: stopping_condition_patience_after_top_items_change(ga, nl, p, 2)
stopping_condition_patience_after_top_3items_change = lambda ga, nl, p: stopping_condition_patience_after_top_items_change(ga, nl, p, 3)
stopping_condition_patience_after_top_4items_change = lambda ga, nl, p: stopping_condition_patience_after_top_items_change(ga, nl, p, 4)
stopping_condition_patience_after_top_5items_change = lambda ga, nl, p: stopping_condition_patience_after_top_items_change(ga, nl, p, 5)

stopping_conditions = {
    "time-per-nl": stopping_condition_time_per_NL,
    "iterations": stopping_condition_iterations,
    "patience-after-top-item-change": stopping_condition_patience_after_top_item_change,
    "patience-after-top-2-items-change": stopping_condition_patience_after_top_2items_change,
    "patience-after-top-3-item-change": stopping_condition_patience_after_top_3items_change,
    "patience-after-top-4-items-change": stopping_condition_patience_after_top_4items_change,
    "patience-after-top-5-items-change": stopping_condition_patience_after_top_5items_change,
}

stopping_conditions_params = {
    "time-per-nl": "time in seconds",
    "iterations": "number of iterations",
    "patience-after-top-item-change": "number of iterations",
    "patience-after-top-2-items-change": "number of iterations",
    "patience-after-top-3-item-change": "number of iterations",
    "patience-after-top-4-items-change": "number of iterations",
    "patience-after-top-5-items-change": "number of iterations",
}

def get_stopping_condition(stopping_condition_type: str, stopping_condition_parameter: str):
    if stopping_condition_type in stopping_conditions:
        return lambda ga, nl: stopping_conditions[stopping_condition_type](ga, nl, float(stopping_condition_parameter))
    else:
        return None

if __name__ == "__main__":
    if len(sys.argv) >= 7 and len(sys.argv) <= 9:
        stopping_condition = get_stopping_condition(sys.argv[5], sys.argv[6])
        if stopping_condition == None:
            print("No stopping condition type found: " + sys.argv[5])
            print("Defined stopping condition types and their params: " + str(stopping_conditions_params))
            exit()
        print("Stopping condition: " + sys.argv[5] + "(" + sys.argv[6] + ")")
    if len(sys.argv) == 7:
        codfrel_eval(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), stopping_condition)
    elif len(sys.argv) == 8:
        codfrel_eval(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), stopping_condition, int(sys.argv[7]))
    elif len(sys.argv) == 9:
        codfrel_eval(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), stopping_condition, int(sys.argv[7]), int(sys.argv[8]))
    elif len(sys.argv) == 10:
        codfrel_eval(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), stopping_condition, int(sys.argv[7]), int(sys.argv[8]), int(sys.argv[9]))
    else:
        print(
            "Params: <name> <jsonl-dataset-file-path> <dataset-type> <max-number-of-links>"
            + " <stopping-condition-type> <stopping-condition-parameter>"
            + " [<GA-population-per-NL-item>"
            + " [<number-of-parents-per-iteration> [<number-of-children-per-iteration>]]]"
        )
        print("Dataset types: " + ', '.join([key for key in codfrel_row_transform_functions.nl_transforms]))
        print("Stopping condition types and their params: " + str(stopping_conditions_params))
