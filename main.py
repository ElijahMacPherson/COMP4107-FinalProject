#Model adapted from: https://github.com/Currie32/Chatbot-from-Movie-Dialogue/blob/master/Chatbot_Attention.py

#External Libraries
import numpy as np
import tensorflow as tf
import sys
from datetime import datetime
now = datetime.now()

#Supplemetary Files
import data_prep as data

print("--- Dependancies Loaded ---")

data_type = ""
if (len(sys.argv) == 2):
    data_type = sys.argv[1].lower()
    if (data_type == "raw"):
        print ("Loading raw data")
        m_data, idx_q, idx_a = data.load_data(True)
    elif (data_type == "clean"):
        print ("Loading clean data")
        m_data, idx_q, idx_a = data.load_data(False)
    else:
        sys.exit("Error, incorrect command line arguments. Please supply either 'raw' or 'clean' for which dataset should be used.")
else:
    sys.exit("Error, incorrect command line arguments. Please supply either 'raw' or 'clean' for which dataset should be used.")

(trX, trY), (teX, teY), (vaX, vaY) = data.split_dataset(idx_q, idx_a)

print("--- Data Loaded ---")

#Hyperparameters
epochs = 500
batch_size = 64
alpha = 0.001
p_keep = 0.75

x_len = trX.shape[-1]
y_len = trY.shape[-1]

layers = 3
xvocab_size = len(m_data['idx2w'])
yvocab_size = xvocab_size
emb_dim = 1024

#Input placeholders
enc_ip = [tf.placeholder(shape=[None,], dtype=tf.int64, name='ei_{}'.format(t)) for t in range(x_len)]
labels = [tf.placeholder(shape=[None,], dtype=tf.int64, name='ei_{}'.format(t)) for t in range(y_len)]
dec_ip = [tf.zeros_like(enc_ip[0], dtype=tf.int64, name='GO')] + labels[:-1]

#Keep Probability placeholder
keep_prob = tf.placeholder(tf.float32)

#Creating the Encoder
enc_cell = tf.nn.rnn_cell.LSTMCell(emb_dim)
dropout = tf.nn.rnn_cell.DropoutWrapper(enc_cell, output_keep_prob = keep_prob)
enc_state = tf.nn.rnn_cell.MultiRNNCell([dropout]*layers)

#Building the Decoder and the Sequence to Sequence model
with tf.variable_scope('decoder') as scope:
    setattr(tf.contrib.rnn.MultiRNNCell, '__deepcopy__', lambda self, _: self)
    decode_out, decode_states = tf.contrib.legacy_seq2seq.embedding_rnn_seq2seq(enc_ip, dec_ip, enc_state, xvocab_size, yvocab_size, emb_dim)
    scope.reuse_variables()
    decode_out_test, decode_states_test = tf.contrib.legacy_seq2seq.embedding_rnn_seq2seq(enc_ip, dec_ip, enc_state, xvocab_size, yvocab_size, emb_dim, feed_previous=True)


    loss_weights = [tf.ones_like(label, dtype=tf.float32) for label in labels]
    cost = tf.contrib.legacy_seq2seq.sequence_loss(decode_out, labels, loss_weights, yvocab_size)
    train_op = tf.train.GradientDescentOptimizer(alpha).minimize(cost)

    tf.summary.scalar("cost", cost) #For TensorBoard

#sets up the feed_dictionary
def get_feed(X, Y, k_prob):
    feed_dict = {enc_ip[t]:X[t] for t in range(x_len)}
    feed_dict.update({labels[t]: Y[t] for t in range(y_len)})
    feed_dict[keep_prob] = k_prob

    return feed_dict

#Trains the model on one batch
def train_batch(sess, train_batch_gen, merged):
    batchX, batchY = train_batch_gen.__next__()
    feed_dict = get_feed(batchX, batchY, k_prob=0.5)
    summary, _, cost_v = sess.run([merged, train_op, cost], feed_dict)

    return cost_v, summary

#evaluates an individual batch
def eval_step(sess, eval_batch_gen):
    batchX, batchY = eval_batch_gen.__next__()
    feed_dict = get_feed(batchX, batchY, k_prob=1.0)
    cost_v, dec_op_v = sess.run([cost, decode_out_test], feed_dict)
    dec_op_v = np.array(dec_op_v).transpose([1,0,2])

    return cost_v, dec_op_v, batchX, batchY

#evaluates the batches
def eval_batches(sess, eval_batch_gen, num_batches):
    costs = []

    for i in range(num_batches):
        cost_v, dec_op_v, batchX, batchY = eval_step(sess, eval_batch_gen)
        costs.append(cost_v)

    return np.mean(costs)

#Trains the model on a training set and a valid set for confirmation
def train(tr_set, v_set, sess=None):
    saver = tf.train.Saver()

    if not sess:
        sess = tf.Session()
        sess.run(tf.global_variables_initializer())
    merged = tf.summary.merge_all()
    writer = tf.summary.FileWriter("./data/logs/" + now.strftime("%Y-%m-%d_%H-%M-%S"), sess.graph)

    for i in range(epochs):
        try:
            _, summary = train_batch(sess, tr_set, merged)
            writer.add_summary(summary, i)
            print('\nIteration: {}'.format(i))
            if (i+1) % 50 == 0 or epochs < 100:
                saver.save(sess, 'data/ckpt/project', global_step=i)
                val_cost = eval_batches(sess, v_set, 16)

                print('\nModel saved to disk at iteration #{}'.format(i+1))
                print('val cost: {0:.6f}'.format(val_cost))

        except KeyboardInterrupt:
            print('Interrupted by user at iteration {}'.format(i))
            session = sess
            return sess

#This functions should be used for testing user input
def predict(sess, X):
    feed_dict = {enc_ip[t]: X[t] for t in range(x_len)}
    feed_dict[keep_prob] = 1

    dec_op_v = sess.run(decode_out_test, feed_dict)
    dec_op_v = np.array(dec_op_v).transpose([1,0,2])

    return np.argmax(dec_op_v, axis=2)


def restore_last_session(data_type):
    saver = tf.train.Saver()
    sess = tf.Session()

    # get checkpoint state
    if (data_type == "raw"):
        ckpt = tf.train.get_checkpoint_state('data/ckpt/raw_ckpt')
    elif (data_type == "clean"):
        ckpt = tf.train.get_checkpoint_state('data/ckpt/clean_ckpt')
        
    # restore session
    if ckpt and ckpt.model_checkpoint_path:
        saver.restore(sess, ckpt.model_checkpoint_path)
    else:
        sys.exit("An error occured when trying to load a previous checkpoint")

    return sess

#Getting batches to train with
val_batch_gen = data.rand_batch_gen(vaX, vaY, batch_size)
train_batch_gen = data.rand_batch_gen(trX, trY, batch_size)

#Training
sess = train(train_batch_gen, val_batch_gen)
#sess = restore_last_session(data_type)
