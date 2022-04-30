from typing import Optional, List, Any, Dict
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import ORJSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import orjson
import traceback
import sys
from time import time
from starlette.background import BackgroundTasks


if "src.information" in sys.modules: # for development
    import src.information as information
    import src.optimization as optimization
    from src.models import *
    from src.config import CONFIG
    from src.utils import format_lanit, deformat_lanit
    from src.main import publish
else:
    import information
    import optimization
    from models import *
    from utils import format_lanit, deformat_lanit
    from config import CONFIG
    from main import publish


app = FastAPI(default_response_class=ORJSONResponse)
# app.mount("/static", StaticFiles(directory=CONFIG.root_dir+"/static"), name="static")


@app.get("/")
def read_root():
    html_content = """

           """
    return HTMLResponse(content=html_content, status_code=200)


def clear_static():
    static_path = CONFIG.root_dir+"/static"
    timenow = time()
    max_time_allowed = CONFIG.cache_lifetime_sec
    for file in os.listdir(static_path):
        full_path =  os.path.join(static_path, file)
        if timenow - os.path.getmtime(full_path) > max_time_allowed:
            os.remove(full_path)


def remove_file(filename: str) -> None:
    os.remove(filename)


@app.get("/calc_grp/{filename}")
def get_file(filename: str, background_tasks: BackgroundTasks):
    filepath = os.path.join(CONFIG.root_dir, "static", filename)
    background_tasks.add_task(remove_file, filepath)
    background_tasks.add_task(clear_static)
    if 'bz2' in filename:
        return FileResponse(filepath, media_type='application/x-bzip2')
    return FileResponse(filepath)


@app.post("/process")
def route_message(message: str = Body(..., embed=True)):
    message_id = 'Unknown'
    request_type = 'Unstated'
    try:
        # Retrieve payload attributes
        payload_in = orjson.loads(message)
        message_id = payload_in['id']
        request_type = payload_in['type']
        kwargs = payload_in['data']
        # Handle various request types
        # ===============================================================
        if request_type == 'analogs':
            # Well params
            well_params = deformat_lanit(kwargs['Параметры'])

            # Strict params
            strict_params = deformat_lanit(kwargs['Входные параметры'])

            # Facies
            facies = deformat_lanit(kwargs['Фации'])
            facies_list = []
            for face, val in facies.items():
                if val:
                    facies_list.append(face)
            if len(facies_list) > 0:
                strict_params['Категория фаций'] = facies_list

            # Refrac?
            refrac = deformat_lanit(kwargs['Состояние'])
            if refrac['Рефрак'] and not refrac['Новая']:
                strict_params['Идентификатор повторного ГРП'] = 1
            elif refrac['Новая'] and not refrac['Рефрак']:
                strict_params['Идентификатор повторного ГРП'] = 0

            # Calculation method
            calc_method = deformat_lanit(kwargs['Метод расчета'])
            if calc_method['Евклидово расстояние']:
                calc_method = 'Euclid'
            else:
                calc_method = 'Cosine'

            # Radius
            use_coords = False
            coordinates = None
            radius = 99_999_999
            coords = deformat_lanit(kwargs['Поиск в радиусе'], add_if_empty=True)
            if coords['X'] != '':
                use_coords = True
                coordinates = {'X': coords['X'], 'Y': coords['Y']}
                radius = float(coords['R'])

            ans = analogues_boundaries( well_params=well_params,
                                        strict_params=strict_params,
                                        use_coords=use_coords,
                                        radius=radius,
                                        calc_method=calc_method,
                                        coordinates=coordinates )
        # ===============================================================
        elif request_type == 'all_wells':
            field = kwargs['Месторождение']['value']
            ans = format_lanit(get_wells(field))
        # ===============================================================
        elif request_type == 'calc_grp':
            # в options: "ID модели" "Плотность проппанта" "Масса пропанта" "Шаг сетки оптимизации"
            options = deformat_lanit(kwargs['Опции оптимизации'])
            model_name = options['ID модели']
            prop_dens = options['Плотность проппанта']
            step = options['Шаг сетки оптимизации']
            prop_mass = -1
            if "Масса пропанта" in options:
                prop_mass = options['Масса пропанта']

            # boundaries[param]: [min, max]
            boundaries = deformat_lanit(kwargs['Границы параметров'])

            well_params = deformat_lanit(kwargs['Целевая скважина'], add_if_empty=True)

            df, optimum = optimize_grid(model_name, well_params, step, boundaries, prop_mass, prop_dens)

            df.to_csv(os.path.join(CONFIG.root_dir, 'static', f'id_{message_id}.csv.bz2'),
                      compression='bz2',
                      index=False)

            result_filepath = f'calc_grp/id_{message_id}.csv.bz2'
            ans = {'result_grid': result_filepath,
                   'optimum': format_lanit(optimum)[0]}
        # ===============================================================
        else:
            ans = {'error': f"Wrong request type ({request_type})"}

        # Gather payload
        payload_out = {'id': message_id,
                       'type': request_type,
                       'data': ans}
        publish(orjson.dumps(payload_out).decode('utf-8'))
    except Exception as e:
        payload_out = {'id': message_id,
                       'error': str(e),
                       'traceback': traceback.format_exc()}
        publish(orjson.dumps(payload_out).decode('utf-8'))


def analogues_boundaries(well_params: Dict,
                         strict_params: Optional[Dict[str, Any]] = None,
                         use_coords: bool = False,
                         coordinates = None,
                         radius: float = 9999999,
                         calc_method: str = 'Euclid',
                         ignore_nan: bool = True,
                         top_N: int = 10,
                         weighted: bool = True):
    """
    Возвращает список со словарём параметров скважин-аналогов в порядке убывания схожести (0-100), где 100 - одинаковые скважины,
    0 - максимально непохожие. Могут быть отрицательные значения.\n
    <b>well_params</b> - словарь {параметр: значение} для поиска аналогов.
    Все параметры должны присутствовать в базе данных %db_name%. Все параметры должны быть числовыми.\n
    <b>strict_params</b> - словарь {параметр: значение}. Все выдаваемые аналоги будут удовлетворять
    каждому значению в обозначенных параметрах. Все параметры должны присутствовать в базе данных %db_name%.
    Значение может быть списком - в таком случае будет удовлетворяться хотя бы одно условие из списка.\n
    <b>ignore_nan</b> - если False - скважины с NaN в параметрах, указанных в %well_params%, отфильтровываются.\n
    <b>top_N</b> - количество скважин-аналогов для отображения. Максимум - 30.\n
    <b>weighted</b> - использование весов (STD) для расчёта Евклидового расстояния.
    """
    return information.analogues_(well_params=well_params,
                                  strict_params=strict_params,
                                  use_coords=use_coords,
                                  coordinates=coordinates,
                                  radius=radius,
                                  calc_method=calc_method)


def get_wells(db_name: str):
    """
    Возвращает список скважин из базы данных, удовлетворяющим условиям из %strict_params%.\n
    <b>strict_params</b> - словарь {параметр: значение}. Все скважины в периметре поиска будут удовлетворять
    каждому значению в обозначенных параметрах. Все параметры должны присутствовать в базе данных %db_name%.
    Значение может быть списком - в таком случае будет удовлетворяться хотя бы одно условие из списка.\n
    """
    return information.all_db_wells(db_name)


def optimize_grid(model_name: str,
                  well_params: Dict[str, Any],
                  step: int,
                  limits: Dict[str, List[float]],
                  prop_mass: float = -1,
                  prop_dens: float = 2.77,
                  impute_with_analogues: bool = False) -> pd.DataFrame:
    """
    Возвращает оптимальный дизайн для конкретной скважины {параметр_дизайна: оптимальное значение}).\n
    <b>well_params</b>: параметры оптимизируемой скважины;\n
    <b>step</b>: шаг для сеточной оптимизации;\n
    <b>limits</b>: границы для параметров оптимизации {параметр: [lower_limit, upper_limit]};\n
    <b>impute_with_analogues</b>: нужно ли импутировать пропущенные значения для пилотной скважины. Если false - оставляет NaN.\n
    """
    return optimization.optimize_grid_(model_name, well_params, step, limits, prop_mass, prop_dens, impute_with_analogues)

if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="0.0.0.0")