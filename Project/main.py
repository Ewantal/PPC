from multiprocessing import Process
import threading
import socket
import sysv_ipc


def house(name, energy_produced, energy_consumed, money, message_queue, market_host, market_port):

    rest_energy = energy_produced - energy_consumed


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as house_socket:
        # Connect to the market using the provided host and port
        house_socket.connect((market_host, market_port))

        # While the rest of energy is not null
        while rest_energy != 0:
            # If there lack of energy send a "NEED" message via the message queue
            if rest_energy < 0:
                message = (name + ":NEED:" + str(abs(rest_energy))).encode()
                print(message)
                message_queue.send(message)
                message, _ = message_queue.receive()
                rest_energy += int(message.decode().split(':')[2])
                print(name + " " + str((message.decode().split(':')[2])))
            # If there is still energy offer it to the market
            elif rest_energy > 0:
                message = (name + ":OFFER:" + str(rest_energy)).encode()
                print(message)
                message_queue.send(message)
                message, _ = message_queue.receive()
                rest_energy -= int(message.decode().split(':')[2])
            # If still not enough energy despite the "NEED" message, buy it from the market
            if rest_energy < 0 and "NEED" in message.decode():
                house_socket.sendall(f"BUY:{abs(rest_energy)}".encode())
                price = float(house_socket.recv(1024).decode().split(':')[1])
                # Check if the house has enough money to buy the energy
                if money >= price:
                    print(name + "buy energy")
                    rest_energy += 1/price*5000
                    money -= price
                else:
                    print(name + "does not have enough money to buy the energy")
            elif rest_energy > 0:
                # If there are no takers, send a "SELL" message to the market
                house_socket.sendall(f"SELL:{rest_energy}".encode())
                print(name + "sell its energy to the market")
                rest_energy = 0

    print(name + " has finished")


class Market(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.priceOfEnergy = 50
    
    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as market_socket:
            market_socket.bind((self.host, self.port))
            market_socket.listen(5)
            while True:
                client_socket, address = market_socket.accept()
                with client_socket:
                    data = client_socket.recv(1024).decode()
                    if data.startswith("SELL:"):
                        sold_amount = int(data.split(":")[1])
                        # decrease the price by a greater amount for larger energy sales
                        self.priceOfEnergy = max(50, self.priceOfEnergy - 0.001 * sold_amount)
                        # send the updated price to the client
                        client_socket.sendall(f"PRICE:{self.priceOfEnergy}".encode())

# Start the market
market = Market("localhost", 6666)
market.start()

# Create the message queue
key = 128
# message_queue = sysv_ipc.MesssageQueue(key, sysv_ipc.IPC_STOP)
message_queue = sysv_ipc.MessageQueue(key, sysv_ipc.IPC_CREAT)

# Create the house processes
house1 = Process(target=house, args=("House 1", 300, 200, 300, message_queue, "localhost", 6666,))
house2 = Process(target=house, args=("House 2", 300, 400, 300, message_queue, "localhost", 6666,))
house3 = Process(target=house, args=("House 3", 100, 150, 300, message_queue, "localhost", 6666,))

# Start the house processes
house1.start()
house2.start()
house3.start()

# Wait them to finish
house1.join()
house2.join()
house3.join()
