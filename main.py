#Model adapted from: https://github.com/Currie32/Chatbot-from-Movie-Dialogue/blob/master/Chatbot_Attention.py

#External Libraries
import numpy as np
import tensorflow as tf

#Supplemetary Files
import data_prep as data

print("--- Dependancies Loaded ---")

m_data, idx_q, idx_a = data.load_data()
(trX, trY), (teX, teY), (vaX, vaY) = data.split_dataset(idx_q, idx_a)

print("--- Data Loaded ---")

#Hyperparameters
epochs = 10000
batch_size = 64

x_len = trX.shape[-1]
y_len = trY.shape[-1]

layers = 3
xvocab_size = len(metadata['idx2w'])
yvocab_size = xvocab_size
emb_dim = 1024

alpha = 0.0001
p_keep = 0.75

#Input placeholders
enc_ip = [tf.placeholder(shape=[None,], dtype=tf.int64, name='ei_{}'.format(t)) for t in range(x_len)]
labels = [tf.placeholder(shape=[None,], dtype=tf.int64, name='ei_{}'.format(t)) for t in range(y_len)]
dec_ip = [tf.zeros_like(enc_ip[0], dtype=tf.int64, name='GO')] + labels[:-1]

#Keep Probability placeholder
keep_prob = tf.placeholder(tf.float32)

#Creating the Encoder
enc_cell = tf.nn.rnn_cell.LSTMCell(emb_dim)
dropout = tf.nn.rnn_cell.DropoutWrapper(cell, output_keep_prob = keep_prob)
enc_state = tf.nn.rnn_cell.MultiRNNCell([dropout]*layers)
 
#Building the Decoder and the Sequence to Sequence model 
with tf.variable_scope('decoder') as scope:
	decode_out, decode_states = tf.contrib.legacy_seq2seq.embedding_rnn_seq2seq(enc_ip, dec_ip, enc_state, xvocab_size, yvocab_size, emb_dim)
	scope.reuse_variables()
	decode_out_test, decode_states_test = tf.contrib.legacy_seq2seq.embedding_rnn_seq2seq(enc_ip, dec_ip, enc_state, xvocab_size, yvocab_size, emb_dim, feed_previous=True)
	
	loss_weights = [tf.ones_like(label, dtype=tf.float32) for label in labels]
	cost = tf.contrib.legacy_seq2seq.sequence_loss(decode_out, labels, loss_weights, yvocab_size)
	train_op = tf.train.AdamOptimizer(alpha).minimize(cost)
	
def get_feed(X, Y, k_prob):
	feed_dict = {enc_ip[t]:X[t] for t in range(x_len)}
	feed_dict.update({labels[t]: Y[t] for t in range(y_len)})
	feed_dict[keep_prob] = k_prob
	
	return feed_dict

def train_batch(sess, train_batch_gen):
	batchX, batchY = train_batch_get.__next__()
	feed_dict = get_feed(batchX, batchY, keep_prob=0.5)
	_, cost_v = sess.run([train_op, cost], feed_dict)
	
	return cost_v
	
def eval_step(sess, eval_batch_gen):
	batchX, batchY = eval_batch_gen.__next__()
	feed_dict = get_feed(batchX, batchY, keep_prob=1.0)
	cost_v, dec_op_v = sess.run([cost, decode_out_test], feed_dict)
	dec_op_v = np.array(dec_op_v).transpose([1,0,2])
	
	return cost_v, dec_op_v, batchX, batchY
	
def eval_batches(sess, eval_batch_gen, num_batches):
	costs = []
	
	for i in range(num_batches):
		cost_v, dec_op_v, batchX, batchY = eval_step(sess, eval_batch_gen)
		costs.append(cost_v)
		
	return np.mean(costs)
	
def train(tr_set, v_set, sess=None):
	saver = td.train.Saver()
	
	if not sess:
		sess = tf.Session()
		sess.run(tf.global_variables_initializer())
		
	for i in range(epochs)
		try:
			train_batch(sess, tr_set)
			if i an i% (epochs//100) == 0:
				saver.save(sess, 'ckpt/data/project.ckpt', global_steps=i)
				val_cost = eval_batches(sess, v_set, 16)
				
				print('\nModel saved to disk at iteration #{}'.format(i))
				print('val cost: {0:.6f}'.format(val_cost))
				
		except KeyboardInterrupt:
			print('Interrupted by user at iteration {}'.format(i))
			session = sess
			return sess
			