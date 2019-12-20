from web3 import Web3
import json
import pprint
import os

pp = pprint.PrettyPrinter(indent=4)


class NodeManager(object):

    web3 = None
    log = None
    network = 'local'
    default_account = 0  # index of the account

    def __init__(self, options=None, path_to_config='config.json', network='local'):

        if options:
            self.options = options
        else:
            self.options = self.options_from_config(filename=path_to_config)

        self.network = network

    def set_network(self, network):
        self.network = network

    def set_log(self, log):
        self.log = log

    @staticmethod
    def options_from_config(filename='config.json'):
        """ Options from file config.json """

        with open(filename) as f:
            options = json.load(f)

        return options

    def connect_node(self):
        """Connect to the node"""
        network = self.network
        self.web3 = Web3(Web3.HTTPProvider(self.options['networks'][network]['uri'],
                                           request_kwargs={'timeout': self.options['timeout_web3']}))

    def set_default_account(self, index):
        """ Default index account from config.json accounts """

        self.default_account = index

    @property
    def is_connected(self):
        """ Is connected to the node """
        return self.web3.isConnected()

    @property
    def gas_price(self):
        """ Gas Price """
        return self.web3.eth.gasPrice

    @property
    def minimum_gas_price(self):
        """ Gas Price """
        return Web3.toInt(hexstr=self.web3.eth.getBlock('latest').minimumGasPrice)

    @property
    def minimum_gas_price_fixed(self):
        """ Gas Price """
        return 60000000

    @property
    def block_number(self):
        """ Las block number """
        return self.web3.eth.blockNumber

    def balance(self, address):
        """ Balance of the address """
        return self.web3.eth.getBalance(Web3.toChecksumAddress(address))

    def get_block(self, *args, **kargs):
        """ Get the block"""
        return self.web3.eth.getBlock(*args, **kargs)

    def get_transaction_receipt(self, transaction_hash):
        """ Transaction receipt """
        return self.web3.eth.getTransactionReceipt(transaction_hash)

    def transferTo(self, to_address, value, unit='wei'):
        """ Transfer value to... """
        network = self.network
        default_account = self.default_account

        # pk from enviroment or from json
        if 'ACCOUNT_PK_SECRET' in os.environ:
            pk = os.environ['ACCOUNT_PK_SECRET']
        else:
            pk = self.options['networks'][network]['accounts'][default_account]['private_key']

        return self.transfer(pk, to_address, value, unit=unit)

    def transfer(self, private_key, to_address, value, unit='wei'):
        """ transfer """
        network = self.network
        default_account = self.default_account

        # account from enviroment or from json
        if 'ACCOUNT_ADDRESS' in os.environ:
            from_address = os.environ['ACCOUNT_ADDRESS']
        else:
            from_address = self.options['networks'][network]['accounts'][default_account]['address']

        from_address = Web3.toChecksumAddress(from_address)
        to_address = Web3.toChecksumAddress(to_address)

        value = self.web3.toWei(value, unit)

        nonce = self.web3.eth.getTransactionCount(from_address)

        transaction = dict(chainId=self.options['networks'][network]['network_id'],
                           nonce=nonce,
                           gasPrice=self.minimum_gas_price_fixed,
                           gas=100000,
                           to=to_address,
                           value=value)

        signed_transaction = self.web3.eth.account.signTransaction(transaction,
                                                                   private_key)

        return self.web3.eth.sendRawTransaction(
            signed_transaction.rawTransaction)

    def transaction(self, fnc, private_key, value=0, gas_limit=0):

        network = self.network
        default_account = self.default_account

        if not gas_limit:
            gas_limit = fnc.estimateGas()

        # account from enviroment or from json
        if 'ACCOUNT_ADDRESS' in os.environ:
            from_address = Web3.toChecksumAddress(os.environ['ACCOUNT_ADDRESS'])
        else:
            from_address = Web3.toChecksumAddress(self.options['networks'][network]['accounts'][default_account]['address'])

        nonce = self.web3.eth.getTransactionCount(from_address)

        transaction_dict = dict(chainId=self.options['networks'][network]['network_id'],
                                nonce=nonce,
                                gasPrice=self.minimum_gas_price_fixed,
                                gas=gas_limit,
                                value=value)

        transaction = fnc.buildTransaction(transaction_dict)

        signed = self.web3.eth.account.signTransaction(transaction,
                                                       private_key=private_key)

        transaction_hash = self.web3.eth.sendRawTransaction(
            signed.rawTransaction)

        return transaction_hash.hex()

    def fnx_transaction(self, sc, function_, *tx_args, tx_params=None, gas_limit=5800000):
        """Contract agnostic transaction function with extras"""

        network = self.network
        default_account = self.default_account

        fxn_to_call = getattr(sc.functions, function_)
        built_fxn = fxn_to_call(*tx_args)

        gas_estimate = built_fxn.estimateGas()
        self.log.debug("Gas estimate to transact with {}: {}\n".format(function_, gas_estimate))

        if gas_estimate > gas_limit:
            raise Exception("Gas estimated is bigger than gas limit")

        if tx_params:
            if not isinstance(tx_params, dict):
                raise Exception("Tx params need to be dict type")

        self.log.debug("Sending transaction to {} with {} as arguments.\n".format(function_, tx_args))

        # account from enviroment or from json
        if 'ACCOUNT_ADDRESS' in os.environ:
            from_address = Web3.toChecksumAddress(os.environ['ACCOUNT_ADDRESS'])
        else:
            from_address = Web3.toChecksumAddress(self.options['networks'][network]['accounts'][default_account]['address'])

        # pk from enviroment or from json
        if 'ACCOUNT_PK_SECRET' in os.environ:
            pk = os.environ['ACCOUNT_PK_SECRET']
        else:
            pk = self.options['networks'][network]['accounts'][default_account]['private_key']

        nonce = self.web3.eth.getTransactionCount(from_address)

        tx_value = 0
        if tx_params:
            if 'value' in tx_params:
                tx_value = tx_params['value']

        transaction_dict = {'chainId': self.options['networks'][network]['network_id'],
                            'nonce': nonce,
                            'gasPrice': self.minimum_gas_price_fixed,
                            'gas': gas_limit,
                            'value': tx_value}

        transaction = built_fxn.buildTransaction(transaction_dict)

        signed = self.web3.eth.account.signTransaction(transaction,
                                                       private_key=pk)

        transaction_hash = self.web3.eth.sendRawTransaction(
            signed.rawTransaction)

        return transaction_hash

    def fnx_constructor(self, sc, *tx_args, tx_params=None, gas_limit=5800000):
        """Contract agnostic transaction function with extras"""

        network = self.network
        default_account = self.default_account

        built_fxn = sc.constructor(*tx_args)

        gas_estimate = built_fxn.estimateGas()
        self.log.debug("Gas estimate to transact with {}: {}\n".format('Constructor', gas_estimate))

        if gas_estimate > gas_limit:
            raise Exception("Gas estimated is bigger than gas limit")

        if tx_params:
            if not isinstance(tx_params, dict):
                raise Exception("Tx params need to be dict type")

        self.log.debug("Sending transaction to {} with {} as arguments.\n".format('Constructor', tx_args))

        # account from enviroment or from json
        if 'ACCOUNT_ADDRESS' in os.environ:
            from_address = Web3.toChecksumAddress(os.environ['ACCOUNT_ADDRESS'])
        else:
            from_address = Web3.toChecksumAddress(
                self.options['networks'][network]['accounts'][default_account]['address'])

        # pk from enviroment or from json
        if 'ACCOUNT_PK_SECRET' in os.environ:
            pk = os.environ['ACCOUNT_PK_SECRET']
        else:
            pk = self.options['networks'][network]['accounts'][default_account]['private_key']

        nonce = self.web3.eth.getTransactionCount(from_address)

        tx_value = 0
        if tx_params:
            if 'value' in tx_params:
                tx_value = tx_params['value']

        transaction_dict = {'chainId': self.options['networks'][network]['network_id'],
                            'nonce': nonce,
                            'gasPrice': self.minimum_gas_price_fixed,
                            'gas': gas_limit,
                            'value': tx_value}

        transaction = built_fxn.buildTransaction(transaction_dict)

        signed = self.web3.eth.account.signTransaction(transaction,
                                                       private_key=pk)

        transaction_hash = self.web3.eth.sendRawTransaction(
            signed.rawTransaction)

        return transaction_hash

    def wait_transaction_receipt(self, tx_hash, timeout=180):

        # Wait for the transaction to be mined, and get the transaction receipt
        tx_receipt = self.web3.eth.waitForTransactionReceipt(tx_hash, timeout=timeout)

        self.log.debug(
            ("Transaction receipt mined with hash: {hash}\n"
             "on block number {blockNum} "
             "with a total gas usage of {totalGas}").format(
                hash=tx_receipt['transactionHash'].hex(),
                blockNum=tx_receipt['blockNumber'],
                totalGas=tx_receipt['cumulativeGasUsed']
            )
        )

        return tx_receipt

    def sc_from_json_bytecode(self, json_filename):
        """ Get the json content from json compiled """

        with open(json_filename) as f:
            json_content = json.load(f)

        sc = self.web3.eth.contract(abi=json_content["abi"], bytecode=json_content["bytecode"])

        return sc, json_content

    def load_json_contract(self, json_filename, deploy_address=None):
        """ Load the abi """

        network = self.network

        with open(json_filename) as f:
            info_json = json.load(f)
        abi = info_json["abi"]

        # Get from json if we dont know the address
        if not deploy_address:
            deploy_address = info_json["networks"][str(self.options['networks'][network]['network_id'])]['address']

        sc = self.web3.eth.contract(address=self.web3.toChecksumAddress(deploy_address), abi=abi)

        return sc

    def handle_event(self, sc, function_, event):

        receipt = self.web3.eth.waitForTransactionReceipt(event['transactionHash'])

        fxn_to_call = getattr(sc.events, function_)
        built_fxn = fxn_to_call()

        result = built_fxn.processReceipt(receipt)

        if result:
            return result[0]['args']

    def list_events_from(self, sc, function_, from_block=0, to_block='latest'):
        sc_address_to_listen = Web3.toChecksumAddress(sc.address)
        event_filter = self.web3.eth.filter({'fromBlock': from_block, 'toBlock': to_block,
                                             'address': sc_address_to_listen})

        events = list()
        for event in event_filter.get_all_entries():
            eve = self.handle_event(sc, function_, event)
            if eve:
                events.append(eve)

        return events


if __name__ == '__main__':
    print("init")
