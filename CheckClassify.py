import cv2
import sys
import re
import os
import json
import imutils
import numpy as np
import subprocess
from imutils import contours
from imutils.perspective import four_point_transform


 
strTime = ["เช้า","กลางวัน","เย็น","ก่อนนอน","ก่อนอาหาร","หลังอาหาร","หลังอาหารเช้าทันที","หลังอาหารเช้า"]

datalists = []

pattern = re.compile(r"[^\u0E00-\u0E7Fa-zA-Z' ]|^'|'$|''")

def iterative_levenshtein(s, t, costs=(1, 1, 1)):
    """ 
        iterative_levenshtein(s, t) -> ldist
        ldist is the Levenshtein distance between the strings 
        s and t.
        For all i and j, dist[i,j] will contain the Levenshtein 
        distance between the first i characters of s and the 
        first j characters of t
        
        costs: a tuple or a list with three integers (d, i, s)
               where d defines the costs for a deletion
                     i defines the costs for an insertion and
                     s defines the costs for a substitution
    """
    rows = len(s)+1
    cols = len(t)+1
    deletes, inserts, substitutes = costs
    
    dist = [[0 for x in range(cols)] for x in range(rows)]
    # source prefixes can be transformed into empty strings 
    # by deletions:
    for row in range(1, rows):
        dist[row][0] = row * deletes
    # target prefixes can be created from an empty source string
    # by inserting the characters
    for col in range(1, cols):
        dist[0][col] = col * inserts
        
    for col in range(1, cols):
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0
            else:
                cost = substitutes
            dist[row][col] = min(dist[row-1][col] + deletes,
                                 dist[row][col-1] + inserts,
                                 dist[row-1][col-1] + cost) # substitution
    # for r in range(rows):
    #     print(dist[r])
    
    return dist[row][col]


def tsplit(string, delimiters):
    """Behaves str.split but supports multiple delimiters."""
    
    delimiters = tuple(delimiters)
    stack = [string,]
    
    for delimiter in delimiters:
        for i, substring in enumerate(stack):
            substack = substring.split(delimiter)
            stack.pop(i)
            for j, _substring in enumerate(substack):
                stack.insert(i+j, _substring)
            
    return stack

def text_from_image_file(image_name,lang):
    output_name = "OutputImg"
    return_code = subprocess.call(['tesseract',image_name,output_name,'-l',lang,'+eng','-c','preserve_interword_spaces=1 --tessdata-dir ./tessdata_best/'],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d = open(output_name+'.txt','r',encoding='utf-8')
    str_read = d.read()
    # char_to_remove = temp.split()
    # char_to_remove = re.findall(pattern, temp)
    
    temp = tsplit(str_read,(',', '/', '-', '=',' '))
    ouput = []
    for idx in temp :
        char_to_remove = re.findall(pattern, idx)

        list_with_char_removed = [char for char in idx if not char in char_to_remove]

        
        if len(''.join(list_with_char_removed)) != 0 :
           ouput = ouput + [''.join(list_with_char_removed)]
    return ouput

def cvt_to_JSON(_isPeriod, _isEatBefore,_isEatBreakfast, _isEatLunch, _isEatDinner, _isEatBedTime, _isRoutine, _periodHour) :
    output = {}
    output["isPeriod"] = _isPeriod
    data = {}
    data["isEatingBefore"] = _isEatBefore
    data["isEatBreakfast"] = _isEatBreakfast
    data["isEatLunch"] = _isEatLunch
    data["isEatDinner"] = _isEatDinner
    data["isEatBedTime"] = _isEatBedTime
    output["data"] = data
    conv_json = json.dumps(output, ensure_ascii = False)
    print(conv_json)

def main(argv) :
    strTime = ["เช้า","กลางวัน","เย็น","ก่อนนอน","ก่อนอาหาร","หลังอาหาร","หลังอาหารเช้าทันที","หลังอาหารเช้า"]

    image = cv2.imread(argv[0] , 0) 
    image = imutils.resize(image, height=700)
    Rim = image.copy()
    image = cv2.medianBlur(image,9)
    image = cv2.adaptiveThreshold(image,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,5,2)
    blurred = cv2.GaussianBlur(image, (7 , 7), 0)
    edged = cv2.Canny(blurred, 50, 200, 255)
    kernel = np.ones((3,15),np.uint8)
    im = cv2.dilate(edged,kernel,iterations = 1)
    kernel = np.ones((1,30),np.uint8)
    im = cv2.erode(im,kernel,iterations = 1)

    contourmask,contours,hierarchy = cv2.findContours(im,cv2.RETR_TREE,cv2.CHAIN_APPROX_NONE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    fname = argv[0].split(".")[0]
    datalists = []

    hog = cv2.HOGDescriptor((80, 80),(80, 80),(80, 80),(80, 80),40)
    features_train = np.load("features_train.npy")
    label_train = np.load("label_train.npy")
    knn = cv2.ml.KNearest_create()
    knn.train(features_train,cv2.ml.ROW_SAMPLE,label_train)

    isEatingBefore = False
    _isEatBreakfast = False
    _isEatLunch = False
    _isEatDinner = False
    _isEatBedTime =False 

    for cnt in contours[1:] :
        x, y, w, h = cv2.boundingRect(cnt)
        if(w * h > 1000 and w * h < 8000) :
            # cv2.rectangle(Rim , (x-10,y-18) , (x+w+13,y+h+4) , (0,0,255) , 2)
            if(y>=18 and x>=10) :
                roi = Rim[y-18:y+h+4, x-10:x+w+13]
                cv2.imwrite( str(w*h) + ".png" , roi)
                txts = text_from_image_file( str(w*h) + ".png" ,'tha')

                im = roi[0:im.shape[1],0:im.shape[1]]
                im = cv2.resize(im, (80, 80))
                ho = hog.compute(im)
                data_train = ho.reshape(1,-1)
                _,result,_,_ = knn.findNearest(data_train,3)
                # print(txts)
                for txt in txts :
                    if iterative_levenshtein(strTime[0],txt) <= 2:
                        # print(result)
                        if result == 0 :
                            _isEatBreakfast = True
                    if iterative_levenshtein(strTime[1],txt) <= 2:
                        # print(result)
                        if result == 0 :
                            _isEatLunch = True
                        
                    if iterative_levenshtein(strTime[2],txt) <= 2:
                        # print(result)
                        if result == 0 :
                            _isEatDinner = True
                        
                    if iterative_levenshtein(strTime[3],txt) <= 2:
                        # print(result)
                        if result == 0 :
                            _isEatBedTime = True
                        
                    if iterative_levenshtein(strTime[4],txt) <= 2:
                        # print(result)
                        if result == 0 :
                            isEatingBefore = True
                        
                    if iterative_levenshtein(strTime[5],txt) <= 2:
                        # print(result)
                        if result == 0 :
                            isEatingBefore = False
                        
                    if iterative_levenshtein(strTime[6],txt) <= 2:
                        # print(result)
                        if result == 0 :
                            isEatingBefore = False
                            _isEatBreakfast = True
                        
                    if iterative_levenshtein(strTime[7],txt) <= 2:
                        # print(result)
                        if result == 0 :
                            isEatingBefore = False
                            _isEatBreakfast = True
                os.remove( ".//"+str(w*h) + ".png")
    cvt_to_JSON(False, isEatingBefore,_isEatBreakfast, _isEatLunch, _isEatDinner, _isEatBedTime, False, "_periodHour")
    #os.remove(argv[0])

main(sys.argv[1:])
