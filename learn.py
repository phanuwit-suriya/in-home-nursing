import collections
from os.path import expanduser

from sqlalchemy.orm.exc import NoResultFound
from tinydb import Query, TinyDB

from config import Config
from database import Fact


class Learner:
    def __init__(self, nlp):
        self.pronouns = collections.OrderedDict()
        self.pronouns['I'] = 'YOU'
        self.pronouns['ME'] = 'YOU'
        self.pronouns['MY'] = 'YOUR'
        self.pronouns['MINE'] = 'YOURS'
        self.pronouns['MYSELF'] = 'YOURSELF'
        self.pronouns['OUR'] = 'YOUR'
        self.pronouns['OURS'] = 'YOURS'
        self.pronouns['OURSELVES'] = 'YOURSELVES'
        self.pronouns['WE'] = 'YOU'
        self.pronouns['US'] = 'YOU'

        self.inv_pronouns = collections.OrderedDict()
        self.inv_pronouns['YOU'] = 'I'
        self.inv_pronouns['YOUR'] = 'MY'
        self.inv_pronouns['YOURS'] = 'MINE'
        self.inv_pronouns['YOURSELF'] = 'MYSELF'
        self.inv_pronouns['YOURSELVES'] = 'OURSELVES'

        self.auxiliaries = collections.OrderedDict()
        self.auxiliaries['AM'] = 'ARE'
        self.auxiliaries['\'M'] = ' ARE'
        self.auxiliaries['WAS'] = 'WERE'

        self.inv_auxiliaries = collections.OrderedDict()
        self.inv_auxiliaries['ARE'] = 'AM'
        self.inv_auxiliaries['WERE'] = 'WAS'

        home = expanduser('~')
        self.db = TinyDB(home + '/.db.json')
        self.nlp = nlp
        self.db_session = None

    def response(self, com, user_id=None):
        """
        Method to respond the user's input/command using learning ability
        """

        is_public = True
        com = self.clean(com)
        doc = self.nlp(com)
        subject = []
        types = []
        types.append("")
        for np in doc.noun_chunks:
            types.append(np.root.dep_)
            np_text, is_public = self.detect_pronoun(np.text)
            if np.root.dep_ == 'pobj' and types[-2] == 'nsubj':
                subject.append(np.root.head.text)
                subject.append(np_text)
            if np.root.dep_ == 'nsubj' and types[-2] not in ['pobj', 'nsubj'] and np.root.tag_ not in ['WDT', 'WP', 'WP$', 'WRB']:
                subject.append(np_text)
            if np.root.dep_ == 'attr' and types[-2] not in ['pobj', 'nsubj'] and np.root.tag_ not in ['WDT', 'WP', 'WP$', 'WRB']:
                subject.append(np_text)
            if np.root.dep_ == 'dobj' and types[-2] not in ['pobj', 'nsubj'] and np.root.tag_ not in ['WDT', 'WP', 'WP$', 'WRB']:
                subject.append(np_text)
        subject = [x.strip() for x in subject]
        subject = ' '.join(subject)
        if subject:
            if subject.upper() in self.inv_pronouns:
                return ''
            wh_found = False
            for word in doc:
                if word.tag_ in ['WDT', 'WP', 'WP$', 'WRB']:
                    wh_found = True
            if wh_found:
                straight = self.db_get(subject, is_public=is_public, user_id=user_id)
                if straight is None:
                    return self.db_get(subject, is_public=is_public, user_id=user_id, invert=True)
                return straight
            else:
                verb_found = False
                verbtense = None
                clause = []
                verbs = []
                for word in doc:
                    if verb_found:
                        if word.pos_ != 'PUNCT':
                            clause.append(word.text)
                    if word.pos_ == 'VERB' and word.is_stop and not verb_found:
                        verb_found = True
                        verbtense = word.text
                    if word.pos_ == 'VERB':
                        verbs.append(word.text)
                clause = [x for x in clause]
                clause = ' '.join(clause).strip()

                if any(verb in verbs for verb in self.upper_capitalize(['forget', 'remove', 'delete', 'update'])):
                    return self.db_delete(subject, is_public=is_public, user_id=user_id)

                if any(verb in verbs for verb in self.upper_capitalize(['define', 'explain', 'tell', 'describe'])):
                    return self.db_get(subject, is_public=is_public, user_id=user_id)

                if verbtense:
                    return self.db_upsert(subject, verbtense, clause, com, is_public=is_public, user_id=user_id)

    def db_get(self, subject, invert=False, is_public=True, user_id=None):
        """
        Method to get a record from the database
        """

        if invert:
            result = self.db.search(Query().clause == subject)
        else:
            result = self.db.search(Query().subject == subject)
        if result:
            dictionary = {}
            for row in result:
                if row['verbtense'] not in dictionary:
                    dictionary[row['verbtense']] = []
                if row['clause'] not in dictionary[row['verbtense']]:
                    dictionary[row['verbtense']].append(row['clause'])
            if invert:
                answer = row['subject']
            else:
                answer = subject
            first_verbtense = False
            for key, value in dictionary.items():
                if not first_verbtense:
                    answer += ' ' + str(key)
                    first_verbtense = True
                else:
                    answer += ', ' + str(key)
                first_clause = False
                for clause in value:
                    if not first_clause:
                        answer += ' ' + clause
                        first_clause = True
                    else:
                        answer += ' and ' + clause
            return self.mirror(answer)
        else:
            return None

    def db_upsert(self, subject, verbtense, clause, com, is_public=True, user_id=None):
        """
        Method to insert(or update) a record to the database
        """

        if not self.db.search((Query().subject == subject) & (Query().verbtense == verbtense) & (Query().clause == clause)):
            self.db.insert({
                'subject': subject,
                'verbtense': verbtense,
                'clause': clause
            })
        return 'OK, I get it. ' + self.mirror(com)

    def db_delete(self, subject, is_public=True, user_id=None):
        """
        Method to delete a record from the database
        """

        if self.db.remove(Query().subject == self.fix_pronoun(subject)):
            return 'OK, I forgot everything I know about ' + self.mirror(subject)
        else:
            return 'I don\'t even know anything about ' + self.mirror(subject)

    def mirror(self, answer):
        """
        Method to mirror the answer (for example: I'M to YOU ARE).
        """

        result = []
        types = []
        types.append('')
        doc = self.nlp(answer)
        for token in doc:
            types.append(token.lemma_)
            if token.lemma_ == '-PRON-':
                if token.text.upper() in self.pronouns:
                    result.append(self.pronouns[token.text.upper()].lower().strip())
                    continue
                if token.text.upper() in self.inv_auxiliaries:
                    result.append(self.inv_auxiliaries[token.text.upper()].lower().strip())
                    continue
            if (token.lemma_ == 'be' or token.dep_ == 'aux') and types[-2] == '-PRON-':
                if token.text.upper() in self.auxiliaries:
                    result.append(self.auxiliaries[token.text.upper()].lower().strip())
                    continue
                if token.text.upper() in self.inv_auxiliaries:
                    result.append(self.inv_auxiliaries[token.text.upper()].lower().strip())
                    continue
            result.append(token.text.strip())
        for i in range(len(result)):
            if result[i] == 'i':
                result[i] = 'I'
        result = ' '.join(result)
        return result.replace(" '", "'")

    def fix_pronoun(self, subject):
        """
        Pronoun fixer to handle situations like YOU and YOURSELF.
        """

        if subject == 'yourself':
            return 'you'
        elif subject == 'Yourself':
            return 'You'
        elif subject == 'YOURSELF':
            return 'YOU'
        else:
            return subject

    def detect_pronoun(self, noun_chunk):
        """
        Determine whether user is talking about himself/herself or some other entity.
        """

        np_text = ''
        is_public = True
        doc = self.nlp(noun_chunk)
        for token in doc:
            if token.lemma_ == '-PRON-':
                np_text += ' ' + token.text.lower()
                is_public = False
            else:
                np_text += ' ' + token.text
        return np_text.strip(), is_public

    def upper_capitalize(self, array):
        """
        Return capitalize and uppercased versions of the strings inside the given array
        """

        result = []
        for word in array:
            result.append(word)
            result.append(word.capitalize())
            result.append(word.upper())
        return result

    def clean(self, com):
        """
        Return a version of user's command that cleaned from punctuations, symbols, etc
        """

        doc = self.nlp(com)
        for token in doc:
            if token.pos_ in ['PUNCT', 'SYM']:
                com = com.replace(token.tag_, '')
        return com
