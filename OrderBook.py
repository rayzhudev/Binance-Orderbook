import asyncio
import websockets
import json
import requests
import time
import sys
from collections import OrderedDict

class OrderBook():

    def __init__(self, uri, depth_api, symbol, volume):
        self.uri = uri
        self.depth_api = depth_api
        self.symbol = symbol
        self.volume = volume
        self.updates = []
        self.bids = OrderedDict() # ordered dictionary used to sort orders by price
        self.asks = OrderedDict()
        super().__init__()

    # asynchronously receive data from uri
    async def get_orders(self):
        received_snapshot = False
        print(self.symbol + " Average Execution Price for volume: " + str(self.volume))
        async with websockets.connect(self.uri) as websocket:
            while True:
                depth_update = await websocket.recv()
                depth_update = json.loads(depth_update)
                self.updates.append(depth_update)
                # print(depth_update["U"])
                # print("receiving update %d", depth_update["u"])
                if not received_snapshot:
                    self.get_depth_snapshot()
                    received_snapshot = True
                self.process_updates()
                self.update_console()


    def get_depth_snapshot(self):
        snapshot = requests.get(self.depth_api)
        snapshot = json.loads(snapshot.content)
        self.snapshot = snapshot
        for order in snapshot["bids"]:
            self.bids[float(order[0])] = float(order[1])
        for order in snapshot["asks"]:
            self.asks[float(order[0])] = float(order[1])

    def process_updates(self):
        for i in range(len(self.updates)):
            if self.updates[i]["u"] < self.snapshot["lastUpdateId"]:
                self.updates.pop(i)
            else:
                for bid in self.updates[i]["b"]:
                    self.bids[float(bid[0])] = float(bid[1])
                for ask in self.updates[i]["a"]:
                    self.asks[float(ask[0])] = float(ask[1])
        # self.bids = dict(sorted(self.bids, reverse=True), )
        self.bids = OrderedDict(sorted(self.bids.items(), reverse=True))
        self.asks = OrderedDict(sorted(self.asks.items()))
        # print(self.bids)
        # print(list(self.bids.items())[0][0])


    def update_console(self):
        print("\rBUY: %f\tSELL: %f" % (self.get_average_price(False), self.get_average_price(True)), end='')

    # bid has value of False, ask has value of True for parameter side
    def get_average_price(self, side):
        book = self.bids
        avg = float(0)
        if side:
            book = self.asks
        quantity = float(0)
        index = 0
        book = list(book.items())
        while quantity < self.volume:
            curr_order = book[index]
            price = curr_order[0]
            volume = curr_order[1]
            new_quantity = min(volume, self.volume-quantity) # volume filled
            quantity += new_quantity
            avg += new_quantity*price
            index += 1
        avg = avg / self.volume
        return avg


if __name__ == "__main__":
    if not len(sys.argv) == 3:
        print("Need quantity and Pair")
        sys.exit()
    try:
        pair = sys.argv[1]
        volume = float(sys.argv[2])
        if volume < 0:
            raise ValueError
    except Exception as e:
        print("Invalid quantity")
        sys.exit()

    # instantiate orderbook
    BTCUSDT_Book = OrderBook(f"wss://stream.binance.com:9443/ws/{pair.lower()}@depth", f"https://www.binance.com/api/v1/depth?symbol={pair}&limit=1000", pair, volume)
    # start receiving updates and start console
    asyncio.get_event_loop().run_until_complete(BTCUSDT_Book.get_orders())
