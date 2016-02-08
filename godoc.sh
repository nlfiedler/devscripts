#!/bin/sh
#
# Start the godoc server and open the URL in the browser.
#
PORT='6060'
godoc -http=:${PORT} &
open http://localhost:${PORT}
