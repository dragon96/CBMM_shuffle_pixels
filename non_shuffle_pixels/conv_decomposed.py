'''
A Convolutional Network implementation example using TensorFlow library.
This example is using the MNIST database of handwritten digits
(http://yann.lecun.com/exdb/mnist/)
Author: Aymeric Damien
Project: https://github.com/aymericdamien/TensorFlow-Examples/
'''

from __future__ import print_function

import pixel_averaging
import sys
import time
import argparse

import tensorflow as tf

# Import MNIST data
from tensorflow.examples.tutorials.mnist import input_data
mnist = input_data.read_data_sets("/tmp/data/", one_hot=True)

# Parameters
learning_rate = 0.001
training_iters = 200000
batch_size = 128
display_step = 10


# Varied parameters
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--layer0_sigma", default=0.0)
sigma = float(parser.parse_args().layer0_sigma)
print("Sigma:", sigma)

# Aaron's add-ons
decomp_hash = pixel_averaging.generate_rand_grid()
decomp_mult = 2

# Network Parameters
n_rows = 28 * decomp_mult
n_cols = 28

n_input = n_rows * n_cols # MNIST data input (img shape: 28*28)
n_classes = 10 # MNIST total classes (0-9 digits)
dropout = 0.75 # Dropout, probability to keep units

# tf Graph input
x = tf.placeholder(tf.float32, [None, n_input])
y = tf.placeholder(tf.float32, [None, n_classes])
keep_prob = tf.placeholder(tf.float32) #dropout (keep probability)

# Create some wrappers for simplicity
def conv2d(x, W, b, strides1=1, strides2=None):
    # Conv2D wrapper, with bias and relu activation
    if strides2 is None:
        strides2 = strides1
    x = tf.nn.conv2d(x, W, strides=[1, strides1, strides2, 1], padding='SAME')
    x = tf.nn.bias_add(x, b)
    return tf.nn.relu(x)


def maxpool2d(x, k=2):
    # MaxPool2D wrapper
    return tf.nn.max_pool(x, ksize=[1, k, k, 1], strides=[1, k, k, 1],
                          padding='SAME')

# Create model
def conv_interleave(x, weights, biases, dropout):
    print()
    print("***********************")
    # Reshape input picture
    x = tf.reshape(x, shape=[-1, n_rows, n_cols, 1])

    # Interleave Convolution
    conv0 = conv2d(x, weights['wc0'], biases['bc0'], strides1=2, strides2=1)
    print("conv0", conv0.get_shape())

    # Convolution Layer
    conv1 = conv2d(conv0, weights['wc1'], biases['bc1'])
    # Max Pooling (down-sampling)
    conv1 = maxpool2d(conv1, k=2)
    print("conv1", conv1.get_shape())

    # Convolution Layer
    conv2 = conv2d(conv1, weights['wc2'], biases['bc2'])
    # Max Pooling (down-sampling)
    conv2 = maxpool2d(conv2, k=2)
    print("conv2", conv2.get_shape())

    # Fully connected layer
    # Reshape conv2 output to fit fully connected layer input
    fc1 = tf.reshape(conv2, [-1, weights['wd1'].get_shape().as_list()[0]])
    fc1 = tf.add(tf.matmul(fc1, weights['wd1']), biases['bd1'])
    fc1 = tf.nn.relu(fc1)
    print("fc1", fc1.get_shape())
    # Apply Dropout
    fc1 = tf.nn.dropout(fc1, dropout)

    # Output, class prediction
    out = tf.add(tf.matmul(fc1, weights['out']), biases['out'])
    print("out", out.get_shape())
    return out, weights['wc0']

def initialize_NN_and_train(sigma):
    # Store layers weight & bias
    weights = {
        # 2x1 conv, 1 input, 8 outputs (8 is arbitrary)
        'wc0': tf.Variable(tf.random_normal([2, 1, 1, 8], mean=1.0, stddev=sigma)),
        # 5x5 conv, 8 input, 32 outputs
        'wc1': tf.Variable(tf.random_normal([5, 5, 8, 32])),
        # 5x5 conv, 32 inputs, 64 outputs
        'wc2': tf.Variable(tf.random_normal([5, 5, 32, 64])),
        # fully connected, 7*7*64 inputs, 1024 outputs
        'wd1': tf.Variable(tf.random_normal([7*7*64, 1024])),
        # 1024 inputs, 10 outputs (class prediction)
        'out': tf.Variable(tf.random_normal([1024, n_classes]))
    }

    biases = {
        'bc0': tf.constant(0.0, shape=[8]),
        'bc1': tf.Variable(tf.random_normal([32])),
        'bc2': tf.Variable(tf.random_normal([64])),
        'bd1': tf.Variable(tf.random_normal([1024])),
        'out': tf.Variable(tf.random_normal([n_classes]))
    }

    # Construct model
    pred, w0 = conv_interleave(x, weights, biases, keep_prob)

    # Define loss and optimizer
    cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred, labels=y))
    optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost)

    # Evaluate model
    correct_pred = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

    # Initializing the variables
    init = tf.initialize_all_variables()

    # Launch the graph
    acc = 0
    testAcc = 0
    with tf.Session() as sess:
        sess.run(init)
        step = 1
        # Keep training until reach max iterations
        while step * batch_size < training_iters:
            batch_x, batch_y = mnist.train.next_batch(batch_size)
            test_x = mnist.test.images[:256]

            t0 = time.time()
            batch_x = pixel_averaging.batch_interleave(batch_x, decomp_hash)
            test_x = pixel_averaging.batch_interleave(test_x, decomp_hash)
            t1 = time.time()

            # Run optimization op (backprop)
            sess.run(optimizer, feed_dict={x: batch_x, y: batch_y,
                                           keep_prob: dropout})
            if step % display_step == 0:
                # Calculate batch loss and accuracy
                loss, acc = sess.run([cost, accuracy], feed_dict={x: batch_x,
                                                                  y: batch_y,
                                                                  keep_prob: 1.})
                layer0_weights = sess.run([w0])
                testAcc = sess.run(accuracy, feed_dict={x: test_x,
                                          y: mnist.test.labels[:256],
                                          keep_prob: 1.})
                print("Iter " + str(step*batch_size) + ", Training Accuracy= " + \
                      "{:.5f}".format(acc) + ", Test Acc.= "+ \
                      "{:.5f}".format(testAcc))
                #print("\t", layer0_weights)
            step += 1
        print("Optimization Finished! (Sigma, TrainAcc):", sigma, "\t", acc)
    return acc

def vary_sigmas():
    #weight0_stdevs = [0.0, 0.001, 0.01, 0.1, 1.0]
    weight0_stdevs = [0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0]
    accuracies = []
    for sigma in weight0_stdevs:
        acc = initialize_NN_and_train(sigma)
        accuracies.append(acc)
        print("\n\n\n ******************* \n\n\n")

    print("Sigmas:", weight0_stdevs)
    print("Training accuracies:", accuracies)
    print("Max_iters:", training_iters)


vary_sigmas()



'''

 - If the accuracy for interleave isn't as good as MNISTs, one guess for
    why is that the hash requires conv0 to find weights of [1 1] for it
    to recover the original MNIST image. This doesn't seem SGD-able
        - TODO: learn how to use Tensorboard to visualize the weights
        - 

'''
