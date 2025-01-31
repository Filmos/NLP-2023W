import os
import argparse
from cate import process_cate
from caseolap import caseolap
from rank_ensemble import rank_ensemble
from documents import rank_documents
from evaluate import evaluate_npmi, evaluate_doc_ids
from utils import *
from tqdm import tqdm

parser = argparse.ArgumentParser(description='newslinking', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--dataset', default='nyt', type=str, help='name of dataset folder')
parser.add_argument('--text_file', default='corpus_train.txt', type=str, help='training corpus')
parser.add_argument('--topic', default='topics', type=str, help='name of topics')
parser.add_argument('--pretrain_emb', default='word_embs.txt', type=str, help='pretrained word2vec embeddings for CatE')
parser.add_argument('--num_iter', default=4, type=int, help='number of iterations')
parser.add_argument('--num_sent', default=500, type=int, help='maximum number of retrieved sentences')
parser.add_argument('--sent_window', default=4, type=int, help='window size for retrieving context sentences')
parser.add_argument('--alpha', default=0.2, type=float, help='weight for calculating topic-indicative context scores')
parser.add_argument('--rank_ens', default=0.3, type=float, help='threshold for rank ensemble')
args = parser.parse_args()

assert os.system(f"cp datasets/{args.dataset}/topics/{args.topic}/{args.topic}.txt \
                    datasets/{args.dataset}/topics/{args.topic}/{args.topic}_seeds.txt") == 0

for iteration in tqdm(range(args.num_iter),total=args.num_iter):

    print(f'start iteration {iteration+1}')

    # execuate cate c command
    cate_c = f"""./cate/cate -train ./datasets/{args.dataset}/{args.text_file} \
                -topic-name ./datasets/{args.dataset}/topics/{args.topic}/{args.topic}_seeds.txt \
                -load-emb {args.pretrain_emb} \
                -res ./datasets/{args.dataset}/topics/{args.topic}/res_{args.topic}.txt -k 10 -expand 1 \
                -word-emb ./datasets/{args.dataset}/topics/{args.topic}/emb_{args.topic}_w.txt \
                -topic-emb ./datasets/{args.dataset}/topics/{args.topic}/emb_{args.topic}_t.txt \
                -size 100 -window 5 -negative 5 -sample 1e-3 -min-count 3 \
                -threads 20 -binary 0 -iter 10 -pretrain 2"""
    # seed-guided text embeddings
    assert os.system(cate_c) == 0, "cate c command execute failed"
    # initial term ranking
    print('initial term ranking')
    # Seed-guided embeddings + PLM Representations
    process_cate(args)

    if iteration == args.num_iter - 1:
        assert os.system(f"cp datasets/{args.dataset}/topics/{args.topic}/intermediate_1.txt \
                            datasets/{args.dataset}/topics/{args.topic}/{args.topic}_results.txt") == 0
        break

    # second term ranking
    print('Second term ranking')
    # topic-indicative sentences
    caseolap(args)
    
    # rank ensemble
    print('Rank ensemble')
    # re-rank all types of context
    rank_ensemble(args)

    # convert collected scores and ids into predictions
    doc_num = 10 # ????
    rank_documents(args, doc_num)
    print("Predictions saved")    

print("Iterations finished!")

# convert collected scores and ids into predictions
doc_num = 10 
rank_documents(args, doc_num)
print("Predictions saved!\nFinished!")    

evaluate_doc_ids(args)
print("Evaluation of documents predictions performed!")
evaluate_npmi(args)
print("NPMI evaluation performed!")

cleanup(args)