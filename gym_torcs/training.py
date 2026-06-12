from math import *

def sigmoid(input,weights,bias):
    total=0
    for a in range(len(weights)):
        total+=input[a]*weights[a]

    total-=bias

    return 1/(1+exp(total*-1))


while True:
    num=input("Enter a digit between 0 and 9:")
    digits=[0,0,0,0,0,0,0,0,0,0]
    digits[int(num)]=1
    one_weights=[-5,5,-5,5,5,5,-5,5,-5,5]
    two_weights=[-5,-5,5,5,-5,-5,5,5,-5,-5]
    three_weights=[-5,-5,-5,-5,5,5,5,5,-5,-5]
    four_weights=[-5,-5,-5,-5,-5,-5,-5,-5,5,5]

    one_bit=sigmoid(digits,one_weights,0)
    two_bit=sigmoid(digits,two_weights,0)
    three_bit=sigmoid(digits,three_weights,0)
    four_bit=sigmoid(digits,four_weights,0)

    rep=[four_bit,three_bit,two_bit,one_bit]
    for a in range(len(rep)):
        if rep[a]>=0.99:
            rep[a]=1
        elif rep[a]<=0.01:
            rep[a]=0


    print(f" {rep[0]} {rep[1]} {rep[2]} {rep[3]} ")






