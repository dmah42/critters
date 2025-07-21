#!/bin/bash

rm app.db
rm -rf migrations
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
