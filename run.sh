#!/bin/bash

project=$1
for d in $(sort -u sub.domain.txt); do
    python3 main.py ${d} ${project} &
done
