import json
from typing import List, Dict, Tuple
from fastapi import FastAPI, Body, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse, FileResponse
import uvicorn
from datetime import datetime
import aioredis
from config import CONFIG


app = FastAPI()
redis = aioredis.from_url(f'{CONFIG.redis_url}:{CONFIG.redis_port}', decode_responses=True)


async def get_states():
    """
    Get initial data from DB with sensors' settings: board_name, sensor_name, pins, units, schedules
    Then get states from frontend
    Store data in redis with
    hmset_dict(
        board_name,
        {
            sensor_name: {
                pin: 0,
                state: 1
                }
            }
        }
    )
    """
    redis.set('led_temp', 0.0)
    redis.set('coco_led', 0)
#%%

def create_schedule(work_hours: List[int],
                    work_time: int,
                    sleep_time: int,
                    start_minute: int = 0) -> Dict[int, List[Tuple[float, float]]]:
    """
    Create schedule in format of
        {
            hour1: [(start_minute, finish_minute), (start2, finish2), ...]
            hour2: [...]
        }
    The start minute of the schedule is being reset after the last working hour or after a break in work_hours list
    """
    work_hours = sorted(work_hours)
    schedule = {}
    for i, hour in enumerate(work_hours):
        schedule[hour] = [(i, i + work_time - 1) for i in range(start_minute, 60, sleep_time + work_time)]
        # Reset if the break >= 1 hour
        if i != 0:
            if hour - work_hours[i-1] > 1:
                start_minute = 0
        # Correct last interval if it ends after 59 min
        last_fin_minute = schedule[hour][-1][1]
        last_start_minute = schedule[hour][-1][0]
        if last_fin_minute >= 60:
            schedule[hour][-1] = (last_start_minute, 59)
        # Calculate starting minute of the next hour
        start_minute = last_start_minute + sleep_time + work_time - 60
    return schedule


work_time = 5
sleep_time = 5
schedule = create_schedule(work_hours=[i for i in range(8, 24)] + [0],
                           work_time=work_time,
                           sleep_time=sleep_time)
schedule_all_day = create_schedule(work_hours=[i for i in range(24)],
                                   work_time=work_time,
                                   sleep_time=sleep_time)
test_schedule = create_schedule(work_hours=[i for i in range(3, 8)],
                                work_time=30,
                                sleep_time=2)
#%%

@app.get("/")
async def read_root():
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

    led_temp = await redis.get('led_temp')
    html_content = f"""
        <script>
        submitForms = function(){{
            var formData = JSON.stringify($("#form1").serializeArray());
            $.ajax({{
              type: "POST",
              url: "/led",
              data: formData,
              success: function(){{}},
              dataType: "json",
              contentType : "application/json"
            }});
        }}
        </script>
        <br>
        <h3>Current LED state: {'ON' if states["LED"] else 'OFF'}</h3>
        <br>
        <iframe name="states" style="display:none;"></iframe>
        <form name="form1" action="/process" method="post" target="states">
            <input type="submit" name="ledstate" value=1 />ON
            <input type="submit" name="ledstate" value=0 />OFF
            <br>
            <input type="submit" name="custom" value="neglect_hours" {neglect_hours}" />
            <input type="submit" name="custom" value="forcibly_off" {forcibly_off}" />
            <input type="submit" name="custom" value="normal" {normal}" />
        </form>

        <h1> {led_temp} </h1>
        <iframe name="coco" style="display:none;"></iframe>
        <form name="form2" action="/process" method="post" target="coco">
            <input type="submit" name="coco_led" value=1 />ON
            <input type="submit" name="coco_led" value=0 />OFF
        </form>
        
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.post("/interact")
async def process(request: Request):
        # name: str = Body(...),
        #           LED: int = Body(...)):
    """
    Read data from arduino
    Send back required states
    """
    data = await request.json()
    name = data['name']

    # Write existing states from arduino
    if name == 'farm':
        LED = data['LED']
        with open("./db/states.json", "w") as f:
            f.write(json.dumps({"name": name, "LED": LED}))

        # Get required states
        with open("./db/required.json") as f:
            states = json.loads(f.read())

        # Get user defined state
        with open("./db/custom.json") as f:
            custom = json.loads(f.read())
            custom = custom['custom']

        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        if custom != 'forcibly_off':
            if custom == 'neglect_hours':
                hourly_schedule = schedule_all_day[current_hour]
            elif custom == 'normal':
                hourly_schedule = schedule[current_hour]
            else:
                raise AttributeError('Unknown custom parameter')
            if any(interval[0] <= current_minute <= interval[1] for interval in hourly_schedule):
                states['LED'] = 1
            else:
                states['LED'] = 0
        else:
            states['LED'] = 0
        return JSONResponse(states)
    elif name == 'coco':
        await redis.set('led_temp', data['led_temp'])
        coco_led_state = await redis.get('coco_led')
        return JSONResponse({"coco_led": int(coco_led_state)})


@app.post("/process")
async def led(payload: str = Body(...)):
    """
    Change state in DB
    """
    payload = payload.split("=")
    if payload[0] == 'ledstate':
        with open("./db/required.json", 'w') as f:
            f.write(json.dumps({"LED": int(payload[1])}))
    elif payload[0] == 'custom':
        with open("./db/custom.json", 'w') as f:
            f.write(json.dumps({"custom": payload[1]}))
    elif payload[0] == 'coco_led':
        await redis.set('coco_led', int(payload[1]))
    return read_root()


# app.mount("", StaticFiles(directory="sveltekit/public/", html=True), name="static")
# app.mount("/svelte", StaticFiles(directory="sveltekit/build"), name="build")

# @app.get('/')
# async def front():
#     return FileResponse('sveltekit/build/index.html')


if __name__ == '__main__':
    uvicorn.run(app, port=8000, host="0.0.0.0")
