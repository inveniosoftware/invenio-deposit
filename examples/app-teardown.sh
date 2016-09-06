#!/bin/sh

DIR=`dirname "$0"`

cd $DIR
export FLASK_APP=app.py

# clean environment
[ -e "$DIR/instance" ] && rm $DIR/instance -Rf
[ -h "$DIR/static/.DS_Store" ] && rm $DIR/static/.DS_Store -Rf
[ -e "$DIR/static/.webassets-cache" ] && rm $DIR/static/.webassets-cache -Rf
[ -e "$DIR/static/admin" ] && rm $DIR/static/admin -Rf
[ -e "$DIR/static/bootstrap" ] && rm $DIR/static/bootstrap -Rf
[ -e "$DIR/static/gen" ] && rm $DIR/static/gen -Rf
[ -e "$DIR/static/images" ] && rm $DIR/static/images -Rf
[ -e "$DIR/static/js" ] && rm $DIR/static/js -Rf
[ -e "$DIR/static/json" ] && rm $DIR/static/json -Rf
[ -e "$DIR/static/node_modules" ] && rm $DIR/static/node_modules -Rf
[ -e "$DIR/static/package.json" ] && rm $DIR/static/package.json -Rf
[ -e "$DIR/static/scss" ] && rm $DIR/static/scss -Rf
[ -e "$DIR/static/templates/invenio_deposit" ] && rm $DIR/static/templates/invenio_deposit -Rf
[ -e "$DIR/static/templates/invenio_search_ui" ] && rm $DIR/static/templates/invenio_search_ui -Rf
[ -e "$DIR/static/vendor" ] && rm $DIR/static/vendor -Rf

# Delete the database
flask db drop --yes-i-know

# Delete indices
flask index destroy --yes-i-know --force
