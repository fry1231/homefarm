import json
from typing import Optional, List, Any, Dict
from fastapi import FastAPI, HTTPException, Body, Request, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from server.config import CONFIG
from server.models import States
import uvicorn
from datetime import datetime


app = FastAPI()


working_minutes = []
five = 0
for i in range(60):
    if five < 5:
        working_minutes.append(i)
    if i % 15 == 0:
        five = -1
    five += 1


working_hours = [i for i in range(8, 24)] + [0]


@app.get("/")
def read_root():
    with open("./db/states.json") as f:
        states = json.loads(f.read())

    with open("./db/custom.json") as f:
        custom = json.loads(f.read())
        custom = custom['custom']

    neglect_hours = forcibly_off = normal = ''
    if custom == 'neglect_hours':
        neglect_hours = 'disabled'
    if custom == 'forcibly_off':
        forcibly_off = 'disabled'
    if custom == 'normal':
        normal = 'disabled'

    html_content = f"""
        <br>
        <h3>Current LED state: {'ON' if states["LED"] else 'OFF'}</h3>
        <br>
        <iframe name="states" style="display:none;"></iframe>
        <form action="/led" method="post" target="states">
            <input type="submit" name="ledstate" value=1>ON</button>
            <input type="submit" name="ledstate" value=0>OFF</button>
            <br>
            <input type="submit" name="custom" value="neglect_hours" {neglect_hours}>neglect_hours</button>
            <input type="submit" name="custom" value="forcibly_off" {forcibly_off}>forcibly_off</button>
            <input type="submit" name="custom" value="normal" {normal}>forcibly_off</button>
        </form>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.post("/interact")
def process(name: str = Body(...),
            LED: int = Body(...)):
    """
    Read data from arduino
    Send back required states
    """
    # data = json.loads(data)
    # name = data['name']
    # state = data['state']
    # Write existing states from arduino
    with open("./db/states.json", "w") as f:
        f.write(json.dumps({"name": name, "LED": LED}))

    # Get required states
    with open("./db/required.json") as f:
        states = json.loads(f.read())

    # Get user defined state
    with open("./db/custom.json") as f:
        custom = json.loads(f.read())
        custom = custom['custom']

    if custom == 'neglect_hours':
        if datetime.now().minute not in working_minutes:
            states['LED'] = 0
    else:
        if datetime.now().minute not in working_minutes or \
                datetime.now().hour not in working_hours or \
                custom == 'forcibly_off':
            states['LED'] = 0

    return JSONResponse(states)


@app.post("/led")
def led(ledstate: str = Form(...),
        custom: str = Form(...)):
    """
    Change state in DB
    """
    with open("./db/required.json", 'w') as f:
        f.write(json.dumps({"LED": int(ledstate)}))

    with open("./db/custom.json", 'w') as f:
        f.write(json.dumps({"custom": custom}))

    return read_root()


if __name__ == '__main__':
    uvicorn.run(app, port=8000, host="0.0.0.0")