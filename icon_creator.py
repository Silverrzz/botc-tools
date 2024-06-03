import flask
import requests
import cv2
import numpy as np
import base64
import json

def resize_image(image):
    tmp = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
    _, alpha = cv2.threshold(tmp, 10, 255, cv2.THRESH_BINARY)
    r,g, b, a = cv2.split(image)
    image = cv2.merge((r, g, b, alpha))
    x, y, w, h = cv2.boundingRect(alpha)
    image = image[y:y+h, x:x+w]
    if w > h:
        diff = w - h
        image = cv2.copyMakeBorder(image, diff//2, diff//2, 0, 0, cv2.BORDER_CONSTANT, value=(0,0,0,0))
    elif h > w:
        diff = h - w
        image = cv2.copyMakeBorder(image, 0, 0, diff//2, diff//2, cv2.BORDER_CONSTANT, value=(0,0,0,0))
    image = cv2.resize(image, (360, 360), interpolation=cv2.INTER_AREA)

    return image

def remove_background(image):
    tmp = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    _, alpha = cv2.threshold(tmp, 10, 255, cv2.THRESH_BINARY)

    r,g, b = cv2.split(image)
    image = cv2.merge((r, g, b, alpha))

    return image

def add_shadow_from(original, new):
    #the original image will contain a fully transparent background, and a fully opaque icon. All pixels that are not fully transparent are shadow and should be copied onto the new image in the exact pixel location

    #convert the original image to grayscale
    gray = cv2.cvtColor(original, cv2.COLOR_BGRA2GRAY)

    #find the shadow
    _, shadow = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)

    #invert the shadow
    shadow = cv2.bitwise_not(shadow)

    #copy the shadow onto the new image
    new[shadow == 255] = original[shadow == 255]

    return new

def image64(image):
    #conver cv2 image to base64 that could be displayed in html
    _, buffer = cv2.imencode(".png", image)
    return base64.b64encode(buffer).decode("utf-8")

def process_character(image_url, team):

    #load the image
    response = requests.get(image_url)

    #ensure images lack of background is kept
    image = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_UNCHANGED)

    #resize the image
    image = resize_image(image)

    if team in ["minion", "demon", "traveler"]:
        #for each pixel in the image
        #hue should go from ~0 to ~200
        #saturation should remain the same
        #value should remain the same

        #convert image to hsv
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        #change the hue
        hsv[:, :, 0] = (hsv[:, :, 0] + 100) % 256

        #convert back to bgr
        good_image = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    else:
        good_image = image.copy()
        good_image = cv2.cvtColor(good_image, cv2.COLOR_BGRA2BGR)

    if team in ["townsfolk", "outsider", "traveler"]:
        #for each pixel in the image
        #hue should change
        #saturation should increase
        #value should remain the same

        #convert image to hsv
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        #change the hue
        hsv[:, :, 0] = (hsv[:, :, 0] + 75) % 256

        #remove pink colours and make them red
        hsv[:, :, 0][hsv[:, :, 0] > 150] = 0

        #convert back to bgr
        evil_image = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    else:
        evil_image = image.copy()
        evil_image = cv2.cvtColor(evil_image, cv2.COLOR_BGRA2BGR)

    good_image = remove_background(good_image)
    evil_image = remove_background(evil_image)

    good_image = add_shadow_from(image, good_image)
    evil_image = add_shadow_from(image, evil_image)

    #save the images
    if team == "traveler":
        #evil_image should be left half of original image (grayscaled) and right half of evil image stitched together
        left_half_original = image[:, :image.shape[1] // 2]
        left_half_original = cv2.cvtColor(left_half_original, cv2.COLOR_BGR2GRAY)
        left_half_original = cv2.cvtColor(left_half_original, cv2.COLOR_GRAY2BGR)

        right_half_original = image[:, image.shape[1] // 2:]
        right_half_original = cv2.cvtColor(right_half_original, cv2.COLOR_BGRA2BGR)
        
        evil_image = np.concatenate((left_half_original, right_half_original), axis=1)
        evil_image = remove_background(evil_image)

        #good_image should be right half of original image (grayscaled) and left half of good image stitched together
        right_half_original = image[:, image.shape[1] // 2:]
        right_half_original = cv2.cvtColor(right_half_original, cv2.COLOR_BGR2GRAY)
        right_half_original = cv2.cvtColor(right_half_original, cv2.COLOR_GRAY2BGR)

        left_half_original = image[:, :image.shape[1] // 2]
        left_half_original = cv2.cvtColor(left_half_original, cv2.COLOR_BGRA2BGR)

        good_image = np.concatenate((left_half_original, right_half_original), axis=1)
        good_image = remove_background(good_image)

        return [image64(image), image64(good_image), image64(evil_image)]

    elif team == "fabled":
        return [image64(image)]

    else:
        return [image64(good_image), image64(evil_image)]
    

app = flask.Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello from Flask!'

@app.route("/process", methods=["POST"])
def process():
    data = flask.request.get_json()
    image_url = data["image_url"]
    team = data["team"]
    return json.dumps(process_character(image_url, team))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

