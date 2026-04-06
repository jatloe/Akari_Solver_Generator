from PIL import Image, ImageDraw
import uuid

cellSize = 50

def drawLine(imgd, x1, y1, x2, y2, width=2):
    x1 += 1
    y1 += 1
    x2 += 1
    y2 += 1
    imgd.line([(cellSize*x1, cellSize*y1), (cellSize*x2, cellSize*y2)], fill="black", width=width)

def drawRect(imgd, x1, y1, x2=None, y2=None, fill="black"):
    if x2 == None: x2 = x1+1
    if y2 == None: y2 = y1+1
    x1 += 1
    y1 += 1
    x2 += 1
    y2 += 1
    imgd.rectangle([(cellSize*x1, cellSize*y1), (cellSize*x2, cellSize*y2)], fill=fill)

def drawText(imgd, text, x1, y1, x2=None, y2=None, fill="white"):
    if x2 == None: x2 = x1+1
    if y2 == None: y2 = y1+1
    x1 += 1
    y1 += 1
    x2 += 1
    y2 += 1
    imgd.text((cellSize*(x1+x2)//2, cellSize*(y1+y2)//2), text, fill=fill, anchor="mm", font_size=cellSize//2)

def drawCircle(imgd, radius, x1, y1, x2=None, y2=None, fill="gray"):
    if x2 == None: x2 = x1+1
    if y2 == None: y2 = y1+1
    x1 += 1
    y1 += 1
    x2 += 1
    y2 += 1
    imgd.circle((cellSize*(x1+x2)//2, cellSize*(y1+y2)//2), radius, fill=fill)

def draw(s, width, depth=0, lpcells=tuple()):
    height = len(s)//width

    img = Image.new("RGB", ((width+2)*cellSize, (height+2)*cellSize))

    imgd = ImageDraw.Draw(img)
    
    white = (255,255,255)
    yellowStep = (0,0,-30)

    drawRect(imgd,-1,-1,width+1,height+1,tuple(u+depth*v for u,v in zip(white,yellowStep)))

    for x in range(width):
        for y in range(height):
            char = s[y*width+x]
            if char in "#01234":
                drawRect(imgd,x,y,fill="black")
            if char in "@-":
                drawRect(imgd,x,y,fill="lime")
            if y*width+x in lpcells:
                drawRect(imgd,x,y,fill="beige")
            if char in "01234":
                drawText(imgd,char,x,y)
            if char == "@":
                drawCircle(imgd,15,x,y)
            if char == " ":
                drawCircle(imgd,3,x,y,fill="green")

    drawLine(imgd,0,0,0,height)
    drawLine(imgd,0,0,width,0)
    drawLine(imgd,width,0,width,height)
    drawLine(imgd,0,height,width,height)

    for x in range(1,width): drawLine(imgd,x,0,x,height)
    for y in range(1,height): drawLine(imgd,0,y,width,y)

    return img

def draw_and_save(info, width):
    img = draw(info[0], width, info[1], info[2])
    route = f"static/solution_{uuid.uuid4().hex}.png"
    img.save(route)
    return route

def make_gif(images):
    images[0].save("proof.gif", save_all=True, append_images = images[1:]+images[-1:]*20, duration=50, loop=0)