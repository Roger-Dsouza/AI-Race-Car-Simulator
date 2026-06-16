import socket
import sys
import getopt
import os
import time
import math
import model
PI= 3.14159265359

#Sample neural network, which can be adjusted for sensor inputs, and the outputs to calibrate car controls.
neural_network=model.Network([30,30,30])
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
    '''Draws a simple asciiart bar graph. Very handy for
    visualizing what's going on with the data.
    x= Value from sensor, mn= minimum plottable value,
    mx= maximum plottable value, w= width of plot in chars,
    c= the character to plot with.'''
    if not w: return '' # No width!
    x=clip(x,mn,mx)
    #The previous line is optimising tese two lines.
    """
    if x<mn: x= mn      # Clip to bounds.
    if x>mx: x= mx      # Clip to bounds.
    """
    
    #*****************
    tx= mx-mn # Total real units possible to show on graph.
    if tx<=0: return 'backwards' # Stupid bounds.
    upw= tx/float(w) # X Units per output char width.
    if upw<=0: return 'What?' # Don't let this happen.
    negpu, pospu, negnonpu, posnonpu= 0,0,0,0
    if mn < 0: # Then there is a negative part to graph.
        if x < 0: # And the plot is on the negative side.
            negpu= -x + min(0,mx)
            negnonpu= -mn + x
        else: # Plot is on pos. Neg side is empty.
            negnonpu= -mn + min(0,mx) # But still show some empty neg.
    if mx > 0: # There is a positive part to the graph
        if x > 0: # And the plot is on the positive side.
            pospu= x - max(0,mn)
            posnonpu= mx - x
        else: # Plot is on neg. Pos side is empty.
            posnonpu= mx - max(0,mn) # But still show some empty pos.
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
        self.maxEpisodes=1 # "Maximum number of learning episodes to perform"
        self.trackname= 'unknown'
        self.stage= 3 # 0=Warm-up, 1=Qualifying 2=Race, 3=unknown <Default=3>
        self.debug= False
        self.maxSteps= 100000  # 50steps/second
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
        '''Server's input is stored in a ServerState object'''
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
            elif not sockdata: # Empty?
                continue       # Try again.
            else:
                self.S.parse_server_str(sockdata)
                if self.debug:
                    sys.stderr.write("\x1b[2J\x1b[H") # Clear for steady output.
                    print(self.S)
                break # Can now return from this function.

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
        '''Parse the server string.'''
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
        '''Specialty output for useful ServerState monitoring.'''
        out= str()
        sensors= [ # Select the ones you want in the order you want them.
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
            if type(self.d.get(k)) is list: # Handle list type data.
                if k == 'track': # Nice display for track sensors.
                    strout= str()
                    raw_tsens= ['%.1f'%x for x in self.d['track']]
                    strout+= ' '.join(raw_tsens[:9])+'_'+raw_tsens[9]+'_'+' '.join(raw_tsens[10:])
                elif k == 'opponents': # Nice display for opponent sensors.
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
            else: # Not a list type of value.
                if k == 'gear': # This is redundant now since it's part of RPM.
                    gs= '_._._._._._._._._'
                    p= int(self.d['gear']) * 2 + 2  # Position
                    l= '%d'%self.d['gear'] # Label
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
                elif k == 'speedY': # This gets reversed for display to make sense.
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k]*-1,-25,25,50,'Y'))
                elif k == 'speedZ':
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k],-13,13,50,'Z'))
                elif k == 'z':
                    strout= '%6.3f %s' % (self.d[k], bargraph(self.d[k],.3,.5,50,'z'))
                elif k == 'trackPos': # This gets reversed for display to make sense.
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
                elif k == 'skid': # A sensible interpretation of wheel spin.
                    frontwheelradpersec= self.d['wheelSpinVel'][0]
                    skid= 0
                    if frontwheelradpersec:
                        skid= .5555555555*self.d['speedX']/frontwheelradpersec - .66124
                    strout= bargraph(skid,-.05,.4,50,'*')
                elif k == 'slip': # A sensible interpretation of wheel spin.
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
    '''What the driver is intending to do (i.e. send to the server).
    Composes something like this for the server:
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus 0)(meta 0) or
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus -90 -45 0 45 90)(meta 0)'''
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
        """There pretty much is never a reason to send the server
        something like (steer 9483.323). This comes up all the time
        and it's probably just more sensible to always clip it than to
        worry about when to. The "clip" command is still a snakeoil
        utility function, but it should be used only for non standard
        things or non obvious limits (limit the steering to the left,
        for example). For normal limits, simply don't worry about it."""
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
        '''Specialty output for useful monitoring of bot's effectors.'''
        out= str()
        od= self.d.copy()
        od.pop('gear','') # Not interesting.
        od.pop('meta','') # Not interesting.
        od.pop('focus','') # Not interesting. Yet.
        for k in sorted(od):
            if k == 'clutch' or k == 'brake' or k == 'accel':
                strout=''
                strout= '%6.3f %s' % (od[k], bargraph(od[k],0,1,50,k[0].upper()))
            elif k == 'steer': # Reverse the graph to make sense.
                strout= '%6.3f %s' % (od[k], bargraph(od[k]*-1,-1,1,50,'S'))
            else:
                strout= str(od[k])
            out+= "%s: %s\n" % (k,strout)
        return out

def destringify(s):
    '''makes a string into a value or a list of strings into a list of
    values (if possible)'''
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
    '''This is only an example. It will get around the track but the
    correct thing to do is write your own `drive()` function.'''
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
#                                                            #
#  Track character                                           #
#  • 2.238 miles, 11 turns, counter-clockwise               #
#  • Long uphill straight to T2 hairpin (hard braking)      #
#  • Technical infield: T3-T5 (slow, sequential)            #
#  • T6 fast left — carry speed                             #
#  • T8/8A Corkscrew: blind drop 59 ft, hard left/right     #
#  • T9-T10-T11 flowing back to start/finish straight       #
#                                                            #
#  Key philosophy:                                           #
#  • Full throttle on straights — no artificial speed cap    #
#  • Carry speed through fast sweepers (T6, T9)             #
#  • Brake hard and late for slow corners (T2, T11)         #
#  • Treat the Corkscrew with extreme caution (steep drop)  #
##############################################################

_recovery_counter = 0

# ─────────────────────────────────────────────────────────────
# LAGUNA SECA — CORNER PROFILE TABLE
# Maps approximate front-sensor reading → corner speed floor
# Lower sensor reading = tighter/closer corner ahead
# ─────────────────────────────────────────────────────────────
#
# Corner reference (Laguna Seca):
#   T2  hairpin:   ~65 km/h apex          (hardest brake)
#   T3-4 infield:  ~80 km/h
#   T5  exit kink: ~95 km/h
#   T6  fast left: ~145 km/h (barely lift)
#   T8  Corkscrew entry: ~100 km/h        (blind drop — caution)
#   T8A Corkscrew exit: ~90 km/h
#   T9  sweeper:   ~130 km/h
#   T10 fast right:~120 km/h
#   T11 hairpin:   ~70 km/h               (hard brake into straight)

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

    Key fixes over the original mgh():
    1. sharp_corner threshold raised from diag_diff>20 to diag_diff>40
       — the old value fired constantly, capping speed to ~80 km/h
       even on long straights. Laguna's fast sweepers (T6, T9) have
       naturally asymmetric diagonal readings and must NOT trigger
       heavy braking.
    2. Straight-line target speed set to 240 km/h (full throttle).
    3. Early-brake 'speed > 80' guard removed — it was the primary
       culprit preventing acceleration beyond 80 km/h.
    4. Corkscrew (T8/8A) caution: when front sensor is short AND
       diag_diff is large AND we are going fast, brake earlier and
       harder because the 59 ft drop punishes over-speed.
    5. Progressive braking divides by 45 (tighter than old 60) to
       actually scrub speed within Laguna's short braking zones.
    6. Duplicate __main__ block removed.
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
    # RECOVERY  (unchanged logic, reliable)
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
    wide_left   = track[14]   # ~60 ° left
    wide_right  = track[4]    # ~60 ° right

    # Worst-case forward clearance
    min_forward = min(front, front_left, front_right)

    # ─────────────────────────────────────────
    # CORNER DETECTION  ← BUG FIX #1
    #
    # OLD: diag_diff > 20  →  fires on every mild sweeper
    # NEW: diag_diff > 40  →  only genuine corners
    #      min_forward < 40 (was 50) so we enter braking mode
    #      only when the wall is actually close.
    #
    # Laguna specific: T6 and T9 are fast sweepers where the
    # car must carry 130-150 km/h. A threshold of 20 destroyed
    # those sectors by triggering repeated early-braking.
    # ─────────────────────────────────────────

    diag_diff    = abs(diag_left - diag_right)
    turning      = diag_diff > 40 or min_forward < 40
    wide_open = wide_left > 80 and wide_right > 80
    turning = (diag_diff > 40 or min_forward < 40) and not wide_open

    # Corkscrew flag: large asymmetry + short front + high speed
    # → extra-early braking to handle the 59 ft blind drop
    corkscrew_caution = (diag_diff > 60 and min_forward < 120 and speed > 90)

    # ─────────────────────────────────────────
    # TARGET SPEED
    # ─────────────────────────────────────────

    if turning:
        target_speed = laguna_corner_speed(min_forward)
        if corkscrew_caution:
            target_speed = min(target_speed, 100)  # never carry too much into T8
        target_speed = max(target_speed, 85) if min_forward > 25 else target_speed
    else:
        # Flat out — Laguna's main straight peaks ~230+ km/h for GT cars
        target_speed = 240

    # ─────────────────────────────────────────
    # BRAKING  ← BUG FIX #2 & #3
    #
    # OLD code had:
    #   elif sharp_corner and speed > 80:   ← stopped acceleration at 80
    #       anticipation = ...
    #       R['brake'] = anticipation        ← always braking above 80!
    #
    # NEW: only brake when actually overspeeding the corner target,
    # or when the Corkscrew caution flag fires.
    # ─────────────────────────────────────────

    overspeed = speed - target_speed
    R['brake'] = 0.0  # default: no brakes

    if turning and overspeed > 8:
        if corkscrew_caution:
            # Harder braking for the Corkscrew — short zone, big drop
            R['brake'] = clip(overspeed / 35.0, 0.2, 0.9)
        else:
            # Progressive braking — dividing by 45 keeps it crisp
            # but not snap-lock (Laguna's zones are short)
            R['brake'] = clip(overspeed / 45.0, 0.0, 0.75)
        R['accel'] = 0.0

    elif front < 8 and speed > 20:
        # Emergency — wall dead ahead
        R['brake'] = 0.85
        R['accel'] = 0.0

    # ─────────────────────────────────────────
    # THROTTLE — full aggression on straights
    # ─────────────────────────────────────────

    if R['brake'] == 0.0:
        if speed < 5:
            R['accel'] = 1.0
        elif speed < target_speed:
            # Always push hard — minimum 0.6 on partial throttle
            # so the car never bogs down on corner exits
            R['accel'] = clip((target_speed - speed) / target_speed + 0.4, 0.6, 1.0)
        else:
            R['accel'] = 0.2  # minimal coast once at target speed

    # ─────────────────────────────────────────
    # TRACTION CONTROL
    # Slightly tighter (>1.5 vs >2) — Laguna's elevation changes
    # make wheelspin more dangerous than on a flat track
    # ─────────────────────────────────────────

    rear_spin  = wheels[2] + wheels[3]
    front_spin = wheels[0] + wheels[1]
    if (rear_spin - front_spin) > 1.5:
        R['accel'] = max(0.0, R['accel'] - 0.15)

    # ─────────────────────────────────────────
    # STEERING
    # Slightly higher angle_gain (12 vs 10) for Laguna's
    # tight infield and the quick direction change at T8/8A
    # ─────────────────────────────────────────

    angle_gain  = 12.0
    center_gain = 0.35   # slightly less centering pull at high speed

    R['steer'] = clip(
        (angle * angle_gain / PI) - (track_pos * center_gain),
        -1, 1
    )

    # ─────────────────────────────────────────
    # GEARS — optimised for Laguna Seca speeds
    # T2 hairpin exits in 2nd, main straight peaks in 6th
    # Upshift points chosen to stay on the power curve
    # ─────────────────────────────────────────

    if   speed < 25:  R['gear'] = 1
    elif speed < 55:  R['gear'] = 2
    elif speed < 90:  R['gear'] = 3
    elif speed < 130: R['gear'] = 4
    elif speed < 175: R['gear'] = 5
    else:             R['gear'] = 6

    # ─────────────────────────────────────────
    # EDGE / WALL CORRECTION
    # ─────────────────────────────────────────

    if 0.85 < abs(track_pos) <= 1.6:
        R['steer'] = clip(-track_pos * 1.2, -1, 1)
        R['brake'] = 0.25
        R['accel'] = 0.0

# FIXED — add a second tier for deep gravel
    if 0.85 < abs(track_pos) <= 1.6:
        R['steer'] = clip(-track_pos * 1.2, -1, 1)
        R['brake'] = 0.25
        R['accel'] = 0.0
    elif abs(track_pos) > 1.6 and speed < 60:   # ← deep gravel, still moving
        R['steer'] = clip(-track_pos * 1.5, -1, 1)
        R['brake'] = 0.0
        R['accel'] = 0.8                          # ← power out, don't brake!
        R['gear']  = 1

    return


if __name__ == "__main__":
    C = Client(t='laguna_seca', p=3001)
    print("WeatherTech Raceway Laguna Seca driver loaded. Connecting...")
    for step in range(C.maxSteps, 0, -1):
        C.get_servers_input()
        drive_laguna(C)
        C.respond_to_server()
N = 0.20  # How strongly the car corrects its position toward the center of the track.
BRAKE_THRESHOLD = 0.9  # Angle threshold for braking. Lower values brake earlier.
GEAR_SPEEDS = [0, 20, 40, 80, 100, 180]  # Speed thresholds for gear shifting.
ENABLE_TRACTION_CONTROL = True  # Toggle traction control system.

# ================= HELPER FUNCTIONS =================
def calculate_steering(S):
    steer = (S['angle'] * STEER_GAIN / math.pi) - (S['trackPos'] * CENTERING_GAIN)
    return max(-1, min(1, steer))

def calculate_throttle(S, R):
    if S['speedX'] < TARGET_SPEED - (R['steer'] * 2.5):
        accel = min(1.0, R['accel'] + 0.4)
    else:
        accel = max(0.0, R['accel'] - 0.2)
    if S['speedX'] < 10:
        accel += 1 / (S['speedX'] + 0.1)
    return max(0.0, min(1.0, accel))

def apply_brakes(S):
    return 0.3 if abs(S['angle']) > BRAKE_THRESHOLD else 0.0

def shift_gears(S):
    gear = 1
    for i, speed in enumerate(GEAR_SPEEDS):
        if S['speedX'] > speed:
            gear = i + 1
    return min(gear, 6)

def traction_control(S, accel):
    if ENABLE_TRACTION_CONTROL:
        if ((S['wheelSpinVel'][2] + S['wheelSpinVel'][3]) - (S['wheelSpinVel'][0] + S['wheelSpinVel'][1])) > 2:
            accel -= 0.1
    return max(0.0, accel)

# ================= MAIN DRIVE FUNCTION =================

