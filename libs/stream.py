from collections.abc import Iterable
from itertools import chain, groupby
from functools import reduce

class Stream:
    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], Iterable):
            self.iter = args[0]
        else:
            self.iter = args

    def map(self, mapper):
        self.iter = map(mapper, self.iter)
        return self

    def flat_map(self, mapper):
        self.iter = map(mapper, chain.from_iterable(self.iter))
        return self

    def filter(self, pred):
        self.iter = filter(pred, self.iter)
        return self

    def distinct(self):
        self.iter = set(self.iter)
        return self

    def sorted(self, key=None, reverse=False):
        self.iter = sorted(self.iter, key=key, reverse=reverse)
        return self
    
    def group_by(self, clf=None, down=None):
        self.iter = groupby(sorted(self.iter, key=clf), clf)
        if down:
            self.iter = ((k, down(v)) for k, v in self.iter)
        return self

    def to_seq(self, t=list):
        return t(self.iter)

    def to_mapping(self, key_mapper, val_mapper):
        return {key_mapper(i): val_mapper(i) for i in self.iter}

    def reduce(self, acc, init=None):
        return reduce(acc, self.iter, init) if init else reduce(acc, self.iter)

    def first(self):
        return next(self.iter)

    def for_each(self, func):
        for i in self.iter:
            func(i)
    
    def all(self, pred=None):
        return all(pred(i) for i in self.iter) if pred else all(self.iter)

    def any(self, pred=None):
        return any(pred(i) for i in self.iter) if pred else any(self.iter)

if __name__ == '__main__':
    Stream(1,2,3,4,5,6)\
        .map(lambda x: x**2)\
        .filter(lambda x: x%2==0)\
        .for_each(print)

    print(Stream([(12, 11, 10, 9, 8), range(10)])\
        .flat_map(lambda x: x)\
        .any())