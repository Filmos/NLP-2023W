import numpy as np
from gensim.models import KeyedVectors
import json
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from tqdm import tqdm

def process_sentences(args):
    with open(f'datasets/{args.dataset}/{args.text_file}') as fin, \
         open(f'datasets/{args.dataset}/sentences.json', 'w') as fout:
        for idx, line in enumerate(fin):
            out = {'doc_id':idx}
            ss = []
            data = line.strip().replace('!', '.').replace('?', '.')
            sents = data.split(' .')
            for sent in sents:
                s = sent.strip()
                if len(s) >= 5:
                    ss.append(s)
            out['sentences'] = ss
            fout.write(json.dumps(out)+'\n')

def load_cate_emb(file):
    word2emb = {}
    with open(file) as fin:
        for idx, line in enumerate(fin):
            if idx == 0:
                continue
            data = line.strip().split()
            word = data[0]
            emb = np.array([float(x) for x in data[1:]])
            emb = emb / np.linalg.norm(emb)
            word2emb[word] = emb
    return word2emb

def load_bert_emb(file):
    word2bert_raw = KeyedVectors.load(file)
    word2bert = {}
    for word in word2bert_raw.index_to_key:
        emb = word2bert_raw[word]
        emb = emb / np.linalg.norm(emb)
        word2bert[word] = emb
    return word2bert

def pmi(topic_words, word_frequency, word_frequency_in_documents, n_docs, normalise=False):
    """PMI/NPMI topic quality metric for a topic.

    Calculates the PMI/NPMI topic quality metric for one individual topic based on the topic words.

    Args:
        topic_words: list
            Words that compose one individual topic.
        word_frequency: dict
            Frequency of each word in corpus.
        word_frequency_in_documents: dict
            Frequency of each word for each document in corpus.
        n_docs: int
            Number of documents in the corpus.
        normalise: bool, default=False
            Where to normalise (NPMI) or not (PMI).

    Returns:
        pmi: float
            Resultant PMI metric value for the topic.
        npmi: float
            Resultant NPMI metric value for the topic.
    """
    n_top = len(topic_words)
    pmi = 0.0
    npmi = 0.0

    for j in range(1, n_top):
        for i in range(0, j):
            ti = topic_words[i]
            if '/' in ti:
                ti = ti[:ti.find('/')]
            tj = topic_words[j]
            if '/' in tj:
                tj = tj[:tj.find('/')]
            if '-' in ti:
                subwords = ti.split('-')
                freqs = 0.0
                doc_sets = []
                for sw in subwords:
                    freqs += word_frequency[sw]
                    doc_sets.append(word_frequency_in_documents[sw])
                c_i = freqs / len(subwords)
                wfid_i = set.intersection(*doc_sets)
            else:
                c_i = word_frequency[ti] 
                wfid_i = word_frequency_in_documents[ti]
            if '-' in tj:
                subwords = tj.split('-')
                freqs = 0.0
                doc_sets = []
                for sw in subwords:
                    freqs += word_frequency[sw]
                    doc_sets.append(word_frequency_in_documents[sw])
                c_j = freqs / len(subwords)
                wfid_j = set.intersection(*doc_sets)
            else:
                c_j = word_frequency[tj]
                wfid_j = word_frequency_in_documents[tj] 

            
            c_i_and_j = len(wfid_i.intersection(wfid_j))

            dividend = (c_i_and_j + 1.0) / float(n_docs)
            divisor = ((c_i * c_j) / float(n_docs) ** 2)
            pmi += np.log(dividend / divisor)

            npmi += -1.0 * np.log((c_i_and_j + 0.01) / float(n_docs))

    npmi = pmi / npmi

    if normalise:
        return npmi
    else:
        return pmi
    
def get_vocabulary(documents):
    """Generates the corpus vocabulary.

    Generates the corpus vocabulary from the CountVectorizer of Scikit-Learn.

    Args:
        documents: list
            List where each element is a entire document.

    Returns:
        vocabulary: list
            List of words present in the corpus.
    """
    cv_model = CountVectorizer(binary=True)
    cv_model.fit(documents)

    vocabulary = cv_model.get_feature_names_out()
    vocabulary = list(map(str, vocabulary))

    return vocabulary


def get_word_frequencies(documents):
    """Word frequencies in documents.

    Count frequency of words and frequency of words in documents.

    Args:
        documents: list
            List where each element is a entire document.

    Returns:
        word_frequency: dict
            Frequency of each word in corpus.
        word_frequency_in_documens: dict
            Frequency of each word for each document in corpus.
    """
    cv_model = CountVectorizer(binary=True)
    tf_matrix = cv_model.fit_transform(documents)
    tf_matrix_transpose = tf_matrix.transpose()

    vocabulary = get_vocabulary(documents)
    n_words = len(vocabulary)

    word_frequency = {}
    word_frequency_in_documents = {}

    for word_idx in tqdm(range(n_words)):
        word = vocabulary[word_idx]
        tf_word = tf_matrix_transpose[word_idx]

        # getnnz -> Get the count of explicitly-stored values (nonzeros)
        word_frequency[word] = float(tf_word.getnnz(1))
        # nonzero -> Return the indices of the elements that are non-zero
        word_frequency_in_documents[word] = set(tf_word.nonzero()[1])

    return word_frequency, word_frequency_in_documents