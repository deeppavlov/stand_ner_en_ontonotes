#!/bin/bash
echo downloading model files.. &&
wget http://lnsigo.mipt.ru/export/deepreply_data/stand_ner_en_ontonotes/model.tar.gz &&
tar -zxvf model.tar.gz &&
rm model.tar.gz &&
echo download successful &&
echo downloading embedding files.. &&
wget -P ./model http://lnsigo.mipt.ru/export/embeddings/glove.6B.100d.txt &&
echo download successful