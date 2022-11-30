TRACE_BERT_CODE_DIR = "TraceBERT-master"

import logging
import os
import sys

#sys.path.append("../..")
sys.path.append(TRACE_BERT_CODE_DIR)

import torch
from common.data_structures import Examples
from common.utils import save_check_point, format_batch_input_for_single_bert, \
    write_tensor_board, evaluate_classification, evalute_retrivial_for_single_bert

from code_search.twin.twin_train import get_train_args, init_train_env, load_examples, train

logger = logging.getLogger(__name__)


accuracies = []
stopping_condition_patience = 3
TRAIN_AC_LOST_AVG_MAX_COUNT = 80


def train_single_iteration(args, model, train_examples: Examples, valid_examples: Examples, optimizer,
                           scheduler, tb_writer, step_bar, skip_n_steps):
    global accuracies
    global stopping_condition_patience
    train_ac_sum = 0
    train_loss_sum = 0
    train_ac_loss_count = 0
    train_ac_avg = 0
    train_loss_avg = 0

    # another dirty trick to prevent stopping the training when resuming from another final_model
    args.max_steps = -1

    tr_loss, tr_ac = 0, 0
    batch_size = args.per_gpu_train_batch_size
    cache_file = "cached_single_random_neg_sample_epoch_{}.dat".format(args.epochs_trained)
    # save the examples for epoch
    if args.neg_sampling == "random":
        if args.overwrite or not os.path.isfile(cache_file):
            train_dataloader = train_examples.random_neg_sampling_dataloader(batch_size=batch_size)
            torch.save(train_dataloader, cache_file)
        else:
            train_dataloader = torch.load(cache_file)
    elif args.neg_sampling == "online":
        # we provide only positive cases and will create negative in the batch processing
        train_dataloader = train_examples.online_neg_sampling_dataloader(batch_size=int(batch_size / 2))
    else:
        raise Exception("{} neg_sampling is not recoginized...".format(args.neg_sampling))

    for step, batch in enumerate(train_dataloader):
        if skip_n_steps > 0:
            skip_n_steps -= 1
            continue
        if args.neg_sampling == "online":
            batch = train_examples.make_online_neg_sampling_batch(batch, model, args.hard_ratio)

        model.train()
        labels = batch[2].to(model.device)
        inputs = format_batch_input_for_single_bert(batch, train_examples, model)
        inputs['relation_label'] = labels
        outputs = model(**inputs)
        loss = outputs['loss']
        logit = outputs['logits']
        y_pred = logit.data.max(1)[1]
        #tr_ac += y_pred.eq(labels).long().sum().item()
        temp_tr_ac_addition = y_pred.eq(labels).long().sum().item()
        tr_ac += temp_tr_ac_addition

        if args.n_gpu > 1:
            loss = loss.mean()  # mean() to average on multi-gpu parallel (not distributed) training
        if args.gradient_accumulation_steps > 1:
            loss = loss / args.gradient_accumulation_steps

        if args.fp16:
            try:
                from apex import amp
                with amp.scale_loss(loss, optimizer) as scaled_loss:
                    scaled_loss.backward()
            except ImportError:
                raise ImportError("Please install apex from https://www.github.com/nvidia/apex to use fp16 training.")
        else:
            loss.backward()
        #tr_loss += loss.item()
        temp_tr_loss_addition = loss.item()
        tr_loss += temp_tr_loss_addition

        train_ac_sum += temp_tr_ac_addition
        train_loss_sum += temp_tr_loss_addition
        train_ac_loss_count += 1
        if train_ac_loss_count >= TRAIN_AC_LOST_AVG_MAX_COUNT:
            train_ac_avg = train_ac_sum / train_ac_loss_count / args.train_batch_size
            train_loss_avg = (train_loss_sum / train_ac_loss_count) * args.gradient_accumulation_steps
            #print("    tr_ac: " + str(train_ac_avg))
            #print("    tr_loss: " + str(train_loss_avg))

        if (step + 1) % args.gradient_accumulation_steps == 0:
            if args.fp16:
                torch.nn.utils.clip_grad_norm_(amp.master_params(optimizer), args.max_grad_norm)
            else:
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
            optimizer.step()
            scheduler.step()
            model.zero_grad()
            args.global_step += 1
            step_bar.update()

            if args.local_rank in [-1, 0] and args.logging_steps > 0 and args.global_step % args.logging_steps == 0:
                tb_data = {
                    'lr': scheduler.get_last_lr()[0],
                    'acc': tr_ac / args.logging_steps / (
                            args.train_batch_size * args.gradient_accumulation_steps),
                    'loss': tr_loss / args.logging_steps
                }
                write_tensor_board(tb_writer, tb_data, args.global_step)
                tr_loss = 0.0
                tr_ac = 0.0

            # Save model checkpoint
            if args.local_rank in [-1, 0] and args.save_steps > 0 and args.global_step % args.save_steps == 1 and args.global_step != 1:
                # step invoke checkpoint writing
                ckpt_output_dir = os.path.join(args.output_dir, "checkpoint-{}".format(args.global_step))
                save_check_point(model, ckpt_output_dir, args, optimizer, scheduler)

            if args.valid_step > 0 and args.global_step % args.valid_step == 1 and args.global_step != 1:
                # step invoke validation
                # valid_examples.update_embd(model)
                valid_accuracy, valid_loss = evaluate_classification(valid_examples, model,
                                                                     args.per_gpu_eval_batch_size,
                                                                     "evaluation/runtime_eval")
                pk, best_f1, map = evalute_retrivial_for_single_bert(model, valid_examples,
                                                                     args.per_gpu_eval_batch_size,
                                                                     "evaluation/runtime_eval")
                tb_data = {
                    "valid_accuracy": valid_accuracy,
                    "valid_loss": valid_loss,
                    "precision@3": pk,
                    "best_f1": best_f1,
                    "MAP": map
                }
                write_tensor_board(tb_writer, tb_data, args.global_step)
            args.steps_trained_in_current_epoch += 1
            if args.max_steps > 0 and args.global_step > args.max_steps:
                break

    # end of epoch
    print()
    print()
    print()
    print("End of epoch " + str(args.epochs_trained + 1))
    print()
    # validation
    valid_accuracy, valid_loss = evaluate_classification(valid_examples, model,
                                                            args.per_gpu_eval_batch_size,
                                                            "evaluation/runtime_eval_epoch_" + str(args.epochs_trained + 1))
    pk, best_f1, map = evalute_retrivial_for_single_bert(model, valid_examples,
                                                            args.per_gpu_eval_batch_size,
                                                            "evaluation/runtime_eval_epoch_" + str(args.epochs_trained + 1))
    tb_data = {
        "train_ac_avg": train_ac_avg,
        "train_loss_avg":train_loss_avg,
        "valid_accuracy": valid_accuracy,
        "valid_loss": valid_loss,
        "(valid) precision@3": pk,
        "(valid) best_f1": best_f1,
        "(valid) MAP (@3)": map
    }
    print("VALID-RESULTS:")
    print(tb_data)
    print()
    # checkpoint
    ckpt_output_dir = os.path.join(args.output_dir, "checkpoint-epoch-{}".format(args.epochs_trained + 1))
    save_check_point(model, ckpt_output_dir, args, optimizer, scheduler)
    # checkpoint valid info
    file = open(os.path.join(ckpt_output_dir, "valid-results.txt"), "w+")
    file.write(str(tb_data))
    file.close()
    # stopping condition
    if len(accuracies) != args.epochs_trained:
        print("[WARNING] THERE MIGHT BE A BUG! len(accuracies) != args.epochs_trained")
    accuracies.append(valid_accuracy)
    max_accuracy = -1
    max_accuracy_index = 0
    for i in range(len(accuracies)):
        if accuracies[i] > max_accuracy:
            max_accuracy = accuracies[i]
            max_accuracy_index = i
    print()
    print("Would stop after " + str(stopping_condition_patience) + " epochs without improvement.")
    if (len(accuracies)-1) - max_accuracy_index >= stopping_condition_patience:
        print("No improvement since " + str((len(accuracies)-1) - max_accuracy_index) + " epochs ago. Stopping...")
        # a dirty trick to stop the training
        args.max_steps = 1
    else:
        print("Max accuracy in " + str((len(accuracies)-1) - max_accuracy_index) + " epochs ago. Not stopping.")
    print()

def init_train_single_iteration(stopping_condition_patience_epochs = 3):
    global accuracies
    global stopping_condition_patience
    accuracies = []
    stopping_condition_patience = stopping_condition_patience_epochs


def main():
    args = get_train_args()
    model = init_train_env(args, tbert_type='single')
    valid_examples = load_examples(args.data_dir, data_type="valid", model=model, num_limit=args.valid_num,
                                   overwrite=args.overwrite)
    train_examples = load_examples(args.data_dir, data_type="train", model=model, num_limit=args.train_num,
                                   overwrite=args.overwrite)
    train(args, train_examples, valid_examples, model, train_single_iteration)
    logger.info("Training finished")


if __name__ == "__main__":
    main()
