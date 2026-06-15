import mnist_loader
import model
training_data,validation_data,test_data=mnist_loader.load_data_wrapper()

net=model.Network([784,10])

net.weights = [w for w in net.weights]
net.biases = [b for b in net.biases]

sample_x, sample_y = list(test_data)[0]

try:
 net.SGD(training_data,30,10,0.1,test_data=test_data)
except KeyboardInterrupt:
 print("...........Exiting program.........")
