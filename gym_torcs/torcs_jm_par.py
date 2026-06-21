import socket
import sys
import getopt
import os
import time
import math
import torcs_model as model
import numpy as np
import random
import json
import threading
import queue
PI= 3.14159265359

#Parrallel Processing Components.
experience_queue=queue.Queue()
training_active=threading.Event()
weights_lock=threading.Lock()

data_size = 2**17

ophelp=  'Options:\n'
ophelp+= ' --host, -H <host>    TORCS server host. [localhost]\n'
ophelp+= ' --port, -p <port>    TORCS port. [3001]\n'
ophelp+= ' --id, -i <id>        ID for server. [SCR]\n'
ophelp+= ' --steps, -m <#>      Maximum simulation steps. 1 sec ~ 50 steps. [100000]\n'
ophelp+= ' --episodes, -e <#>   Maximum learning episodes. [1]\n'
ophelp+= ' --track, -t <track>  Your name for this track. Used for learning. [unknown]\n'
ophelp+= ' --stage, -s <#>      0=warm up, 1=qualifying, 2=race, 3=unknown. [3]\n'
ophelp+= ' --debug, -d          Output full telemetry.\n'
ophelp+= ' --help, -h           Show this help.\n'
ophelp+= ' --version, -v        Show current version.'
usage= 'Usage: %s [ophelp [optargs]] \n' % sys.argv[0]
usage= usage + ophelp
version= "20130505-2"

def clip(v,lo,hi):
    if v<lo: return lo
    elif v>hi: return hi
    else: return v

def bargraph(x,mn,mx,w,c='X'):
    if not w: return ''
    x=clip(x,mn,mx)
    tx= mx-mn
    if tx<=0: return 'backwards'
    upw= tx/float(w)
    if upw<=0: return 'What?'
    negpu, pospu, negnonpu, posnonpu= 0,0,0,0
    if mn < 0:
        if x < 0:
            negpu= -x + min(0,mx)
            negnonpu= -mn + x
        else:
            negnonpu= -mn + min(0,mx)
    if mx > 0:
        if x > 0:
            pospu= x - max(0,mn)
            posnonpu= mx - x
        else:
            posnonpu= mx - max(0,mn)
    nnc= int(negnonpu/upw)*'-'
    npc= int(negpu/upw)*c
    ppc= int(pospu/upw)*c
    pnc= int(posnonpu/upw)*'_'
    return '[%s]' % (nnc+npc+ppc+pnc)

class Client():
    def __init__(self,H=None,p=None,i=None,e=None,t=None,s=None,d=None,vision=False):
        self.vision = vision

        self.host= 'localhost'
        self.port= 3001
        self.sid= 'SCR'
        self.maxEpisodes=1
        self.trackname= 'unknown'
        self.stage= 3
        self.debug= False
        self.maxSteps= 100000
        self.parse_the_command_line()
        if H: self.host= H
        if p: self.port= p
        if i: self.sid= i
        if e: self.maxEpisodes= e
        if t: self.trackname= t
        if s: self.stage= s
        if d: self.debug= d
        self.S= ServerState()
        self.R= DriverAction()
        self.setup_connection()

    def setup_connection(self):
        try:
            self.so= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error as emsg:
            print('Error: Could not create socket...')
            sys.exit(-1)
        self.so.settimeout(1)

        n_fail = 5
        while True:
            a= "-45 -19 -12 -7 -4 -2.5 -1.7 -1 -.5 0 .5 1 1.7 2.5 4 7 12 19 45"

            initmsg='%s(init %s)' % (self.sid,a)

            try:
                self.so.sendto(initmsg.encode(), (self.host, self.port))
            except socket.error as emsg:
                sys.exit(-1)
            sockdata= str()
            try:
                sockdata,addr= self.so.recvfrom(data_size)
                sockdata = sockdata.decode('utf-8')
            except socket.error as emsg:
                print("Waiting for server on %d............" % self.port)
                print("Count Down : " + str(n_fail))
                if n_fail < 0:
                    print("relaunch torcs")
                    os.system('pkill torcs')
                    time.sleep(1.0)
                    if self.vision is False:
                        os.system('torcs -nofuel -nodamage -nolaptime &')
                    else:
                        os.system('torcs -nofuel -nodamage -nolaptime -vision &')

                    time.sleep(1.0)
                    os.system('sh autostart.sh')
                    n_fail = 5
                n_fail -= 1

            identify = '***identified***'
            if identify in sockdata:
                print("Client connected on %d.............." % self.port)
                break

    def parse_the_command_line(self):
        try:
            (opts, args) = getopt.getopt(sys.argv[1:], 'H:p:i:m:e:t:s:dhv',
                       ['host=','port=','id=','steps=',
                        'episodes=','track=','stage=',
                        'debug','help','version'])
        except getopt.error as why:
            print('getopt error: %s\n%s' % (why, usage))
            sys.exit(-1)
        try:
            for opt in opts:
                if opt[0] == '-h' or opt[0] == '--help':
                    print(usage)
                    sys.exit(0)
                if opt[0] == '-d' or opt[0] == '--debug':
                    self.debug= True
                if opt[0] == '-H' or opt[0] == '--host':
                    self.host= opt[1]
                if opt[0] == '-i' or opt[0] == '--id':
                    self.sid= opt[1]
                if opt[0] == '-t' or opt[0] == '--track':
                    self.trackname= opt[1]
                if opt[0] == '-s' or opt[0] == '--stage':
                    self.stage= int(opt[1])
                if opt[0] == '-p' or opt[0] == '--port':
                    self.port= int(opt[1])
                if opt[0] == '-e' or opt[0] == '--episodes':
                    self.maxEpisodes= int(opt[1])
                if opt[0] == '-m' or opt[0] == '--steps':
                    self.maxSteps= int(opt[1])
                if opt[0] == '-v' or opt[0] == '--version':
                    print('%s %s' % (sys.argv[0], version))
                    sys.exit(0)
        except ValueError as why:
            print('Bad parameter \'%s\' for option %s: %s\n%s' % (
                                       opt[1], opt[0], why, usage))
            sys.exit(-1)
        if len(args) > 0:
            print('Superflous input? %s\n%s' % (', '.join(args), usage))
            sys.exit(-1)

    def get_servers_input(self):
        if not self.so: return
        sockdata= str()

        while True:
            try:
                sockdata,addr= self.so.recvfrom(data_size)
                sockdata = sockdata.decode('utf-8')
            except socket.error as emsg:
                print('.', end=' ')
            if '***identified***' in sockdata:
                print("Client connected on %d.............." % self.port)
                continue
            elif '***shutdown***' in sockdata:
                print((("Server has stopped the race on %d. "+
                        "You were in %d place.") %
                        (self.port,self.S.d['racePos'])))
                self.shutdown()
                return
            elif '***restart***' in sockdata:
                print("Server has restarted the race on %d." % self.port)
                self.shutdown()
                return
            elif not sockdata:
                continue
            else:
                self.S.parse_server_str(sockdata)
                if self.debug:
                    sys.stderr.write("\x1b[2J\x1b[H")
                    print(self.S)
                break

    def respond_to_server(self):
        if not self.so: return
        try:
            message = repr(self.R)
            self.so.sendto(message.encode(), (self.host, self.port))
        except socket.error as emsg:
            print("Error sending to server: %s Message %s" % (emsg[1],str(emsg[0])))
            sys.exit(-1)
        if self.debug: print(self.R.fancyout())

    def shutdown(self):
        if not self.so: return
        print(("Race terminated or %d steps elapsed. Shutting down %d."
               % (self.maxSteps,self.port)))
        self.so.close()
        self.so = None

class ServerState():
    '''What the server is reporting right now.'''
    def __init__(self):
        self.servstr= str()
        self.d= dict()

    def parse_server_str(self, server_string):
        self.servstr= server_string.strip()[:-1]
        sslisted= self.servstr.strip().lstrip('(').rstrip(')').split(')(')
        for i in sslisted:
            w= i.split(' ')
            self.d[w[0]]= destringify(w[1:])

    def __repr__(self):
        return self.fancyout()
        out= str()
        for k in sorted(self.d):
            strout= str(self.d[k])
            if type(self.d[k]) is list:
                strlist= [str(i) for i in self.d[k]]
                strout= ', '.join(strlist)
            out+= "%s: %s\n" % (k,strout)
        return out

    def fancyout(self):
        out= str()
        sensors= [
        'stucktimer',
        'fuel',
        'distRaced',
        'distFromStart',
        'opponents',
        'wheelSpinVel',
        'z',
        'speedZ',
        'speedY',
        'speedX',
        'targetSpeed',
        'rpm',
        'skid',
        'slip',
        'track',
        'trackPos',
        'angle',
        ]

        for k in sensors:
            if type(self.d.get(k)) is list:
                if k == 'track':
                    strout= str()
                    raw_tsens= ['%.1f'%x for x in self.d['track']]
                    strout+= ' '.join(raw_tsens[:9])+'_'+raw_tsens[9]+'_'+' '.join(raw_tsens[10:])
                elif k == 'opponents':
                    strout= str()
                    for osensor in self.d['opponents']:
                        if   osensor >190: oc= '_'
                        elif osensor > 90: oc= '.'
                        elif osensor > 39: oc= chr(int(osensor/2)+97-19)
                        elif osensor > 13: oc= chr(int(osensor)+65-13)
                        elif osensor >  3: oc= chr(int(osensor)+48-3)
                        else: oc= '?'
                        strout+= oc
                    strout= ' -> '+strout[:18] + ' ' + strout[18:]+' <-'
                else:
                    strlist= [str(i) for i in self.d[k]]
                    strout= ', '.join(strlist)
            else:
                if k == 'gear':
                    gs= '_._._._._._._._._'
                    p= int(self.d['gear']) * 2 + 2
                    l= '%d'%self.d['gear']
                    if l=='-1': l= 'R'
                    if l=='0':  l= 'N'
                    strout= gs[:p]+ '(%s)'%l + gs[p+3:]
                elif k == 'damage':
                    strout= '%6.0f %s' % (self.d[k], bargraph(self.d[k],0,10000,50,'~'))
                elif k == 'fuel':
                    strout= '%6.0f %s' % (self.d[k], bargraph(self.d[k],0,100,50,'f'))
                elif k == 'speedX':
                    cx= 'X'
                    if self.d[k]<0: cx= 'R'
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k],-30,300,50,cx))
                elif k == 'speedY':
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k]*-1,-25,25,50,'Y'))
                elif k == 'speedZ':
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k],-13,13,50,'Z'))
                elif k == 'z':
                    strout= '%6.3f %s' % (self.d[k], bargraph(self.d[k],.3,.5,50,'z'))
                elif k == 'trackPos':
                    cx='<'
                    if self.d[k]<0: cx= '>'
                    strout= '%6.3f %s' % (self.d[k], bargraph(self.d[k]*-1,-1,1,50,cx))
                elif k == 'stucktimer':
                    if self.d[k]:
                        strout= '%3d %s' % (self.d[k], bargraph(self.d[k],0,300,50,"'"))
                    else: strout= 'Not stuck!'
                elif k == 'rpm':
                    g= self.d['gear']
                    if g < 0:
                        g= 'R'
                    else:
                        g= '%1d'% g
                    strout= bargraph(self.d[k],0,10000,50,g)
                elif k == 'angle':
                    asyms= [
                          "  !  ", ".|'  ", "./'  ", "_.-  ", ".--  ", "..-  ",
                          "---  ", ".__  ", "-._  ", "'-.  ", "'\.  ", "'|.  ",
                          "  |  ", "  .|'", "  ./'", "  .-'", "  _.-", "  __.",
                          "  ---", "  --.", "  -._", "  -..", "  '\.", "  '|."  ]
                    rad= self.d[k]
                    deg= int(rad*180/PI)
                    symno= int(.5+ (rad+PI) / (PI/12) )
                    symno= symno % (len(asyms)-1)
                    strout= '%5.2f %3d (%s)' % (rad,deg,asyms[symno])
                elif k == 'skid':
                    frontwheelradpersec= self.d['wheelSpinVel'][0]
                    skid= 0
                    if frontwheelradpersec:
                        skid= .5555555555*self.d['speedX']/frontwheelradpersec - .66124
                    strout= bargraph(skid,-.05,.4,50,'*')
                elif k == 'slip':
                    frontwheelradpersec= self.d['wheelSpinVel'][0]
                    slip= 0
                    if frontwheelradpersec:
                        slip= ((self.d['wheelSpinVel'][2]+self.d['wheelSpinVel'][3]) -
                              (self.d['wheelSpinVel'][0]+self.d['wheelSpinVel'][1]))
                    strout= bargraph(slip,-5,150,50,'@')
                else:
                    strout= str(self.d[k])
            out+= "%s: %s\n" % (k,strout)
        return out

class DriverAction():
    '''What the driver is intending to do (i.e. send to the server).'''
    def __init__(self):
       self.actionstr= str()
       self.d= { 'accel':0.2,
                   'brake':0,
                  'clutch':0,
                    'gear':1,
                   'steer':0,
                   'focus':[-90,-45,0,45,90],
                    'meta':0
                    }

    def clip_to_limits(self):
        self.d['steer']= clip(self.d['steer'], -1, 1)
        self.d['brake']= clip(self.d['brake'], 0, 1)
        self.d['accel']= clip(self.d['accel'], 0, 1)
        self.d['clutch']= clip(self.d['clutch'], 0, 1)
        if self.d['gear'] not in [-1, 0, 1, 2, 3, 4, 5, 6]:
            self.d['gear']= 0
        if self.d['meta'] not in [0,1]:
            self.d['meta']= 0
        if type(self.d['focus']) is not list or min(self.d['focus'])<-180 or max(self.d['focus'])>180:
            self.d['focus']= 0

    def __repr__(self):
        self.clip_to_limits()
        out= str()
        for k in self.d:
            out+= '('+k+' '
            v= self.d[k]
            if not type(v) is list:
                out+= '%.3f' % v
            else:
                out+= ' '.join([str(x) for x in v])
            out+= ')'
        return out+'\n'

    def fancyout(self):
        out= str()
        od= self.d.copy()
        od.pop('gear','')
        od.pop('meta','')
        od.pop('focus','')
        for k in sorted(od):
            if k == 'clutch' or k == 'brake' or k == 'accel':
                strout=''
                strout= '%6.3f %s' % (od[k], bargraph(od[k],0,1,50,k[0].upper()))
            elif k == 'steer':
                strout= '%6.3f %s' % (od[k], bargraph(od[k]*-1,-1,1,50,'S'))
            else:
                strout= str(od[k])
            out+= "%s: %s\n" % (k,strout)
        return out

def destringify(s):
    if not s: return s
    if type(s) is str:
        try:
            return float(s)
        except ValueError:
            print("Could not find a value in %s" % s)
            return s
    elif type(s) is list:
        if len(s) < 2:
            return destringify(s[0])
        else:
            return [destringify(i) for i in s]


def drive_example(c):
    S,R= c.S.d,c.R.d
    target_speed=160

    R['steer']= S['angle']*25 / PI
    R['steer']-= S['trackPos']*.25

    R['accel'] = max(0.0, min(1.0, R['accel']))

    if S['speedX'] < target_speed - (R['steer']*2.5):
        R['accel']+= .4
    else:
        R['accel']-= .2
    if S['speedX']<10:
       R['accel']+= 1/(S['speedX']+.1)

    if ((S['wheelSpinVel'][2]+S['wheelSpinVel'][3]) -
       (S['wheelSpinVel'][0]+S['wheelSpinVel'][1]) > 2):
       R['accel']-= 0.1

    R['gear']=1
    if S['speedX']>60:
        R['gear']=2
    if S['speedX']>100:
        R['gear']=3
    if S['speedX']>140:
        R['gear']=4
    if S['speedX']>190:
        R['gear']=5
    if S['speedX']>220:
        R['gear']=6
    return

TARGET_SPEED=100
STEER_GAIN=30
CENTERING_GAIN=0.20
BRAKE_THRESHOLD=0.9
GEAR_SPEEDS=[0,20,40,80,100,120]
ENABLE_TACTION_CONTOL=True

##############################################################
#  LAGUNA SECA (WeatherTech Raceway) — TAILORED DRIVE LOGIC  #
##############################################################
#Added a feature which uses the neural network approach into the present algorithm.

def get_sensor_vector(S):
    #compresses sensor readings into a normalised column vector.
    track=S.get('track',[100]*19)
    wheels=S.get('wheelSpinVel',[0]*4)

    inputs=[
        *[t/200.0 for t in track],
        S.get('speedX',0)/300.0,
        S.get('speedY',0)/50.0,
        S.get('angle',0)/PI,
        S.get('trackPos',0),
        *[w/100.0 for w in wheels],
        S.get('rpm',0)/10000.0,
        S.get('gear',1)/6.0
    ]
    return np.array(inputs).reshape(-1,1)

def apply_action(R,action):
    #Translates the outputs of the neural networks into car controls.
    action=action.flatten()
    R['steer']=float(np.clip(action[0],-1,1))
    R['accel']=float(np.clip(action[1],0,1))
    R['brake']=float(np.clip(action[2],0,1))

    #Rounds gear output to the nearest gear setting.
    gear_raw=float(np.squeeze(action[3]))
    gear_val=int(np.clip(round(gear_raw*6),1,6))
    R['gear']=gear_val
                 
def construct_target(action,reward,R):
    """
        We want the neural network approach to focus on improving the manual
        algorithm we have. So, this is doing what the 
    
    """

    action=np.array([
        R['steer'],
        R['accel'],
        R['brake'],
        R['gear']/6.0
    ]).reshape(-1,1)

    #Trust the network or the previous algorithm.
    blend=np.clip(0.5+reward*0.1,0.0,1.0)
    target=blend*action+(1.0-blend)*action

    #Clip to defined ranges.
    target[0]=np.clip(target[0],-1,1)
    target[1]=np.clip(target[1],0,1)
    target[2]=np.clip(target[2],0,1)
    target[3]=np.clip(target[3],0,1)

    return target

def run_lap(network,client,eta):
    """
        -Runs one full lap using the drive_laguna and neural network. Computes cost function and reward, then retrains.
        - We have a function that does a decent job, the network should improve it.
        

        Three Steps:
        1. drive_laguna computes its suggestion.
        2. network computes its suggestion.
        3. The two suggestions are blended together, and ideally the network should do better.
    
    
    
    """
    experiences=[]
    recovery_count=0
    lap_start_damage=client.S.d.get('damage',0)
    prev_lap_time=0
    lap_num=0
    best_cost=float('inf')

    network_thrust=getattr(network,'trust',0.2)

    for step in range(client.maxSteps):
        client.get_servers_input()

        #Client closed connection.
        if client.so is None:
            break

        S=client.S.d
        R=client.R.d

        if 'speedX' not in S:
            continue

        #Laguna's implementation.
        drive_laguna(client)
        R_laguna={
            'steer':R['steer'],
            'accel':R['accel'],
            'brake':R['brake'],
            'gear':R['gear']
        }
        #Network's suggestion
        sensors=get_sensor_vector(S)
        network_action=network.feedForward(sensors)

        #Blending
        laguna_action=np.array([R_laguna['steer'],R_laguna['accel'],R_laguna['brake'],R_laguna['gear']/6.0]).reshape(-1,1)

        if np.any(np.isnan(network_action)) or np.any(np.isinf(network_action)):
            blended_action=laguna_action
        else:
            blended_action=network_thrust*network_action+(1-network_thrust)*laguna_action


        if R_laguna['gear']==-1:
            apply_action(R,laguna_action)
            recovery_count+=1
        else:
            apply_action(R,blended_action)

        experiences.append((sensors,blended_action,R_laguna))
        client.respond_to_server()

        current_lap_time=S.get('lastLapTime',0)
        if current_lap_time>0 and current_lap_time!=prev_lap_time:
            damage_delta=S.get('damage',0)-lap_start_damage
            collisions=damage_delta/100.0

            cost=current_lap_time+(recovery_count*5)+(collisions*3)
            reward=(best_cost-cost)/max(best_cost,1.0)

            training_data=[]
            for sns,act,lag in experiences:
                target=construct_target(act,reward,lag)
                training_data.append((sns,target))

            mini_batch_size=32
            random.shuffle(training_data)
            mini_batches=[
                training_data[k:k+mini_batch_size] for k in range(0,len(training_data),mini_batch_size)]
            

            nan_detected = any(np.any(np.isnan(w)) for w in network.weights) or any(np.any(np.isnan(b)) for b in network.biases)
            
            for m in mini_batches:
                network.update_mini_batch(m,eta)

            if nan_detected:
                print("WARNING: Training produced NaN weights! Reverting to last good state.")
                network.weights = [np.array(w) for w in last_good_weights]
                network.biases  = [np.array(b) for b in last_good_biases]
            else:
    # Only update the "last good" snapshot if everything is still sane
                last_good_weights = [w.copy() for w in network.weights]
                last_good_biases  = [b.copy() for b in network.biases]


            if reward>0:
                network.trust=min(network.trust+0.05,0.95)
            else:
                network.trust=max(network.trust-0.02,0.05)
            network_trust=network.trust

            if cost<best_cost:
                best_cost=cost
                with open('weights.json','w') as f:
                    json.dump({
                        'weights':[w.tolist() for w in network.weights],
                        'biases':[b.tolist() for b in network.biases],
                        'trust':network.trust,
                        'best_cost':best_cost,
                        'lap':lap_num
                    },f)

            eta=max(eta*0.99,0.00001)

            experiences=[]
            recovery_count=0
            lap_start_damage=S.get('damage',0)
            lap_num+=1
        prev_lap_time=current_lap_time
    
    client.shutdown()

#Defines a drive thread.
def driving_thread(client):
    #This thread is for driving.
    for step in range(client.maxSteps):
        client.get_servers_input()

        if client is None:
            #Stops training thread.
            training_active.clear()
            break

        S=client.S.d
        R=client.R.d

        if 'speedX' not in S:
            continue

        drive_laguna(client)
        laguna_out=np.array([R['steer'],R['accel'],R['brake'],R['gear']/6.0]).reshape(-1,1)

        sensors=get_sensor_vector(S)

        client.respond_to_server()

        if not np.any(np.isnan(laguna_out)):
            experience_queue.put((sensors,laguna_out))
        else:
            print("Erroneous data detected.")
    
    client.shutdown()

def training_thread(network,eta,batch_size=32):
    print("Thread started.")
    last_good_weights=[w.copy() for w in network.weights]
    last_good_biases=[b.copy() for b in network.biases]

    buffer=[]

    if not training_active.is_set():
        print("Selection error.")
    else:
        print("Thread activation is set.")

    while training_active.is_set():
        try:
            item=experience_queue.get(timeout=0.01)
            buffer.append(item)
        except queue.Empty:
            continue

        if len(buffer)>=batch_size:
            print("Onboard")
            with weights_lock:
                print(network,eta)
                network.update_mini_batch(buffer,eta)

                if any(np.any(np.isnan(w)) for w in network.weights):
                    network.weights=[w.copy() for w in last_good_weights]
                    network.biases=[b.copy() for b in last_good_biases]
                else:
                    network.weights=[w.copy() for w in network.weights]
                    network.biases=[b.copy() for b in network.biases]

                buffer=[]
        else:
            print("huh?")

def train_laguna(network,client,eta):
    
    training_active.set()

    drive_t=threading.Thread(target=driving_thread,args=(client,))
    train_t=threading.Thread(target=training_thread,args=(network,eta))

    drive_t.start()
    train_t.start()

    drive_t.join()            #Waits for the thread to finish.
    training_active.clear()   #Switches training 
    train_t.join()

    with open('weights.json','w') as f:
        json.dump({
            'weights': [w.tolist() for w in network.weights],
            'biases':  [b.tolist() for b in network.biases],
            'mode':    'imitation-threaded'
        },f,indent=2)






            
_recovery_counter = 0

LAGUNA_CORNER_SPEEDS = [
    (200, 240),   # very long view — flat-out straight
    (120, 200),   # long approach — carry speed
    ( 70, 155),   # medium corner (T6/T9/T10 style)
    ( 40, 110),   # tighter corner (T5/T3 style)
    ( 20,  80),   # sharp corner (T2/T11/Corkscrew style)
    (  0,  65),   # blind/very sharp — emergency scrub
]

def laguna_corner_speed(sensor_min):
    """Return a target apex speed given the shortest forward sensor reading."""
    for threshold, speed in LAGUNA_CORNER_SPEEDS:
        if sensor_min >= threshold:
            return speed
    return 65  # absolute floor



def drive_laguna(c):

    """
    Laguna Seca-tuned drive function for TORCS/snakeoil.

    Changes vs previous version:
    1. Gear hysteresis: separate upshift/downshift thresholds per gear to
       eliminate 3↔4 and 4↔5 flickering. The car must fall well below the
       upshift speed before downshifting.
    2. Softer braking: divisors increased from 35/45 to 55/70, and the
       turning trigger for min_forward raised from 40 to 55 so braking
       begins earlier on approach, spreading deceleration over a longer
       distance at lower peak pressure.
    """
    global _recovery_counter

    S, R = c.S.d, c.R.d

    speed     = S['speedX']
    angle     = S['angle']
    track_pos = S['trackPos']
    stuck     = S.get('stucktimer', 0)
    wheels    = S.get('wheelSpinVel', [0, 0, 0, 0])
    track     = S.get('track', [100] * 19)

    # ─────────────────────────────────────────
    # RECOVERY
    # ─────────────────────────────────────────

    if _recovery_counter > 0:
        _recovery_counter -= 1
        R['gear']  = -1
        R['accel'] = 0.6
        R['brake'] = 0.0
        R['steer'] = clip(track_pos * 0.5, -1, 1)
        return

    if stuck > 50 or abs(track_pos) > 1.6:
        _recovery_counter = 80
        R['gear']  = -1
        R['accel'] = 0.6
        R['brake'] = 0.0
        R['steer'] = clip(track_pos * 0.5, -1, 1)
        return

    # ─────────────────────────────────────────
    # SENSOR EXTRACTION
    # Index layout (19 beams, 0=far right … 9=dead ahead … 18=far left)
    # ─────────────────────────────────────────

    front       = track[9]
    front_left  = track[10]
    front_right = track[8]
    diag_left   = track[12]   # ~30 ° left
    diag_right  = track[6]    # ~30 ° right


    left_converge  = diag_left < front_left      # left wall closing in
    right_converge = diag_right < front_right    # right wall closing in
    tightening     = left_converge or right_converge


    # Worst-case forward clearance
    min_forward = min(front, front_left, front_right)

    # ─────────────────────────────────────────
    # CORNER DETECTION
    #
    # min_forward threshold raised from 40 → 55 so the car begins
    # recognising the corner earlier, giving more distance to shed speed
    # gently rather than stamping the brakes at the last moment.
    # ─────────────────────────────────────────

    diag_diff = abs(diag_left - diag_right)
    turning   = diag_diff > 40 or min_forward < 55 or tightening

    # Corkscrew flag: large asymmetry + short front + high speed
    corkscrew_caution = (diag_diff > 60 and min_forward < 80 and speed > 100)

    # ─────────────────────────────────────────
    # TARGET SPEED
    # ─────────────────────────────────────────

    if turning:
        target_speed = laguna_corner_speed(min_forward)
        if tightening:
        # Corner is getting tighter — be more conservative
            target_speed = target_speed * 0.85   # ← 15% speed reduction
        if corkscrew_caution:
            target_speed = min(target_speed, 100)
    else:
        target_speed = 240

    # ─────────────────────────────────────────
    # BRAKING
    #
    # Divisors increased (35→55 for corkscrew, 45→70 for normal corners)
    # so that a given overspeed produces lower peak brake pressure but is
    # applied over a longer run-in, keeping total deceleration the same
    # while making the car feel much smoother through braking zones.
    # Minimum brake floor also slightly reduced (0.2→0.15, 0.1→0.08) so
    # the car doesn't lock up on mild approaches.
    # ─────────────────────────────────────────

    overspeed = speed - target_speed
    R['brake'] = 0.0

    if turning and overspeed > 0:
        if corkscrew_caution:
            # Softer but earlier for the Corkscrew
            R['brake'] = clip(overspeed / 55.0, 0.15, 0.85)
        else:
            # Gentle progressive braking — long distance, low peak pressure
            R['brake'] = clip(overspeed / 70.0, 0.08, 0.70)
        R['accel'] = 0.0

    elif front < 8 and speed > 20:
        # Emergency — wall dead ahead
        R['brake'] = 0.85
        R['accel'] = 0.0

    # ─────────────────────────────────────────
    # THROTTLE
    # ─────────────────────────────────────────

    if R['brake'] == 0.0:
        if speed < 5:
            R['accel'] = 1.0
        elif speed < target_speed:
            R['accel'] = clip((target_speed - speed) / target_speed + 0.4, 0.6, 1.0)
        else:
            R['accel'] = 0.2

    # ─────────────────────────────────────────
    # TRACTION CONTROL
    # ─────────────────────────────────────────

    rear_spin  = wheels[2] + wheels[3]
    front_spin = wheels[0] + wheels[1]
    if (rear_spin - front_spin) > 1.5:
        R['accel'] = max(0.0, R['accel'] - 0.15)

    # ─────────────────────────────────────────
    # STEERING
    # ─────────────────────────────────────────

    angle_gain  = 12.0
    center_gain = 0.35

    R['steer'] = clip(
        (angle * angle_gain / PI) - (track_pos * center_gain),
        -1, 1
    )

    # ─────────────────────────────────────────
    # GEARS — hysteresis to eliminate 3↔4 and 4↔5 flickering
    #
    # Strategy: upshift thresholds are higher than downshift thresholds
    # for the same gear boundary. The gap (≈8-13 km/h) means the car
    # must travel a meaningful distance in either direction before the
    # gearbox reacts, preventing oscillation when speed hovers near a
    # boundary under partial throttle or light braking.
    #
    # Upshift points  (speed must EXCEED to go up):
    #   1→2: 28    2→3: 58    3→4: 95    4→5: 138   5→6: 178
    # Downshift points (speed must FALL BELOW to go down):
    #   2→1: 20    3→2: 48    4→3: 82    5→4: 122   6→5: 162
    # ─────────────────────────────────────────

    current_gear = int(R.get('gear', 1))
    if current_gear < 1:
        current_gear = 1  # don't apply hysteresis during recovery

    if current_gear == 1:
        if   speed > 28:  R['gear'] = 2
        else:             R['gear'] = 1
    elif current_gear == 2:
        if   speed > 58:  R['gear'] = 3
        elif speed < 20:  R['gear'] = 1
        else:             R['gear'] = 2
    elif current_gear == 3:
        if   speed > 95:  R['gear'] = 4
        elif speed < 48:  R['gear'] = 2
        else:             R['gear'] = 3
    elif current_gear == 4:
        if   speed > 138: R['gear'] = 5
        elif speed < 82:  R['gear'] = 3
        else:             R['gear'] = 4
    elif current_gear == 5:
        if   speed > 178: R['gear'] = 6
        elif speed < 122: R['gear'] = 4
        else:             R['gear'] = 5
    else:  # gear 6
        if   speed < 162: R['gear'] = 5
        else:             R['gear'] = 6

    # ─────────────────────────────────────────
    # EDGE / WALL CORRECTION
    # ─────────────────────────────────────────

    if 0.85 < abs(track_pos) <= 1.6:
        R['steer'] = clip(-track_pos * 1.2, -1, 1)
        R['brake'] = 0.25
        R['accel'] = 0.0

    return

def laguna_net(network,client):
    for step in range(client.maxSteps):
        client.get_servers_input()

        if client.so is None:
            break

        S=client.S.d
        R=client.R.d

        if 'speedX' not in S:
            continue

        sensors=get_sensor_vector(S)

        network_action=network.feedForward(sensors)

        if np.any(np.isnan(network_action)) or np.any(np.isinf(network_action)):
            if np.any(np.isnan(network_action)):
                print("NaN present, corrupt output.")
            elif np.any(np.isinf(network_action)):
                print("Output blew up, corrupt output.")
            continue
        else:
            apply_action(R,network_action)

        client.respond_to_server()

if __name__ == "__main__":
    C=Client(t="laguna_seca",p=3001,e=10)

    network=model.Network([29,30,30,30,4],0.11)

    if os.path.exists('weights.json'):
        with open('weights.json','r') as f:
            data=json.load(f)
        network.weights=[np.array(w) for w in data['weights']]
        network.biases=[np.array(b) for b in data['biases']]
        network.trust=data.get('trust',0.1)

    laguna_net(network,C)