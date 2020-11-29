from typing import Optional
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import os
# import json

from pre_build.class_f import TextBox, CheckBox

class Item(BaseModel):
    type: str
    id:str
    dict_data: Optional[list] = None
    file:str


app = FastAPI()

def get_data(item: Item):

    if item.type == "checkbox":
        box = CheckBox(item.id, item.file, item.dict_data)
        print(item.dict_data)
        data = box.get_data()
    else:
        box =  TextBox(item.id, item.file)
        data = box.get_data()

    return data
    ## With local host
    # data_path = "./source"
    # with open(os.path.join(data_path,item.id), 'w') as outfile:
    #     json.dump(data, outfile)

@app.post("/put_items/")
async def create_item(item: Item, background_tasks: BackgroundTasks):
    # background_tasks.add_task(get_data,item)
    item.file = os.path.join("data_drive",item.file)
    data = get_data(item)
    re ={}
    re['id'] = "item.id"
    re['data'] = data
    return re
