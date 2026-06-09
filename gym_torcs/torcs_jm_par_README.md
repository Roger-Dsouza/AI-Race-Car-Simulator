Modules Imported:
1. socket: Interacts with network sockets and enables TCP/IP communication.
2. sys: Enables access to various system-related functionality for example command-line arguments passed through the function call.
3. getopt: Standard module that allows options to be parsed and read from command-line arguments.
4. os: Provides access to operating system-specific functionality (I/O operations).
5. time: Provides functions for managin program's execution time.


Set Constants:
Pi.
data_size.


Run Options:
1. --host, -H <host>: TORCS server host.
2. --port, -p <port>: TORCS port.
3. --id, -i <id>: Provides an id for the server.
4. --steps, -m <n>: Maximum number of simulation steps where 1 second is around 50 steps.
5. --episodes, -e <n>: Maximum learning episodes.
6. --track, -t <name>: Name for the track.
7. --stage, -s <n>: 0=warm-u, 1=qualifying,2=race,3=unknown
8. --debug, -d: Output full telemetry.
9. --help, -h: Help option.
10. --version, -: Shows current version.

The string usage specifies the script being executed and the ophelp consists of the response to the input flag which will help execute the information response.


Functions:
1. clip(v,lo,hi): Returns v if lo<v<hi. Otherwise if v<=lo, v is returned. Else, hi is returned.

2. bargraph(x,mn,mx,w,c="X"): Returns a bar graph where:
  mn=Minimum plottable value.
  x=Value from sensor.
  mx: Maximum plottable value.
  w=Width of plot in chars.
  c=Character to plot with.


    Can return 'backwards' if mx<mn. 'What' if negative units are needed to be plotted.

    The function first paritions the range between mn and mx into units of width w.
    Then it checks whether x is positive or negative. Then from either zero or the smaller upper bound, the function draws a streak of X's from that point to the unit which contains x. The rest of the units are covered with _ making a bar-graph.

    Default value for the streak is 'X', which can be changed by passing in the required parameter.

    Example print(bargraph(25,0,30,5,c="*"))
    => [*****_]


Client() Class:
    Attributes:
        - vision:
        - host: The site where the client is hosted at.
        - port: The port where the client will be posted at.
        - sid: Specific id- in this case, 'src'.
        - maxEpisodes: Maximum number of learning episodes to perform.
        - trackname: Set during the race initiation.
        - stage: All three stages included.
        - debug: Debug mode enabled or not.
        - maxSteps: The upper bound of steps that the client will take.
        - parse_the_command_line(): An inherently run command which first gets a tuple for the options and their corresponding arguments. After error checking, it checks the corresponding flags and runs the usage script for each option.
        - Chain of Conditionals:
        [H,p,i,e,t,s,d]: Assigns the corresponding attribute to the value present.
        - Sets its S attribute to the ServerState() function.
        - Sets its R attribute to the DriverAction() function.
        - Implements the setup_connection() function.


    Methods:
    - setup_connection(): 
      - Sets up the socket with the AF_INET. This creates the IPv4 addressing convention.
      - Also creates a Datagram socket which uses the UDP protocol. Which allows messages to be sent via system similiar to a mailing system with no need for simultaneous connection.
      - After returning an error message if unable to create a socket. It sets out a time out option of 1 second.

      Sets the number of times it fails to connect to be 5.

      Then initiates a continuous loop such that during each iteration:
        1. Creates a string that functions as a unique identifier tag.
        2. Tries to encode the string and sends it to the host on the port under the object's socket. Exits if an error message is detected.
        3. Creates a string variable that accepts incoming socket data.
        4. Tries to recieve messages from the socket and the address of the incoming message.
        5. Decodes the socket data under the utf-8 convention. If an error message comes up instead. It tries to re-establish a connection for five more times. If it fails, there is a message demanding a relaunch of torcs. Aborting torcs and then reports whether vision attribute was present in the first place. Then restarts the process after 1 second, and resetting the number of tries.
        6. If the socket data contains the '***identified***' string, then confirms connection is established.

    - parse_the_command_line():
      - Gets the tuple containing opts which is a tuple containing the flag and its singly associated value. The args is the value passed into the function directly.
      - After returning an error in case it cannot correctly sort the incoming input. It parses through the options stored in opts. 
        1. After checking the first part of the options tuple, it will output the appropriate usage output.
        2. If a wrong parameter is passed. It will point out the appropriate area where the parameter was wrongly passed. If the length of the arguments is greater than 0, it will return that the input is flawed. As no input is meant to be passed into the client function.

    - get_servers_input():
      - In a continuous loop:
        - Gets the socket data and address and decodes the data in utf-8 format. If error, returns '. '.
        - If the string "***identified***" is in socket data prints that it is connected.
        - If "***shutdown***" is identified, prints out that the server has stopped the race at the port and highlights which position you were in.
        - "***restart***" restarts the race.
        - It then performs a check that there is data in the sockdata variable.
        - Otherwise it just parses the sockdata string and writes out the data out clearly if debug mode is enabled.

    respond_to_server():
      - First checks that a socket is created.
      - Then converts the output of the DriverState function into a String encoding.
      - Finally sends the message as raw bytes to the location of the host which is in a specific port.

      - If the process throws out an error message, function states that it couldn't send out the message. 
      - The process prints out a human readable version of the text if debug mode is enabled.

  shutdown():
      - Firstly after checking that socket creation was successful, it then closes the socket and then signals it has done so.


ServerState() Class:
  Attributes:
    serverstr: A string variable. Which contains information for the state of the server which will be updated to its dictionary variable.
    d: A dictionary variable. Which is sued to store the conetents of the server string for future reference.

  Methods:
    1. parse_server_str():
      First, it removes the unneccesary whitespaces at beginning and at the end, then returns everything except the last character.
      Then, it further removes any more whitespaces and then removes the brackets '()'. then splits the string on the basis of ')('.
      Finally, it iterates through each of the items in the list and splits the string on the basis of whitespaces, and each item in the list is then removed from the string encoding present.

      2. __repr__():
        returns a description of itself in a human-readable format. (Don't know what's up with the out string description).

      3. fancyout():
        Specifies the output for writing out the state of the server which will be useful in debugging. States the sensor parameters.
        Then for each:
          First checks if the type is a list: There are only two particular sensors which are of a list type- 'track','opponents'.
            1. If the sensor type is the track sensors: then it will strip the digits of the particular sensor track.
            2. If the sensor type is the opponents sensor: It calculates the distance between the car and the nearest opponent. It simplifies it down into a more tangible value to gauge distance. Adding arrows to signify the direction the opponent is at.
            3. If it is another type of sensor, it just lists the values joined by a comma.

            For the non list sensors:
              1. If the sensor type is gear sensor: (Now gear is part of RPM):
                  It lists out the total gears present.
                  Then finds the position and converts it into the appropriate gear location.
                  Then it collects the label at that position, taking care that the -1 and 0 label correspond to Reverse and Neutral position.

                  Finally, the strout string focuses on the gear specifically, inserting the gear as highlighted out of the others.
              2. 'damage' returns the damage output to six signifcant giures and a bargraph highlighting the scale of the damage with the scale in '~'.
              3. 'Fuel': Returns the same specification. The only difference is that the scale if of 'f'.
              4. 'speedX': Shows the speed in the x-direction with the bargraph. With 'R' if it the speed is less than zero.
              5. 'SpeedY': Similiar setup to speedX. Only that the bargraph tracker is 'Y'.
              6. 'speedZ': Similiar setup to speedX. Only that the bargraph tracker is 'Z'.
              7. trackPos: Renders the position of the car by '<' or '>' arrows.
              8. stucktimer: If the sensor variable has a value, it is displayed in a bar graph, otherwise states that it is not stuck.
              9. rpm: Selects the gear option and then displays the rpm in a bar-graph.
              10. angle: Fetches the angle in radians and then displays the angle in degrees, radians, and a visual display of the angle.
              11. skid: Fetches the rotation of the front wheel, if there is a value, it is then used to calculate and display the magnitude of the skid.
              12. slip: Fetches the rotation of the front wheel, then if there is a tangible value present, it factors in the contribution of the other wheels to calculate the slip of the vehicle and display its magnitude.

              If the sensor is not any of these categories, it is just encoded in a string format. 

              Finally, all of the bar-graphs throughout the function are added to the strout variable and are then returned out of the function as a pair of sensor and the corresponding output.

DriverAction() class:
  Attributes:
    - actionstr: Represents the action currently being performed by the driver.
    - d: A dictionary containing the current state of the driver and with the goal of the methods to modify them.

  Methods: 
  1. clip_to_limits():
    Clips each value in the dictionary to the limits to prevent anomalous data being sent to the server.

  2. __repr__():
    Provides a representation of the DriverAction after first clipping to the limits.

  3. fancyout():
    Provides a more readable output for the bot's effectiveness. 
    Removes the gear, meta and focus entries. Then displays the mangitueds of the values present in the clutch, brake and accel entries. For any other values, it is just encoded in a string format.



destringify(): Turns the string into a value or an array of strings into an array of values wherever possible.


drive_example(): 
  











    
      

         


        