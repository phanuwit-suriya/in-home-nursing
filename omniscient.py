import collections
from random import uniform

import requests.exceptions
import wikipedia
import wikipedia.exceptions
from nltk.corpus import wordnet as wn
from nltk.corpus.reader.wordnet import WordNetError

from utilities import nostderr


class Omniscient():
    def __init__(self, nlp):
        self.nlp = nlp
        self.entity_map = {
            'WHO': ['PERSON'],
            'WHAT': ['PERSON', 'NORP', 'FACILITY', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'LANGUAGE', 'DATE', 'TIME', 'PERCENT', 'MONEY', 'QUANTITY', 'ORDINAL', 'CARDINAL'],
            'WHEN': ['DATE', 'TIME', 'EVENT'],
            'WHERE': ['FACILITY', 'GPE', 'LOC']
        }
        self.coefficient = {'frequency': 0.36, 'precedence': 0.13, 'proximity': 0.21, 'mention': 0.30}

    def respond(self, com, tts_output=False, userin=None, user_prefix=None, is_server=False):
        """
        Method to response the user's input/command using factoid question answering ability.
        """
        result = None
        subject, subjects, focus, subject_with_objects = self.semantic_extractor(com)
        if not subject:
            return False
        
        doc = self.nlp(com)
        query = subject
        if query:
            if not tts_output and not is_server: print('Please wait....')
            if tts_output and not is_server: userin.say('Please wait....', True, False)
            wh_question = []
            for word in doc:
                if word.tag_ in ['WDT', 'WP', 'WP$', 'WRB']:
                    wh_question.append(word.text.upper())
            if not wh_question:
                return False
            with nostderr():
                try:
                    wikiresult = wikipedia.search(query)
                    if len(wikiresult) == 0:
                        result = 'Sorry, ' + user_prefix + '. But I couldn\'t find anythin about ' + query + ' in Wikipedia.'
                        if not tts_output and not is_server: print(result)
                        if tts_output and not is_server: userin.say(result)
                        print('OM1')
                        return result
                    wikipedia.page(wikiresult[0])
                except requests.exceptions.ConnectionError:
                    result = 'Sorry, ' + user_prefix + '. But I\'m unable to connect to Wikipedia servers.'
                    if not is_server:
                        userin.execute([' '], 'Wikipedia connection error.')
                        if not tts_output: print(result)
                        if tts_output: userin.say(result)
                    print('OM2')
                    return result
                except wikipedia.exceptions.DisambiguationError as disambiguation:
                    wikiresult = wikipedia.search(disambiguation.options[0])
                except:
                    result = 'Sorry, ' + user_prefix + '. But something went horribly wrong while I\'m searching Wikipedia.'
                    if not tts_output and not is_server: print(result)
                    if tts_output and not is_server: userin.say(result)
                    return result

            findings = []
            nth_page = 0
            while not findings:
                if not len(wikiresult) >= (nth_page + 1):
                    break
                with nostderr():
                    try:
                        wikipage = wikipedia.page(wikiresult[nth_page])
                    except requests.exceptions.ConnectionError:
                        result = 'Sorry, ' + user_prefix + '. But I\'m unable to connect to Wikipedia servers.'
                        if not is_server:
                            userin.execute([' '], 'Wikipedia connection error.')
                            if not tts_output: print(result)
                            if tts_output: userin.say(result)
                        return result
                    except:
                        result = 'Sorry, ' + user_prefix + '. But something went horribly wrong while I\'m searching Wikipedia.'
                        if not tts_output and not is_server: print(result)
                        if tts_output: userin.say(result)
                        return result
                    nth_page += 1
                    if nth_page > 5: break
                    wikidoc = self.nlp(wikipage.content)
                    sentences = [sent.string.strip() for sent in wikidoc.sents]
                    all_entities = []
                    mention = {}
                    subject_entities_by_wordnet = None
                    if 'WHAT' in wh_question:
                        subject_entities_by_wordnet = self.wordnet_entity_determiner(subject_with_objects, tts_output, is_server, userin, user_prefix)
                        if not subject_entities_by_wordnet:
                            return True
                    for sentence in reversed(sentences):
                        sentence = self.nlp(sentence)
                        for ent in sentence.ents:
                            all_entities.append(ent.text)
                            mention[ent.text] = 0.0
                            for wh in wh_question:
                                if wh.upper() in self.entity_map:
                                    target_entities = self.entity_map[wh.upper()]
                                    if wh.upper() == 'WHAT':
                                        target_entities = []
                                        for subject_entity_by_wordnet in subject_entities_by_wordnet:
                                            target_entities.append(subject_entity_by_wordnet)
                                    if ent.label_ in target_entities:
                                        findings.append(ent.text)
                                        if focus:
                                            if focus in sentence.text:
                                                mention[ent.text] += 1.0 * sentence.text.count(focus)
            
            if findings:
                frequency = collections.Counter(findings)
                max_freq = max(frequency.values())
                for key, value in frequency.items():
                    frequency[key] = float(value) / max_freq

                precedence = {}
                unique = list(set(findings))
                for i in range(len(unique)):
                    precedence[unique[i]] = float(len(unique) - i) / len(unique)

                proximity = {}
                subject_indices = []
                for i in range(len(all_entities)):
                    for subject in subjects:
                        for word in subject.split():
                            if word in all_entities[i]:
                                subject_indices.append(i)
                for i in range(len(all_entities)):
                    for index in subject_indices:
                        inverse_distance = float((len(all_entities) - 1) - abs(i - index)) / (len(all_entities) - 1)
                        if all_entities[i] in proximity:
                            proximity[all_entities[i]] = (proximity[all_entities[i]] + inverse_distance) / 2
                        else:
                            proximity[all_entities[i]] = inverse_distance
                    if all_entities[i] not in proximity:
                        proximity[all_entities[i]] = 0

                ranked = {}
                for key, value in frequency.items():
                    if key not in query:
                        ranked[key] = (value * self.coefficient['frequency'] + precedence[key] * self.coefficient['precedence'] + proximity[key] * self.coefficient['proximity'] + mention[key] * self.coefficient['mention'])

                result = sorted(ranked.items(), key=lambda x: x[1])[::-1][0][0]
                if not tts_output and not is_server: print(sorted(ranked.items(), key=lambda x: x[1])[::-1][:5])
                if tts_output and not is_server: userin.say(result, True, True)
                return result
            else:
                return False


    def wordnet_entity_determiner(self, subject, tts_output, is_server, userin=None, user_prefix=None):
        """
        Method to determine the named entity classification of the subject
        """
        entity_samples_map = {
            'PERSON': ['person', 'character', 'human', 'individual', 'name'],
            'NORP': ['nationality', 'religion', 'politics'],
            'FACILITY': ['building', 'airport', 'highway', 'bridge', 'port'],
            'ORG': ['company', 'agency', 'institution', 'university'],
            'GPE': ['country', 'city', 'state', 'address', 'capital'],
            'LOC': ['geography', 'mountain', 'ocean', 'river'],
            'PRODUCT': ['product', 'object', 'vehicle', 'food'],
            'EVENT': ['hurricane', 'battle', 'war', 'sport'],
            'WORK_OF_ART': ['art', 'book', 'song', 'painting'],
            'LANGUAGE': ['language', 'accent', 'dialect', 'speech'],
            'DATE': ['year', 'month', 'day'],
            'TIME': ['time', 'hour', 'minute'],
            'PERCENT': ['percent', 'rate', 'ratio', 'fee'],
            'MONEY': ['money', 'cash', 'salary', 'wealth'],
            'QUANTITY': ['measurement', 'amount', 'distance', 'height', 'population'],
            'ORDINAL': ['ordinal', 'first', 'second', 'third'],
            'CARDINAL': ['cardinal', 'number', 'amount', 'mathematics']}
        doc = self.nlp(subject)
        subject = []
        for word in doc:
            if word.pos_ == 'NOUN':
                subject.append(word.text.lower())
        entity_scores = {}
        for entity, samples in entity_samples_map.items():
            entity_scores[entity] = 0
            for sample in samples:
                sample_wn = wn.synset(sample + '.n.01')
                for word in subject:
                    try:
                        word_wn = wn.synset(word + '.n.01')
                        entity_scores[entity] += word_wn.path_similarity(sample_wn)
                    except WordNetError:
                        # userin.execute([' '], 'NLP(WordNet) error. Unrecognized word: ' + word)
                        userin.say(f"Sorry, {user_prefix}. But I'm unable to understand the word {word}.")
                        return False
            entity_scores[entity] = entity_scores[entity] / len(samples)
        if not tts_output and not is_server: print(sorted(entity_scores.items(), key=lambda x: x[1])[::-1][:3])
        result = sorted(entity_scores.items(), key=lambda x: x[1])[::-1][0][0]
        if result == 'FACILITY': return [result, 'ORG']
        if result == 'PRODUCT': return [result, 'ORG']
        return [result]
    
    def randomize_coefficient(self):
        """
        Method to randomize the coefficients for the purpose of optimizing their values
        """
        coeff1 = round(uniform(0.00, 0.98), 2)
        coeff2 = round(uniform(0.00, (1 - coeff1)), 2)
        coeff3 = round(uniform(0.00, (1 - (coeff1 + coeff2))), 2)
        coeff4 = 1 - (coeff1 + coeff2 + coeff3)
        self.coefficient = {'frequency': coeff1, 'precedence': coeff2, 'proximity': coeff3, 'mention': coeff4}

    def phrase_cleaner(self, phrase):
        """
        Method to clean unnecessary words from the given phrase/string. (Punctuation mark, symbol unknown, conjunction, deteminer, subordinating or preposition and space)
        """
        clean_phrase = []
        for word in self.nlp(phrase):
            if word.pos_ not in ['PUNCT', 'SYM', 'X', 'CONJ', 'DET', 'ADP', 'SPACE']:
                clean_phrase.append(word.text)
        return ' '.join(clean_phrase)

    def semantic_extractor(self, string):
        """
        Method to extract subject, subjects, focus, subject_with_objects from given string.
        """
        doc = self.nlp(string)
        the_subject = None
        subjects = []   # subject list
        pobjects = []   # object of a preposition list
        dobjects = []   # direct object list
        for np in doc.noun_chunks:
            if (np.root.dep_ == 'nsubj' or np.root.dep_ == 'nsubjpass') and np.root.tag_ != 'WP':
                subjects.append(np.text)
            if np.root.dep_ == 'pobj':
                pobjects.append(np.text)
            if np.root.dep_ == 'dobj':
                dobjects.append(np.text)

        pobjects = [x for x in pobjects]
        subjects = [x for x in subjects]
        dobjects = [x for x in dobjects]
        if pobjects:
            the_subject = ' '.join(pobjects)
        elif subjects:
            the_subject = ' '.join(subjects)
        elif dobjects:
            the_subject = ' '.join(dobjects)
        else:
            return None, None, None, None
        
        focus = None
        if dobjects:
            focus = self.phrase_cleaner(' '.join(dobjects))
        elif subjects:
            focus = self.phrase_cleaner(' '.join(subjects))
        elif pobjects:
            focus = self.phrase_cleaner(' '.join(pobjects))
        if focus in the_subject:
            focus = None

        subject_with_objects = []
        for dobject in dobjects:
            subject_with_objects.append(dobject)
        for subject in subjects:
            subject_with_objects.append(subject)
        for pobject in pobjects:
            subject_with_objects.append(pobject)
        subject_with_objects = ' '.join(subject_with_objects)

        wh_found = False
        for word in doc:
            if word.tag_ in ['WDT', 'WP', 'WP$', 'WRB']:
                wh_found = True
        if not wh_found:
            return None, None, None, None

        return the_subject, subjects, focus, subject_with_objects
