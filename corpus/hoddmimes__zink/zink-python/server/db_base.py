import abc

class db_base(abc.ABC):

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def save(self, application, tag, data):
        pass

    @abc.abstractmethod
    def find(self, application, tag, before, after, limit):
        pass

