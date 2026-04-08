#!/bin/bash

echo "Executing create_pkg.sh..."

cd $path_cwd/src

# Installing python dependencies...
FILE=$path_cwd/requirements.txt
echo "Requirements file: $FILE"
cat $FILE
if [ -f "$FILE" ]; then
  echo "Installing dependencies into src/ ..."
  pip install -r "$FILE" -t . --upgrade
else
  echo "Error: requirements.txt does not exist!"
fi

echo "Finished script execution!"