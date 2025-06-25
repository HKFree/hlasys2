#!/bin/sh

echo "=== HlaSys v2 for hkfree.org ==="
echo "====== made by OndraLhota ======"
echo "version ${HLASYS2_VERSION}"

if [ ! -f /hlasys2/instance/hlasys2.sqlite ]
then
    echo "Database does not exist. Initializing it with empty schema."
    flask init-db
else 
    echo "Database exists, launching app."
fi

waitress-serve --listen=*:5000 --call 'hlasys2_app:create_app'
