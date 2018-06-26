#!/usr/bin/env python
#coding:utf8
import numpy
import argparse
import logging
import sys
import cPickle as pkl
from helper import Config
from helper import Dataset
from helper import DataLoader
from helper import prepare_data
from helper import test
import data_reader as dr
import codecs
import time
import tensorflow as tf
from model import SummaRuNNer

logging.basicConfig(level = logging.INFO, format = '%(asctime)s [INFO] %(message)s')

parser = argparse.ArgumentParser()

parser.add_argument('--sen_len', type=int, default=40)
parser.add_argument('--doc_len', type=int, default=90)
parser.add_argument('--train_file', type=str, default='./data/split_90/')
parser.add_argument('--validation_file', type=str, default='./data/split_90/valid')
parser.add_argument('--model_dir', type=str, default='./runs/1528870032/checkpoints/')
parser.add_argument('--epochs', type=int, default=15)
parser.add_argument('--hidden', type=int, default=110)
parser.add_argument('--lr', type=float, default=1e-4)

tf.flags.DEFINE_boolean("allow_soft_placement", True, "Allow device soft device placement")
tf.flags.DEFINE_boolean("log_device_placement", False, "Log placement of ops on devices")

FLAGS = tf.flags.FLAGS

args = parser.parse_args()
print("dc", args.doc_len)
max_sen_length = args.sen_len
max_doc_length = args.doc_len

logging.info('generate config')
word_vocab, word_tensors, max_doc_length, label_tensors = \
    dr.load_data(args.train_file, max_doc_length, max_sen_length)

batch_size = 1
time1 = time.time()
test_reader = dr.DataReader(word_tensors['test'], label_tensors['test'],
                         batch_size)
pretrained_embedding = dr.get_embed(word_vocab)
embedding_size = pretrained_embedding.shape[1]
config = Config(
        vocab_size = pretrained_embedding.shape[0],
        embedding_dim = pretrained_embedding.shape[1],
        position_size = 500,
        #position_dim = 50,
        position_dim = args.sen_len,
        word_input_size = 150,
        sent_input_size = 2 * args.hidden,
        word_GRU_hidden_units = args.hidden,
        sent_GRU_hidden_units = args.hidden,
        pretrained_embedding = pretrained_embedding)


with tf.Graph().as_default():
    session_conf = tf.ConfigProto(
      allow_soft_placement=FLAGS.allow_soft_placement,
      log_device_placement=FLAGS.log_device_placement)
    sess = tf.Session(config=session_conf)
    with sess.as_default():
        # Checkpoint directory. Tensorflow assumes this directory already exists so we need to create it
        Summa = SummaRuNNer(
            word_vocab.size, embedding_size, pretrained_embedding
            )
        '''
        with tf.variable_scope("Model"):
            #m = build_model(word_vocab)
            global_step = tf.Variable(0, dtype=tf.int32, name='global_step')
        '''
        init = tf.global_variables_initializer()
        sess.run(init)
        #saver = tf.train.Saver()
        saver = tf.train.import_meta_graph('./runs/1528870032/checkpoints/model-1024.meta')
        module_file = tf.train.latest_checkpoint("./runs/1528870032/" + 'checkpoints/')
        saver.restore(sess, module_file)
        #saver.restore(sess, FLAGS.load_model)
        #print('Loaded model from', FLAGS.load_model, 'saved at global step', global_step.eval())


        f = codecs.open(args.model_dir+"/scores" , "w", "utf-8")
        jk = 0
        for x, y in test_reader.iter():
            x = x[0]
            y = y[0]
            #print (x)
            y_ = sess.run(Summa.y_, feed_dict = {Summa.x: x, Summa.y:y})
            
            flag = 0
            max_len = 0
            for i,item in enumerate(x):
                #print item
                temp = 0
                for sub_item in item:
                    #print(type(int(sub_item)))
                    if sub_item > 0:
                        temp += 1
                        #print temp
                if temp == 0:
                    x = x[:i, :max_len]
                    y_ = y_[:i]
                    break
                if temp > max_len:
                    max_len = temp
            x = x[:, :max_len]
            #y_ = sess.run(Summa.y_, feed_dict = {Summa.x: x, Summa.y:y}
            for score in y_:
                #print(type(score.float))
                #score = score.float
                f.write(str(score[0][0]))
                f.write(" ")
                jk += 1
                #print("jk:", jk)
            f.write("\n")
        f.close()
