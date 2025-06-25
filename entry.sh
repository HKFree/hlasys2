#!/bin/sh

echo "Launching hlasys2."

if [ ! -f /hlasys2/hlasys2_app/instance/hlasys2.sqlite ]
then
    echo "Database does not exist. Initializing it with empty schema."
    flask init-db
else 
    echo "Database exists, launching app."
fi


flask run --host 0.0.0.0
