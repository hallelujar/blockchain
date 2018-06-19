from hashlib import sha256
import hashlib
import json
import requests
from textwrap import dedent
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse


class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.new_block(previous_hash = 1, proof = 100)
        self.nodes = set()

    def register_node(self, address):
        """
        add a new node to list of node
        param address: <str> example: https://192.168.0.1:5000
        return: None
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def new_block(self, proof, previous_hash = None):
        # create new block and adds it to the chain
        """
        param proof: <int> the proof given by the proof of work algorithm
        param previous_hash: <str> hash of previous block
        return: <dict> new block
        """
        block = {
            "index": len(self.chain) + 1,
            "timestamp": time(),
            "transactions": self.current_transactions,
            "proof": proof,
            "previous_hash": previous_hash or self.hash(self.chain[-1]),
        }
        # reset the current list of transactions
        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        # add a new transaction to list of transactions
        """ generate new transaction information, add information to next block to be mined.
        param sender: <str> Address of the sender
        param recipient: <str> Address of the recipient
        param amount: <int> Amount
        return: <int> the index of the block that will hold this transaction
        """
        self.current_transactions.append({
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
        })
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        # hash a block
        """
        generate hash value of block
        param block: <dict> block
        return: <str>
        """
        block_string = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # return th last block in the chain
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        check if hash(pp') is beginning with four '0', p is last proof,
        p' is current proof
        param last_proof: <int>
        return : <int>
        """
        proof = 0
        while self.valid_proof(last_proof, proof) == False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        param last_proof: <int>
        param proof: <int>
        return: <bool>
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def valid_chain(self, chain):
        """
        param chain: <list>
        return: <bool>
        """
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print('\n----------\n')
            # check hash of block
            if block['previous_hash'] != self.hash(last_block):
                return False
            # check proof of work
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        """
        return: <bool> True if chain is replaced
        """
        neighbors = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbors:
            response = requests.get(f'http://{node}/chain')
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




# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate our blockchain
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    blockchain.new_transaction(
        sender = '0',
        recipient = node_identifier,
        amount = 1,
    )

    block = blockchain.new_block(proof)
    response = {
        'message': "new block forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
    # create a new transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amout'])
    response = {'message': f'transactions will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if not nodes:
        return 'Error: please get a valid list of nodes', 400
    for node in nodes:
        blockchain.register_node(node)
    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/ndoes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain,
        }
    else:
        response = {
            'message': 'Our chain was legal',
            'new_chain': blockchain.chain,
        }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5000)
