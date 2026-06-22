import random
import numpy as np

def sigmoid(i):
    return 1.0/(1.0+np.exp(-i))


def sigmoid_prime(z):
    """Derivative of the sigmoid function."""
    return sigmoid(z)*(1-sigmoid(z))
class Network(object):

    def __init__(self,sizes,trust=0.1):
        self.num_layers=len(sizes)
        self.sizes=sizes
        self.trust=trust
        self.biases=[np.random.randn(y,1) for y in sizes[1:]]
        self.weights=[np.random.randn(y,x) for x,y in zip(sizes[:-1],sizes[1:])]

   
    
    def feedForward(self,a): 
        "Norml sigmoid for the input and hidden layers."
        for b,w in zip(self.biases[:-1],self.weights[:-1]):
            a=sigmoid(np.clip((np.dot(w,a)+b),-500,500))
        
        "The outputs encounter different operations for different sections, as thye control different parts respectively."
        z_out=np.dot(self.weights[-1],a)+self.biases[-1]
        z_out=np.clip(z_out,-500,500)

        output=np.array([
            np.tanh(z_out[0]),
            sigmoid(z_out[1]),
            sigmoid(z_out[2]),
            sigmoid(z_out[3])



        ]).reshape(-1,1)
        
        return output

    def SGD(self,training_data,epochs,mini_batch_size,eta,test_data=None):
        """ Trains the neural network by using stochastic gradient descent on a 
        sample of the data."""
        if test_data: n_test=len(test_data)
        n=len(training_data)

        for j in range(epochs):
            random.shuffle(training_data)
            mini_batches=[
                training_data[k:k+mini_batch_size]
                for k in range(0,n,mini_batch_size)]
            
            for mini in mini_batches:
                self.update_mini_batch(mini,eta,1)

            if test_data:
                print ("Epoch {0}: {1} / {2}".format(j, self.evaluate(test_data), n_test))
            else:
                print("Epoch {0} complete".format(j))

    def update_mini_batch(self,mini_batch,eta,steer_grad_clip=None):
        """
            Updates network's weights and biases by applying gradient descent using backpropogation
            on a single mini batch.
        
        """
        nabla_b=[np.zeros(b.shape) for b in self.biases]
        nabla_w=[np.zeros(w.shape) for w in self.weights]

        for x,y in mini_batch:
            delta_nabla_b,delta_nabla_w=self.backprop(x,y)
            nabla_b=[nb+dnb for nb,dnb in zip(nabla_b,delta_nabla_b)]
            nabla_w=[nw+dnw for nw,dnw in zip(nabla_w,delta_nabla_w)]


        steer_grad_norm=np.linalg.norm(nabla_w[-1][0])
        print(f"Norm:{steer_grad_norm:.4f}")

        if steer_grad_clip is not None:
            np.clip(nabla_w[-1][0],-steer_grad_clip,steer_grad_clip,out=nabla_w[-1][0])
            np.clip(nabla_b[-1][0],-steer_grad_clip,steer_grad_clip,out=nabla_b[-1][0])



        self.weights=[w-(eta/len(mini_batch))*nw
                      for w,nw in zip(self.weights,nabla_w)]
        self.biases=[b-(eta/len(mini_batch))*nb for b,nb in zip(self.biases,nabla_b)]

    def backprop(self,x,y):
        """Returns the gradient operator representing the gradient of the cost function."""

        nabla_b=[np.zeros(b.shape) for b in self.biases]
        nabla_w=[np.zeros(w.shape) for w in self.weights]

        #Feed-Forward.
        activation=x
        activations=[x]
        zs=[]
        for b,w in zip(self.biases[:-1],self.weights[:-1]):
            z=np.dot(w,activation)+b
            zs.append(z)
            activation=sigmoid(z)
            activations.append(activation)

        z_out=np.dot(self.weights[-1],activation)+self.biases[-1]
        zs.append(z_out)

        out_activation=np.zeros_like(z_out)
        out_activation[0]=np.tanh(z_out[0])
        out_activation[1]=sigmoid(z_out[1])
        out_activation[2]=sigmoid(z_out[2])
        out_activation[3]=sigmoid(z_out[3])
        activations.append(out_activation)


        #Backward Pass for output activations.
        sp=np.zeros_like(z_out)
        sp[0]=1.0-out_activation[0]**2
        sp[1]=out_activation[1]*(1.0-out_activation[1])
        sp[2]=out_activation[2]*(1.0-out_activation[2])
        sp[3]=out_activation[3]*(1.0-out_activation[3])



        delta=self.cost_derivative(activations[-1],y)*sp
               
        nabla_b[-1]=delta
        nabla_w[-1]=np.dot(delta,activations[-2].transpose())

        #the variable l in the loop below is used a little
        # differently to the notation in Chapter 2 of the book.  Here,
        # l = 1 means the last layer of neurons, l = 2 is the
        # second-last layer, and so on.  It's a renumbering of the
        # scheme in the book, used here to take advantage of the fact
        # that Python can use negative indices in lists.

        for l in range(2,self.num_layers):
            z=zs[-l]
            sp=sigmoid_prime(z)
            delta=np.dot(self.weights[-l+1].transpose(),delta)*sp
            nabla_b[-l]=delta
            nabla_w[-l]=np.dot(delta,activations[-l-1].transpose())

        return (nabla_b,nabla_w)
    
    def evaluate(self,test_data):
       l=len(test_data)

       per_output_sq_error=np.zeros((4,1))
       for x,y in test_data:
           prediction=self.feedForward(x)
           error=prediction-y
           per_output_sq_error+=error*error
       per_output_mse=(per_output_sq_error/l).flatten()
       the_list=per_output_mse.tolist()
       total_mse=float(np.mean(per_output_mse))

       print(
           f"""
                mse_total:{total_mse}
                mse_per_output:[{the_list[0]:.3f},{the_list[1]:.3f},{the_list[2]:.3f},{the_list[3]:.3f}]
                n:{l}


           """



       )
    
    def cost_derivative(self,output_activations,y):
        return (output_activations-y)
    



