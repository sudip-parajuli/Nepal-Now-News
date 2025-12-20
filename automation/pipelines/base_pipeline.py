from abc import ABC, abstractmethod

class BasePipeline(ABC):
    def __init__(self, config):
        self.config = config
    
    @abstractmethod
    async def run(self):
        """
        Main execution logic for the pipeline.
        """
        pass
