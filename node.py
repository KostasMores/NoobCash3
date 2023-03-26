import time
from block import Block
from wallet import Wallet
from blockchain import BlockChain
from transaction import Transaction
import requests
import termcolor as co
from Crypto.Random import random

CAPACITY = 3
MINING_DIFFICULTY = 4

my_ip = '192.168.1.9'
port = ':5000'

class Node:
    def __init__(self, master = False, N = None):
        if (master == True):
            self.transaction_pool = []  # Here transactions will be accepted and provided with shelter and food no matter where they came from!
            self.validated_transactions = []
            self.wallet = self.create_wallet() # [To Do]: Rich people have big wallys
            gen_block = self.create_genesis_block()
            self.chain = BlockChain(blocks = [gen_block], capacity=CAPACITY) # [To Do]: Ohh kinky ;)
            self.id = 0
            self.ring = {self.wallet.address.decode() : [0, '192.168.1.4']}              # Yes I do <3
            self.id_count = 0
            self.N = N
        else:
            self.transaction_pool = []  # Here transactions will be accepted and provided with shelter and food no matter where they came from!
            self.validated_transactions = []
            self.wallet = self.create_wallet() # [To Do]: Rich people have big wallys
            self.chain = self.create_chain()   # [To Do]: Ohh kinky ;)
            self.id = -1
            self.ring = {}     # Already taken luv </3
            self.id_count = None
            self.N = N

    def add_transaction_to_pool(self, T):
        self.transaction_pool.append(T)
        return
    
    def create_new_block(self, prevHash, tlist):
        return Block(prevHash,time.time(), nonce=-1, tlist=tlist)
    
    def create_wallet(self):
        return Wallet()
    
    def create_chain(self):
        return BlockChain(blocks = [], capacity = CAPACITY)
    
    def register_node_to_ring(self, public_key, ip):
        if (self.id == 0):
            if public_key in self.ring.keys():
                requests.post('http://'+ip+port+'/registerFail',
                              json={'ERROR' : 'Public address already in use!'})
            else:
                self.id_count+=1
                self.ring[public_key] = [self.id_count, ip]                
                # Send the blockchain to the node registering
                blockchain = self.chain.to_dict()
                requests.post('http://'+ip_b+port+'/broadcastBlockchain',
                              json=blockchain)
                
                # Broadcast the ring to everyone in the network
                for _, value in self.ring.items():
                    ip_b = value[1]
                    requests.post('http://'+ip_b+port+'/broadcastRing',
                                  json = {'ring' : self.ring})
                    
                # If all nodes are present in the ring then
                # send each node 100 NBC for entering (so generous ^^)
                if self.N == self.id_count:
                    for pk, _ in self.ring.items(): 
                        transaction = self.create_transaction(receiver=pk.encode(),
                                                            amount=100)
                        for _, value in self.ring.items():
                            ip_b = value[1]
                            transaction_dic = transaction.to_dict()
                            requests.post('http://'+ip_b+port+'/broadcastTransaction',
                                        json = transaction_dic)
        return
    
    def create_transaction(self, receiver, amount):
        s = 0
        transactionInputs = []
        
        for t in self.wallet.utxos:
            if s >= amount:
                # flag = True 
                break
            if t.address == self.wallet.address: 
                transactionInputs.append(t)
                s += t.amount
        if s < amount:
            return None
        else:
            return Transaction(self.wallet.public_key, receiver, amount,
                                       transactionInputs, self.wallet.private_key)
    
    def valid_proof(self, hash, difficulty = MINING_DIFFICULTY):
        i=0
        while i < difficulty:
            if hash[i] != '0':
                return False
            else:
                i += 1
        return True
    
    def create_genesis_block(self):
        genesis_transaction = Transaction(b'0', 100*self.N, [])
        return Block('1', time.time(), nonce = 0, tlist = [genesis_transaction])
    
    # If the Transaction / Block / Chain is valid self.wallet.utxos will change accordingly
    def validate_transaction(self, transaction):
        # Check for valid signature
        if not transaction.verify_signature():
            print(co.colored("[ERROR]: Wrong signature", 'red'))
            return False
        # Check for valid inputs/outputs
        inputs = transaction.transaction_inputs
        outputs = transaction.transaction_outputs
        
        if inputs == []:
            print(co.colored("[ERROR]: Transaction has no inputs", 'red'))
            return False
        
        sum = 0
        for t_in in inputs:
            sum += t_in.amount
        if sum < transaction.amount:
            print(co.colored("[ERROR]: Sender doesn't have enough money", 'red'))
            return False

        for t_in in inputs:
            res = False
            for utxo in self.wallet.utxos:
                if t_in.utxo_id == utxo.utxo_id:
                    res = True
            if res == False:
                print(co.colored("[ERROR]: UTXO input of sender does not exist", 'red'))
                return False
        
        for t_out in outputs:
            if t_out.amount < 0:
                print(co.colored("[ERROR]: UTXO output has negative value", 'red'))
                return False
        
        # Here we are sure that the input is valid, so the utxos are updated

        # First delete the inputs from current utxos
        for t_in in inputs:
            temp = self.wallet.utxos.copy()
            for t in temp:
                if t_in.utxo_id == t.utxo_id:
                    self.wallet.utxos.remove(t)
        
        # Then add to current utxos the outputs
        for t_out in outputs:
            if t_out.amount != 0:
                self.wallet.utxos.append(t_out)
        
        return True
                
    def validate_block(self, block):
        previous_block = self.chain.blocks[len(self.chain.blocks)-1]
        if not (block.previousHash == previous_block.hash):
            return -2
        if not self.valid_proof(block.hash):
            print("[validate_block]: not valid proof")
            print("\tBlock's proof: ", block.hash)
            return -1
        checkpoint = self.wallet.utxos.copy()
        for t in block.listOfTransactions:
            if not self.validate_transaction(t):
                print("[validate_block]: not valid transaction")
                print("\tInvalid Transaction: ", t)
                self.wallet.utxos = checkpoint
                return 0
            # I should update utxos
        return 1
    
    def validate_chain(self, chain):
        # Validate all blocks except genesis block
        checkpoint = self.wallet.utxos.copy()
        self.wallet.utxos = []
        first_block = chain.blocks[0]
        gen_trans = first_block.listOfTransactions[0]
        self.wallet.utxos.append(gen_trans.transaction_outputs[1])
        for block in chain.blocks[1:]:
            flag = self.validate_block(block)
            if flag != 1:
                self.wallet.utxos = checkpoint
                return False
        return True
    
    def wallet_balance(self, target):
        balance = 0
        for utxo in self.wallet.utxos:
            if target.address == utxo.address:
                balance += utxo.amount
        return balance

    def add_transaction_to_pool(self, transaction):
        self.transaction_pool.append(transaction)
        return
   
    def broadcast_transaction(self, transaction):

        dic = transaction.to_dict()
        print(co.colored("[Broadcast]: Transaction ...", 'green'))
        for _, value in self.ring.items():
            if self.id != value[0]:    
                ip = value[1]
                url = 'http://' + ip + port + '/'
                res = requests.post(url + 'broadcastTransaction', json = dic)
        print(co.colored("[Broadcast]: Finished", 'green'))
        return

    def add_transaction_to_block(self, transaction, block):
        block.listOfTransactions.append(transaction)

    def mine_block(self):
        while len(self.validated_transactions) < CAPACITY:
            if self.transaction_pool != []:
                t = self.transaction_pool[0]
                if self.validate_transaction(t):
                    self.validated_transactions.append(t)
                    self.transaction_pool.remove(t)
                else:
                    self.transaction_pool.remove(t)
        mining_block = self.create_new_block(self.chain.blocks[len(self.chain.blocks)-1].hash,
                                             self.validated_transactions)
        while True:
            if self.valid_proof(mining_block.hash):
                self.validated_transactions = []
                self.broadcast_block(mining_block)
                break
            else:
                mining_block.nonce = random.getrandbits(32)
        
        return
    
    def broadcast_block(self, block):
        dic_blck = block.to_dict()
        print("[Block]: Broadcasting ...")
        for _, value in self.ring.items():
            ip = value[1]
            url = 'http://' + ip + port + '/'
            res = requests.post(url + 'broadcastBlock', json = dic_blck)
        print("[Block]: Broadcast END")
        return

    def reverse_transaction(self, T):
        transaction_inputs = T.transaction_inputs
        transaction_outputs = T.transaction_outputs

        for t_out in transaction_outputs:
            temp = self.wallet.utxos.copy()
            for t in temp:
                if t_out.utxo_id == t.utxo_id:
                    self.wallet.utxos.remove(t)
        
        for t_in in transaction_inputs:
            self.wallet.utxoslocal.append(t_in)
                        
    def resolve_conflict(self):
        max_length = len(self.chain.blocks)
        new_chain = None
        for _, value in self.ring.items():
            ip = value[1]
            url = 'http://' + ip + port + '/'
            response = requests.get(url + 'broadcastBlockchain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        if new_chain:
            self.chain = new_chain
            return True
        return False

    