#!/bin/bash

num_games=10

for i in $(seq 1 $num_games)
do
   python watch_bot.py > results/result_$i.txt
done