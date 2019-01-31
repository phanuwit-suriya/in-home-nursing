from collections import defaultdict
from random import shuffle

import nltk
from nltk.corpus import brown, names


class Classifier():
    @staticmethod
    def gender_features(word):
        if not word:
            return {'last_letter': 'a'}
        else:
            return {'last_letter': word[-1]}

    @staticmethod
    def gender(word):
        labeled_names = ([(name, 'male') for name in names.words('male.txt')] + [(name, 'female') for name in names.words('female.txt')])
        shuffle(labeled_names)
        featuresets = [(Classifier.gender_features(n), gender) for (n, gender) in labeled_names]
        train_set = featuresets[500:]
        classifier = nltk.NaiveBayesClassifier.train(train_set)
        return classifier.classify(Classifier.gender_features(word))


class TopicExtractor(object):
    def __init__(self):
        brown_train = brown.tagged_sents(categories='news')
        regexp_tagger = nltk.RegexpTagger([
            (r'^-?[0-9]+(.[0-9]+)?$', 'CD'),
            (r'(-|:|;)$', ':'),
            (r'\'*$', 'MD'),
            (r'(The|the|A|a|An|an)$', 'AT'),
            (r'.*able$', 'JJ'),
            (r'^[A-Z].*$', 'NNP'),
            (r'.*ness$', 'NN'),
            (r'.*ly$', 'RB'),
            (r'.*s$', 'NNS'),
            (r'.*ing$', 'VBG'),
            (r'.*ed$', 'VBD'),
            (r'.*', 'NN')
        ])
        unigram_tagger = nltk.UnigramTagger(brown_train, backoff=regexp_tagger)
        self.bigram_tagger = nltk.BigramTagger(brown_train, backoff=unigram_tagger)

        self.cfg = {}
        self.cfg['NNP+NNP'] = 'NNP'
        self.cfg['NN+NN'] = 'NNI'
        self.cfg['NNI+NN'] = 'NNI'
        self.cfg['JJ+JJ'] = 'JJ'
        self.cfg['JJ+NN'] = 'NNI'

    def tokenize_sentence(self, sentence):
        tokens = nltk.word_tokenize(sentence)
        return tokens

    def normalize_tags(self, tagged):
        n_tagged = []
        for t in tagged:
            if t[1] in ('NP-TL', 'NP'):
                n_tagged.append((t[0], 'NNP'))
                continue
            if t[1].endswith('-TL'):
                n_tagged.append((t[0], t[1][:-3]))
                continue
            if t[1].endswith('S'):
                n_tagged.append(([0], t[1][:-1]))
                continue
            if t[1].endswith('S'):
                n_tagged.append((t[0], t[1][:-1]))
                continue
            n_tagged.append((t[0], t[1]))
        return n_tagged

    def extract(self, sentence):
        tokens = self.tokenize_sentence(sentence)
        tags = self.normalize_tags(self.bigram_tagger.tag(tokens))
        merge = True
        while merge:
            merge = False
            for x in range(0, len(tags) - 1):
                t1 = tags[x]
                t2 = tags[x + 1]
                key = '%s+%s' % (t1[1], t2[1])
                value = self.cfg.get(key, '')
                if value:
                    merge = True
                    tags.pop(x)
                    tags.pop(x)
                    match = '%s-%s' % (t1[0], t2[0])
                    pos = value
                    tags.insert(x, (match, pos))
                    break
        
        matches = []
        for t in tags:
            if t[1] == 'NNP' or t[1] == 'NNI':
                matches.append(t[0])
        return matches


class Helper():
    def __init__(self, doc):
        self.doc = doc

    def directly_equal(self, words):
        """
        Method to check if user's input is directly equal to one of these word.
        """
        for word in words:
            if self.doc[0].lemma_ == word.lower() and len(self.doc) == 1:
                return True
        return False

    def check_nth_lemma(self, n, word):
        """
        Method to check if nth lemma is equal to given word.
        """
        try:
            return self.doc[n].lemma_ == word
        except IndexError:
            return False
    
    def check_verb_lemma(self, verb):
        """
        Method to check if there is a verb with given lemma.
        """
        for token in self.doc:
            if token.pos_ == "VERB" and token.lemma_ == verb:
                return True
        return False

    def check_wh_lemma(self, wh):
        """
        Method to check if there is a WH- word with given lemma.
        """
        for token in self.doc:
            if token.tag_ in ['WDT', 'WP', 'WP$', 'WRB'] and token.lemma_ == wh:
                return True
        return False

    def check_deps_contain(self, phrase):
        """
        Method to check if the user's input/command contains this phrase.
        """
        for chunk in self.doc.noun_chunks:
            if chunk.text.lower() == phrase.lower():
                return True
        return False

    def check_only_deps_is(self, phrase):
        """
        Method to check if this is the only phrase user's input/command has.
        """
        return sum(1 for _ in self.doc.noun_chunks) == 1 and self.doc.noun_chunks.__next__().text.lower() == phrase.lower()

    def check_noun_lemma(self, noun):
        """
        Method to checl if there is a verb noun given lemma
        """
        for token in self.doc:
            if (token.pos_ == 'NOUN' or token.pos_ == 'PROPN') and token.lemma_ == noun:
                return True
        return False

    def check_adj_lemma(self, adj):
        """
        Method to checl if there is an adjective with given lemma.
        """
        for token in self.doc:
            if token.pos_ == 'ADJ' and token.lemma_ == adj:
                return True
        return False

    def check_adv_lemma(self, adv):
        """
        Method to check if there is an adverb with given lemma.
        """
        for token in self.doc:
            if token.pos_ == 'ADV' and token.lemma_ == adv:
                return True
        return False

    def check_lemma(self, lemma):
        """
        Method to check if there is a word with given lemma.
        """
        for token in self.doc:
            if token.lemma_ == lemma:
                return True
        return False

    def check_text(self, text):
        """
        Method to check if the user's input/command is directly equal to given text.
        """
        for token in self.doc:
            if token.text.upper() == text.upper():
                return True
        return False

    def is_wh_question(self):
        """
        Method to check if the user's input/command a WH question.
        """
        for token in self.doc:
            if token.is_stop:
                break
            if token.tag_ in ['WDT', 'WP', 'WP$', 'WRB']:
                return True
        return False

    def max_word_count(self, n):
        """
        Method to check if the word length of the user's input/command is less than or equal to given value.
        """
        return len(self.doc) <= n
    
    def find_word_index(self, word):
        """
        Method to find index of the given word
        """
        try:
            return self.doc.index(word)
        except ValueError:
            return False

    def get_time(self):
        """
        Method to get the time in the user's input/command
        """
        prev_token = None
        time_dict = {'hour': 0, 'minute': 0, 'second': 0}
        for token in self.doc:
            if token.lemma_ in ['second', 'minute', 'hour'] and token.tag_ in ['JJ', 'NN', 'NNS']:
                if prev_token.is_digit:
                    time_dict[token.lemma_] = int(prev_token.text)
            prev_token = token
        return time_dict
