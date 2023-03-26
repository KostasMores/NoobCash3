import requests
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
import json
import node
from transaction import Transaction, TransactionIO
from block import Block
from blockchain import BlockChain
import base64
import termcolor as co
import threading

master_url='http://192.168.1.9:5000'

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

@app.route('/login', methods=['GET'])
def login():
    master = master_url + '/register'
    requests.post(master, json={'public_key': myNode.wallet.public_key.decode()})
    return "Login Page"

@app.route('/register', methods=['POST'])
def registerNode():
    temp = json.loads((request.data).decode())

    # public_key = bytes(temp['public_key'], 'utf-8')
    public_key = temp['public_key']
    ip=request.remote_addr
    # print(type(public_key))
    
    # print(ip)
    myNode.register_node_to_ring(public_key,ip)
    return '1'

@app.route('/createTransaction', methods=['GET'])
def createTransaction():
    return render_template('createTransaction.html')

@app.route('/createTransaction', methods=['POST'])
def broadcastTransaction():
    field1 = request.form['field1']
    field2 = request.form['field2']
    # process the data here
    # flash('Transaction submitted', 'success')
    # return redirect(url_for('create_transaction_page'))
    for id, value in myNode.ring.items():
        if ('id'+str(value[0])) == field1:
            receiver = id.encode()
    T = myNode.create_transaction(receiver, int(field2))
    if T != None:
        if myNode.validate_transaction(T):
            myNode.add_transaction_to_pool(T)
        myNode.broadcast_transaction(T)
        return "Data received: Recipient -> {0}, Amount -> {1}".format(field1, field2)
    else:
        return "Something went wrong :(" 

# This method is only used at the beginning so entry nodes can get the
# current ring from bootstrap node.
@app.route('/broadcastRing', methods=['POST'])
def receiveRing():
    temp = json.loads((request.data).decode())
    
    ring = temp['ring']
    myNode.ring = ring.copy()
    # Set the id of Node to the id given by master
    for pk, value in ring.items():
        if(myNode.wallet.address.decode() == pk):
            myNode.id = value[0]
    return "Ring Received"

# This method is only used at the beginning so entry nodes can get the
# current blockchain from bootstrap node.
@app.route('/broadcastBlockchain', methods=['POST'])
def receiveBlockchain():
    temp = json.loads((request.data).decode())
    
    blocks = temp['blocks']
    capacity = temp['capacity']

    block_list = []
    for x in blocks:
        prev_hash = x['previousHash']
        ts = x['timestamp']
        nonce = x['nonce']
        transactions = x['listOfTransactions']

        t_list = []
        for t in transactions:
            sender_address = t['sender_address'].encode()
            receiver_address = t['receiver_address'].encode()
            amount = t['amount']
            signature = base64.b64decode(t['signature'].encode())
            transaction_inputs = [TransactionIO(r[0], bytes(r[1],'utf-8'), int(r[2])) for r in t['transaction_inputs']]
            t_list.append(Transaction(sender_address, receiver_address, amount, transaction_inputs, signature=signature))

        block_list.append(Block(prev_hash, ts, nonce=nonce, tlist=t_list))

        blockchain = BlockChain(block_list, capacity)

        if myNode.validate_chain(blockchain):
            myNode.chain = blockchain

            myNode.miner_thread = threading.Thread(target=myNode.mine_block, daemon=True)
            myNode.miner_thread.start()
        else:            
            print(co.colored("[ERROR]: Invalid Blockchain received from bootstrap",
                             'red'))
            print(co.colored("Exiting ... SIKE",
                             'red'))
        return 'Broadcast Blockchain'

# This function should terminate the mining thread.
@app.route('/broadcastBlock', methods=['POST'])
def receive_block():
    myNode.stop_event.set()
    myNode.miner_thread.join()
    temp = json.loads((request.data).decode())
    prev_hash = temp['previousHash']
    ts = temp['timestamp']
    nonce = temp['nonce']
    transactions = temp['listOfTransactions']

    t_list = []
    for t in transactions:
        sender_address = t['sender_address'].encode()
        receiver_address = t['receiver_address'].encode()
        amount = t['amount']
        signature = base64.b64decode(t['signature'].encode())
        inputs = [TransactionIO(r[0], bytes(r[1],'utf-8'), int(r[2])) for r in t['transaction_inputs']]
        t_list.append(Transaction(sender_address, receiver_address, amount, inputs, signature=signature))

    block = Block(prev_hash, ts, nonce, t_list)
    # In order to validate the block utxos must be reset. How?
    # Someone sends me a transaction. This transaction is added to the pool.
    # Who is gonna validate the transaction? Who is gonna add it to the block to mine?
    # Who will initiate the mining process?
    # > Validate transactions until capacity.
    # > Put these transactions to validated transaction pool.
    # > If block received reverse these transactions and put them to the pool. (WAIT FOR IT)
    # > If validated transaction pool reaches capacity start mining the block.

    # MAKE SURE THAT MINING HAS STOPPED AND THAT IT WILL START FROM BEGINNING

    # Reverse the transactions validated to go back to a good state
    # Put the transactions in the pool. If our block is the one received these
    # transactions will be invalidated the second time.
    

    flag = myNode.run_block(block)

    if flag == -2:
        if myNode.resolve_conflict:
            print("[RESOLVE CONFLICT]: Your chain lost")
        else:
            print("[RESOLVE CONFLICT]: Your chain WON")
        myNode.stop_event.clear()
        myNode.miner_thread = threading.Thread(target=myNode.mine_block, daemon=True)
        myNode.miner_thread.start()
        return 'This block does not refer to prev block resolve the conflict'
    elif flag == -1:
        myNode.stop_event.clear()
        myNode.miner_thread = threading.Thread(target=myNode.mine_block, daemon=True)
        myNode.miner_thread.start()
        return 'Invalid Proof Of Work'
    elif flag == 0:
        myNode.stop_event.clear()
        myNode.miner_thread = threading.Thread(target=myNode.mine_block, daemon=True)
        myNode.miner_thread.start()
        return 'Invalid Transaction Inside Block'
    elif flag == 1:
        myNode.stop_event.clear()
        myNode.miner_thread = threading.Thread(target=myNode.mine_block, daemon=True)
        myNode.miner_thread.start()
        return 'Block is valid and has run update checkpoint'
    else:
        return "whadafuq"


# This method is called when we receive a transaction.
# This transaction is added to the pool of unvalidated transactions.
# Bring your swimsuit :)
@app.route('/broadcastTransaction', methods=['POST'])
def receiveTransaction():
    temp = json.loads((request.data).decode())

    signature = base64.b64decode(temp['signature'].encode())
    sender_address = bytes(temp['sender_address'], 'utf-8')
    receiver_address = bytes(temp['receiver_address'], 'utf-8')
    amount = temp['amount']

    inputs = [TransactionIO(r[0], bytes(r[1],'utf-8'), int(r[2])) for r in temp['transaction_inputs']]
    T = Transaction(sender_address, receiver_address, amount, inputs, signature=signature)

    if myNode.validate_transaction(T):
        myNode.add_transaction_to_pool(T)

    return temp

@app.route('/consensus', methods=['GET'])
def consensus():
    chain = myNode.chain.to_dict()
    length = len(myNode.chain.blocks)
    to_send = {'chain' : chain, 'length': length}

    return jsonify(to_send), 200

@app.route('/printBlockchain', methods=['GET'])
def print_blockchain():
    str_chain = myNode.chain.to_dict()
    return str_chain

@app.route('/getBalance', methods=['GET', 'POST'])
def getBalance():
    balance = myNode.wallet.balance()
    print(balance)
    # ret = str(balance)
    return str(balance)

if __name__ == '__main__':
    from argparse import ArgumentParser  

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    myNode = node.Node(master=True, N=2)
    # print(myNode.wallet.public_key)
    # myBlock = myNode.create_new_block()
    
    app.run(host='192.168.1.9', port=port, debug=True)
    