from abc import ABC, abstractmethod


class DocumentRepository(ABC):
    @abstractmethod
    def get_by_id(self, document_id: str):
        pass

    @abstractmethod
    def get_all(self):
        pass

    @abstractmethod
    def add(self, document):
        pass

    @abstractmethod
    def update(self, document):
        pass

    @abstractmethod
    def delete(self, document_id: str) -> bool:
        pass