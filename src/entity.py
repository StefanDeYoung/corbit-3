from unum.units import rad,m,s,kg,N
import collections
from math import atan2,cos,sin,pi
import scipy.linalg as linalg
from scipy import array

class Entity:
    "Base class for all physical objects"
            
    def __init__(self, name, color, mass, radius,
                 displacement, velocity, acceleration,
                 angular_position, angular_speed, angular_acceleration):
        
        self.name = name    # should be a string
        self.color = color  # should be a tuple, e.g. (255,255,5)
        self.mass = mass    # should be in units of kg
        self.radius = radius    # should be in units of m
        
        self.displacement = displacement    # should be in units of m
        self.velocity = velocity            # should be in units of m/s
        self.acceleration = acceleration    # should be in units of m/s/s 
        
        self.angular_position = angular_position    # units: radians 
        self.angular_speed = angular_speed            # units: radians/s
        self.angular_acceleration = angular_acceleration    # units: radians/s/s
    
    def moment_of_inertia(self):
        "Returns the entity's moment of inertia, which is that of a sphere"
        return (2 * self.mass * self.radius**2) / 5
    
    def accelerate(self, force, angle):
        """
        Called when the entity is accelerated by a force
        force: a cartesian force vector
        angle: the angle on the entity that the force is applied onto.
        An angle of zero would mean the force is applied on the front, while
        An angle of pi/2 would mean the force is applied on the left
        ("front" is where the entity is pointing, i.e. self.angular_position)
        """
        angle += self.angular_position
        # F_theta is the angle of the vector F from the x axis
        ## for example, a force vector pointing directly up will have
        ## F_theta = pi/2
        # angle is the angle from the x axis the force is applied to the entity
        ## for example, a rock hitting the right side of the hab will have
        ## angle = 0
        ## and the engines firing from the bottom of the hab will have
        ## angle = 3pi/2
        F_theta = atan2(force[1].asNumber(), force[0].asNumber())
        
        # a = F / m
        ## where
        # a is linear acceleration, m is mass of entity
        # F is the force that is used in making linear acceleration
        F_cen = force * abs(cos(angle - F_theta))
        self.acceleration += F_cen / self.mass
        
        # w = T / I
        ## where
        # w is angular acceleration in rad/s/s
        # T is torque in J/rad
        # I is moment of inertia in kg*m^2
        T = N * linalg.norm(force.asNumber()) \
            * self.radius * sin(angle - F_theta)
        self.angular_acceleration += T / self.moment_of_inertia()
        
    def move(self, time):
        "Updates velocities, positions, and rotations for entity"
        
        self.velocity += self.acceleration * time
        self.acceleration = 0 * m/s/s
        self.displacement += self.velocity * time

        self.angular_speed += self.angular_acceleration * time
        self.angular_acceleration = 0 * rad/s/s
        self.angular_position += self.angular_speed * time
    
    def dict_repr(self):
        "Returns a dictionary representation of the Entity"
        
        blob = collections.OrderedDict([
        
         ("name", self.name),
         ("color", self.color),  
         ("mass", self.mass.asNumber()),
         ("radius", self.radius.asNumber()),
         
         ("displacement", self.displacement.asNumber().tolist()),
         ("velocity", self.velocity.asNumber().tolist()),
         ("acceleration", self.acceleration.asNumber().tolist()),
         
         ("angular_position", self.angular_position.asNumber()),
         ("angular_speed", self.angular_speed.asNumber()),
         ("angular_acceleration", self.angular_acceleration.asNumber())
        
        ])
        
        return blob
        
class Habitat(Entity):
    "A special class for the habitat"
    
    def __init__(self, name, color, mass, radius,
                 displacement, velocity, acceleration,
                 angular_position, angular_speed, angular_acceleration,
                 fuel):
        Entity.__init__(self, name, color, mass, radius,
                 displacement, velocity, acceleration,
                 angular_position, angular_speed, angular_acceleration)
        
        self.fuel = fuel
        self.engine_usage = 0
        self.fuel_flow_rate = 10 * kg/s
        self.I_sp = 500 * m/s
        
    def move(self, time):
        "kind of a place holder function atm"
        if self.fuel > (self.fuel_flow_rate * abs(self.engine_usage)) * time:
            fuel_usage = self.fuel_flow_rate * abs(self.engine_usage)
            self.fuel -= (self.fuel_flow_rate * abs(self.engine_usage)) * time
        else:
            fuel_usage = self.fuel / time
            self.fuel = 0 * kg
        
        print(self.fuel)
        print(fuel_usage)
            
        thrust = self.I_sp * fuel_usage
        thrust_vector = N *array((cos(self.angular_position)*thrust.asNumber(),
                                  sin(self.angular_position)*thrust.asNumber()))
        self.accelerate(thrust_vector, pi/2)
        Entity.move(self, time)
