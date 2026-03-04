#!/bin/bash

num_games=10

for i in $(seq 1 $num_games)
do
   python3 eval_raw_network.py > data/eval_raw_network/result_$i.txt
done