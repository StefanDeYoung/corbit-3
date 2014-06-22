__version__ = "3.0.0"
import corbit
from scipy import array, linalg
import json
from unum.units import N,m,s,kg,rad,Hz
import atexit
import time
import itertools
from math import sin,cos,atan2,pi
import socket
import threading

print("Corbit SERVER " + __version__)

entities = []   # This object stores a list of all entities

time_acc_index = 0
time_acceleration = [1, 5, 10, 50, 100, 1000, 10000, 100000]
def time_per_tick():
    return time_acceleration[time_acc_index] / (60*Hz)

G = 6.6720E-11 * N*m**2/kg**2
PORT = 3141




def accelerate_time(amount):
    "Increases how much time is simulated per tick of the server program"
    global time_acc_index
    global time_acceleration
    
    if time_acc_index + amount < 0:
        return
    try:
        time_acceleration[time_acc_index + amount]
        print(time_acc_index + amount)
    except IndexError:
        return
    
    time_acc_index += amount

def accelerate(name, force, angle):
    "Wrapper for accelerating entities, callable on a client machine"
    global entities
    for entity in entities:
        if entity.name == name:
            entity.accelerate(force, angle)

def change_main_engines(name, increment):
    "Changes the engine usage of the specified entity. Fails if no engines"
    global entities
    for entity in entities:
        if entity.name == name:
            entity.main_engines.usage += increment
    
def fire_rcs_thrusters(name, direction):
    "Changes the rcs usage of the specified entity. Fails if no thrusters"
    global entities
    target = corbit.Entity
    for entity in entities:
        if entity.name == name:
            target = entity
    
    rcs_thrust = target.rcs.thrust(time_per_tick())
    theta = direction + target.angular_position
    rcs_thrust_vector = \
        N * array((cos(theta) * rcs_thrust.asNumber(), 
                   sin(theta) * rcs_thrust.asNumber()))
    for angle in target.rcs.engine_positions:
        target.accelerate(
            rcs_thrust_vector/len(target.rcs.engine_positions), angle)
    
def fire_vernier_thrusters(name, amount):
    "Changes the vernier thrusters of the specified entity. Fails if none"
    global entities
    target = corbit.Entity
    for entity in entities:
        if entity.name == name:
            target = entity
   
    vernier_thrust = target.rcs.thrust(time_per_tick())
    vernier_thrust_vector = \
        N * array((0, vernier_thrust.asNumber())) * amount
    target.accelerate(vernier_thrust_vector, 0)
    target.accelerate(-vernier_thrust_vector, pi)
    #for angle in target.rcs.engine_positions:
        #target.accelerate(
            #vernier_thrust_vector/len(target.rcs.engine_positions), angle)
        #print(vernier_thrust_vector,angle)
        ## this code rotates the vernier_thrust_vector by pi/2, since to
        ## rotate a vector, (x,y) = (-y, x)
        #vernier_thrust_vector[0], vernier_thrust_vector[1] = \
        #-vernier_thrust_vector[1], vernier_thrust_vector[0]


with open("../res/OCESS.json", "r") as loadfile:
    entities = corbit.load(loadfile)

def exit_handler():
    serversocket.close()
atexit.register(exit_handler)

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind((socket.gethostname(), PORT))
serversocket.listen(5)
pilot_commands = ""
def pilot_server_thread():
    global pilot_commands
    pilot_socket, addr = serversocket.accept()
    print("Connection from pilot", addr)
    pilot_commands = corbit.recvall(pilot_socket)
    print("got commands:", pilot_commands)
    corbit.sendall(corbit.json_serialize(entities), pilot_socket)


ticks_to_simulate = 0
def ticker():
    global ticks_to_simulate
    ticks_to_simulate += 1
    threading.Timer(time_per_tick().asNumber(s), ticker).start()

ticker()


while True:

    #    for A, B in itertools.combinations(entities, 2):
    #        gravity = corbit.gravitational_force(A, B)
    #        theta = angle(A, B)
    #        A.accelerate(gravity, theta)
    #        B.accelerate(-gravity, theta)

    collisions = []
    for A, B in itertools.combinations(entities, 2):
        affected_objects = corbit.resolve_collision(A, B, time_per_tick())
        if affected_objects != None:
            collisions += affected_objects
    
    for entity in entities:
        already_moved = False
        for name in collisions:
            if entity.name == name:
                already_moved = True
        
        if not already_moved:
            entity.move(time_per_tick())
            
    ticks_to_simulate -= 1  # ticks_to_simulate is incremented in the ticker() function every tick
    
    # while ticks_to_simulate <= 0:
    #     if not connection_established:
    #         try:
    #             clientsocket, address = serversocket.accept()
    #             connection_established = True
    #         except socket.error:
    #             None
    #     else:
    #         if corbit.recvall(clientsocket) == "ACKnowledge connection":
    #             connection_established = True
    #         if not corbit.sendall("connection ACKnowledged", clientsocket):
    #             connection_established = False
    #             print("client is deaf")
    #             break
    #
    #         commands = corbit.recvall(clientsocket)
    #         print("got commands")
    #         print(commands)
    #
    #         if not corbit.sendall(corbit.json_serialize(entities), clientsocket):
    #             connection_established = False
    #             break

    if pilot_commands != "":
        print(pilot_commands.split(" "))
        for command in pilot_commands.split(" "):
            function, argument = command.split("|")[0], command.split("|")[1]
            if len(command.split("|")) != 2:
                print("Malformed command, should have exactly one '|':",command)
            elif function == "fire_verniers":
                if len(argument.split(",")) != 2:
                    print("Malformed argument, should have exactly one ',':",command)
                else:
                    name, amount = argument.split(",")[0], float(argument.split(",")[1])
                    fire_vernier_thrusters(name, amount)
            elif function == "change_engines":
                if len(argument.split(",")) != 2:
                    print("Malformed argument, should have exactly one ',':",command)
                else:
                    name, amount = argument.split(",")[0], float(argument.split(",")[1])
                    change_main_engines(name, amount)
            elif function == "fire_rcs":
                if len(argument.split(",")) != 2:
                    print("Malformed argument, should have exactly one ',':",command)
                else:
                    name, direction = argument.split(",")[0], float(argument.split(",")[1])
                    fire_rcs_thrusters(name, direction)
            elif function == "accelerate_time":
                if len(argument.split(",")) != 1:
                    print("Malformed argument, should have exactly no ',':",command)
                else:
                    amount = int(argument)
                    accelerate_time(amount)
            elif function == "open":
                if len(argument.split(",")) != 1:
                    print("Malformed argument, should have exactly no ',':",command)
                else:
                    filename = argument
                    with open(filename, "r") as loadfile:
                        entities = corbit.load(loadfile)



print("okay")

exit_handler()
