from argparse import _AppendAction
import os
import logging
import pathlib
import json
import sqlite3
import hashlib
import shutil
import sys
from fastapi import FastAPI, Form, UploadFile, HTTPException
from fastapi.params import File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from http.server import HTTPServer, SimpleHTTPRequestHandler, test

class CORSRequestHandler (SimpleHTTPRequestHandler):
    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        SimpleHTTPRequestHandler.end_headers(self)

if __name__ == '__main__':
    test(CORSRequestHandler, HTTPServer, port=int(sys.argv[1]) if len(sys.argv) > 1 else 8000)

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
images = pathlib.Path(__file__).parent.resolve() / "images"
origins = [ os.environ.get('FRONT_URL', 'http://localhost:3000')]
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
    category_id INTEGER,
    image_filename STRING,
    FOREIGN KEY(category_id) REFERENCES category(id)
)""")
c.execute("""CREATE TABLE IF NOT EXISTS category (
    id INTEGER PRIMARY KEY,
    name STRING
)""")
#Commit
conn.commit()
#Close
conn.close()

def hashImage(filename):
    try:    
        hashed_str = hashlib.sha256(str(filename).replace('.jpg', '').encode('utf-8')).hexdigest() + '.jpg'
        return hashed_str

    except sqlite3.Error as error:
        return error

def addItem(name, category, image_filename):
    try:
        conn = sqlite3.connect('mercari.sqlite3')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO category (name) VALUES (?)", (category,))
        c.execute("SELECT id FROM category WHERE name=(?)", (category,))
        category_id = c.fetchone()[0]
        c.execute("INSERT INTO items(name, category_id, image_filename) VALUES (?,?,?)", (name, category_id, image_filename))
        conn.commit()
        conn.close()
        print("Item added successfully.")
    except sqlite3.Error as error:
        return error

def getAllItems():
    try:
        conn = sqlite3.connect('mercari.sqlite3')
        c = conn.cursor()
        #c.execute("SELECT name, category, image_filename FROM items")
        c.execute("""SELECT items.name,
        category.name as category,
        items.image_filename
        FROM  items INNER JOIN category
        ON items.category_id =category.id
        """)
        itemLists = c.fetchall()
        result = []
        for itemList in itemLists:
            result.append({ "name": itemList[0], "category": itemList[1], "image_filename": itemList[2]})
        return result
        conn.commit()
        conn.close()
    except sqlite3.Error as error:
        return error

def getSpecificItems(**args):
    try:
        conn = sqlite3.connect('mercari.sqlite3')
        c = conn.cursor()
        select = ("""SELECT items.id,
        items.name,
        category.name as category,
        items.image_filename
        FROM items INNER JOIN category
        ON items.category_id =category.id
        """)
        conn.row_factory = sqlite3.Row
        if 'name' in args: c.execute(select + "WHERE items.name LIKE " + (args['name'].lower(),))
        if 'id' in args: c.execute(select + "WHERE items.id LIKE " + (args['id'],))
        itemLists = c.fetchall()
        result = []
        for itemList in itemLists:
            result.append({ "name": itemList[0], "category": itemList[1], "image_filename": itemList[2]})
        return result
        conn.commit()
        conn.close()
    except sqlite3.Error as error:
        return error

@app.get("/")
def root():
    return {"message": "Hello, world!"}

@app.post("/items")
def add_item(name: str = Form(...), category: str = Form(...), image_filename: UploadFile = File(...)):
    
    filename = image_filename.filename
    hashedFilename = hashImage(filename)
    save_path = images / hashedFilename
    with open(save_path, 'wb') as buffer:
        shutil.copyfileobj(image_filename.file, buffer)
    
    addItem(name, category, hashedFilename)
    inputDetail = {"name": name, "category": category, "image_filename": hashedFilename}
    logger.info(f"Receive item: {inputDetail}")
    return {"message": f"item received: {name}"}

@app.get("/items")
def getItems():
    return {'items': getAllItems()}

@app.get("/search")
def getKeyword(keyword: str):
    return {'items': getSpecificItems(name=keyword)}

@app.get("/items/{item_id}")
def getKeyword(item_id: int):
    return {'items': getSpecificItems(id=item_id)}

@app.get("/image/{image_filename}")
async def get_image(image_filename):
    
    # Create image path
    image = images / image_filename
    if not image_filename.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.info(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)