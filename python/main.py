from argparse import _AppendAction
import os
import logging
import pathlib
import json
import sqlite3
import hashlib
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
images = pathlib.Path(__file__).parent.resolve() / "image"
origins = [ os.environ.get('FRONT_URL', 'http://localhost:3000') ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET","POST","PUT","DELETE"],
    allow_headers=["*"],
)

#Connect to db
conn = sqlite3.connect('mercari.sqlite3')
#Create cursor
c = conn.cursor()
#Create a table
c.execute("""CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    name STRING,
    category STRING,
    image STRING
)""")
#Commit
conn.commit()
#Close
conn.close()

def hashImage(filepath):
    with open(filepath,"rb") as f:
        bytes = f.read() # read entire file as bytes
        imageHash = hashlib.sha256(bytes).hexdigest()
        return (f'{imageHash}.jpg')

def addItem(name, category, image):
    conn = sqlite3.connect('mercari.sqlite3')
    c = conn.cursor()
    c.execute("INSERT INTO items(name, category, image) VALUES (?,?,?)", (name, category, hashImage(image)))
    conn.commit()
    conn.close()
    print("Item added successfully.")

def getAllItems():
    conn = sqlite3.connect('mercari.sqlite3')
    c = conn.cursor()
    c.execute("SELECT name, category, image FROM items")
    itemLists = c.fetchall()
    result = []
    for itemList in itemLists:
        result.append({ "name": itemList[0], "category": itemList[1], "image": itemList[2]})
    return result
    conn.commit()
    conn.close()

def getSpecificItems(**args):
    conn = sqlite3.connect('mercari.sqlite3')
    c = conn.cursor()
    if 'name' in args: c.execute("SELECT name, category, image FROM items WHERE name = ?", (args['name'].lower(),))
    if 'id' in args: c.execute("SELECT name, category, image FROM items WHERE id = ?", (args['id'],))
    itemLists = c.fetchall()
    result = []
    for itemList in itemLists:
        result.append({ "name": itemList[0], "category": itemList[1], "image": itemList[2]})
    return result
    conn.commit()
    conn.close()

@app.get("/")
def root():
    return {"message": "Hello, world!"}

#data = []
#data1 = {"items": data}
#@app.post("/items")
#def add_item(name: str = Form(...), category: str = Form(...)):
#    data.append({"name": name, "category": category})
#    with open('items.json', 'w') as json_file:
#        json.dump(data1, json_file)
#    logger.info(f"Receive item: {name}")
#    return {"message": f"item received: {name}"}

@app.post("/items")
def add_item(name: str = Form(...), category: str = Form(...), image: str = Form(...)):
    addItem(name, category, image)
    inputDetail = {"name": name, "category": category, "image": image}
    logger.info(f"Receive item: {inputDetail}")
    return {"message": f"item received: {name}"}

#@app.get("/items")
#def getItems():
#    data = open('items.json')
#    return json.load(data)

@app.get("/items")
def getItems():
    return {'items': getAllItems()}

@app.get("/search")
def getKeyword(keyword: str):
    return {'items': getSpecificItems(name=keyword)}

@app.get("/items/{item_id}")
def getKeyword(item_id: int):
    return {'items': getSpecificItems(id=item_id)}

@app.get("/image/{items_image}")
async def get_image(items_image):
    # Create image path
    image = images / items_image

    if not items_image.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)
