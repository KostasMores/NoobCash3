from Crypto.PublicKey import RSA

class Wallet:

    def __init__(self):
        key_length = 1024
        rsaKeys = RSA.generate(key_length)
        self.private_key = rsaKeys.export_key()
        self.public_key = rsaKeys.publickey().export_key()
        self.address = self.public_key
        self.utxos = []
        self.validutxos = []

    def balance(self):
        return sum([x.amount for x in self.utxos if x.address == self.address])
		
# Use valid utxos to hold utxos of current block in blockchain
# Inorder to put transactions to mining block from valid pool we should check
# If they are valid AGAIN now with validutxos since we trying to put them in
# After this block