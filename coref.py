import itertools

import en_coref_sm


class NeuralCoref:
    def __init__(self):
        self.nlp = en_coref_sm.load()
        self.coms = []

    def resolve(self, com):
        """
        Method to return the version of command where each corfering mention is replaced
        by the main mention in the associated cluster (compare to preious commands)
        """

        com_doc = self.nlp(com)
        n_sents = sum(1 for sent in com_doc.sents)

        token = None
        for token in com_doc:
            pass
        if token.tag_ not in [',', ':', '.']:
            com += '.'
        self.coms.append(com)

        if len(self.coms) > 1:
            chain = ' '.join(self.coms[-2:])

            doc = self.nlp(chain)
            if doc._.has_coref:
                resolution = doc._.coref_resolved
                chained = self.nlp(resolution)
                total_sents = sum(1 for sent in chained.sents)
                sents = itertools.islice(chained.sents, total_sents - n_sents, None)
                sents_arr = []
                for sent in sents:
                    sents_arr.append(sent.text)
                return ' '.join(sents_arr)
            return com
        return com
