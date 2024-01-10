"""
This is the test flask script to run in the devenv:

```
flask --app flask-hello-world run
```

OR  

```
python -m flask --app flask-hello-world run
```
"""
from flask import Flask

print(__name__)
app = Flask(__name__)

@app.route("/")
def hello_world():
	return "<p>Hello, World!</p>"
	
	
"""
Added this main for easier self-service run

```
python flask-hello-world.py
```

There are some pro/con(s) for using one launcher versus the other
as documented in [How to Run a Flask Application](https://www.twilio.com/blog/how-run-flask-application)
"""
if "__main__" == __name__:
	app.run(host="0.0.0.0", port="8080")
	
	
