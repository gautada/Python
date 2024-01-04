#!/bin/sh

# This script should find/locate a python script and run it passing all values.

# Check that the environment is active
# This script should not be called directly but should be called from a symlink, the symlink
#  provides the name of the script to call
# Should pass all parameters to the script
# locate the python script by first searching the public folder then private folder.

BASE_SCRIPT="$(basename "$0")"
if [ "$BASE_SCRIPT" = "run-python.sh" ]; then
 echo "[ERROR] Script should be called through a symlink names for the python script to run"
 exit 1
fi

BASE_PATH="$HOME/Workspace/Python"
PUBLIC_PATH="$BASE_PATH/public"
PRIVATE_PATH="$BASE_PATH/private"

SCRIPT="$BASE_SCRIPT.py"
PUBLIC_SCRIPT="$PUBLIC_PATH/$SCRIPT"
PRIVATE_SCRIPT="$PRIVATE_PATH/$SCRIPT"

# echo $PUBLIC_SCRIPT

if [ -f "$PUBLIC_SCRIPT" ]; then
 SCRIPT="$PUBLIC_SCRIPT"
else
 if [ -f "$PRIVATE_SCRIPT" ]; then
  SCRIPT="$PRIVATE_SCRIPT"
 else
  echo "[ERROR] Script ($SCRIPT) not found."
  exit 2
 fi
fi

# echo $SCRIPT
RTN=0 
if [ -f "$SCRIPT" ]; then
 RUN="$(which python) $SCRIPT $@"
 # echo "RUN: $RUN"
 eval "$RUN"
 RTN=$?
fi

exit $RTN
