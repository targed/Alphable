#!/bin/bash

num_games=10

for i in $(seq 1 $num_games)
do
   python3 debug_brain.py > data/debug_brain/result_$i.txt
done