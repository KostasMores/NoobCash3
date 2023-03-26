class BlockChain:

    def __init__(self, blocks=[], capacity=1):
        self.blocks = blocks
        self.capacity = capacity 

    def add_block(self, block):
        self.blocks.append(block)
        return
    
    def to_dict(self):
        blockchain = {
            'blocks' : [x.to_dict() for x in self.blocks],
            'capacity' : self.capacity
        }
        return blockchain