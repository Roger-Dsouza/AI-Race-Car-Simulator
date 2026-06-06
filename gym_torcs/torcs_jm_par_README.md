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


Client Class:
    Attributes:
        - vision:
        - host: The site where the client is hosted at.
        - port: The port where the client will be posted at.
        - stage: All three stages included.
        - debug: Debug mode enabled or not.
         


        