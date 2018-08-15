import cv2
import os
import json
from os.path import join
from random import choice


alphabet = ['A', 'B', 'C', 'E', 'H', 'K', 'M', 'O', 'P', 'T', 'X', 'Y']
digits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

path_templates = '/ssd480/grisha/plates_generation/templates'
path_jsons = "/ssd480/data/metadata/"
# path_to_cropped_imgs = '/home/grigorii/Desktop/style_transfer/test'
# path_to_save = '/home/grigorii/Desktop/style_transfer/save'
# path_templates = '/home/grigorii/Desktop/plates_generator/templates'

# TODO add some more comments
area_number_two_line = (39, 59, 131, 328) # whole area for 6 first elements on a plate
area_two_line_region_2 = (179, 24, 273, 177) # region area
area_two_line_region_3 = (179, 218, 273, 346) # region area

# digit's width and height
dx_d_two_line = 57
dy_d_two_line = area_number_two_line[2] - area_number_two_line[0]
dx_l_two_line = 73 - 5
dy_l_two_line = area_two_line_region_2[2] - area_two_line_region_2[0] - 5
dx_r_two_line = 62 - 2
dy_r_two_line = dy_l_two_line

imsize = 128


def get_two_line_plate_img(elements):
    template_name = 'template_two_line.jpg'
    temp = cv2.imread(join(path_templates, template_name), 0)

    n = 4
    dist = round((area_number_two_line[3] - area_number_two_line[1] - n * dx_d_two_line) / (n - 1))
    shift_dy = area_number_two_line[2] - dy_d_two_line
    shift_dx = area_number_two_line[1]
    cur_x_pos = shift_dx
    for i in range(n):
        img = cv2.imread(join(path_templates, elements[i] + '.png'), 0)
        img = cv2.resize(img, (dx_d_two_line, dy_d_two_line))
        temp[shift_dy:shift_dy + img.shape[0], cur_x_pos:cur_x_pos + img.shape[1]] = img
        cur_x_pos += img.shape[1] + dist

    n = 2
    dist = round((area_two_line_region_2[3] - area_two_line_region_2[1] - n * dx_l_two_line) / (n - 1))
    shift_dy = area_two_line_region_2[2] - dy_l_two_line
    shift_dx = area_two_line_region_2[1]
    cur_x_pos = shift_dx
    for i in range(n):
        img = cv2.imread(join(path_templates, elements[4 + i] + '.png'), 0)
        img = cv2.resize(img, (dx_l_two_line, dy_l_two_line))
        temp[shift_dy:shift_dy + img.shape[0], cur_x_pos:cur_x_pos + img.shape[1]] = img
        cur_x_pos += img.shape[1] + dist

    n = 2
    dist = round((area_two_line_region_3[3] - area_two_line_region_3[1] - n * dx_r_two_line) / (n - 1))
    shift_dy = area_two_line_region_3[2] - dy_r_two_line
    shift_dx = area_two_line_region_3[1]
    cur_x_pos = shift_dx
    for i in range(n):
        img = cv2.imread(join(path_templates, elements[6 + i] + '.png'), 0)
        img = cv2.resize(img, (dx_r_two_line, dy_r_two_line))
        temp[shift_dy:shift_dy + img.shape[0], cur_x_pos:cur_x_pos + img.shape[1]] = img
        cur_x_pos += img.shape[1] + dist

    return temp


def get_random_plate():
    num = []
    for j in range(4):
        num.append(choice(digits))
    for j in range(2):
        num.append(choice(alphabet))
    for j in range(2):
        num.append(choice(digits))
    img = get_two_line_plate_img(num)
    img = cv2.resize(img, (imsize, imsize))
    return img


def printing(s):
    print('-' * 30)
    print(s)
    print('-' * 30)


def all_images_file():
    all_images = {}
    shift = 5

    if not os.path.exists('all_images.json'):
        printing('Creating all_images file...')
        files = os.listdir(path_jsons)
        json_list = []
        for file in files:
            if file.endswith(".json"):
                json_list.append(file)

        data_all = []
        for json_file in json_list:
            with open(join(path_jsons, json_file)) as f:
                data = json.load(f)
                data_all.append(data)
                for i, item in enumerate(data['results']):

                    # add first image from two
                    img_name = item['firstOct']['photoProof']['link'].split('/')[-1]
                    left = item['firstOct']['photoProof']['bounds']['leftBorder']
                    top = item['firstOct']['photoProof']['bounds']['topBorder']
                    right = item['firstOct']['photoProof']['bounds']['rightBorder']
                    bottom = item['firstOct']['photoProof']['bounds']['bottomBorder']
                    number = item['firstOct']['correctedCarNumber']
                    middle_part = number['middleCarNumber']
                    region_part = number['regionCarNumber'].split(' ')[0]
                    all_images[img_name] = {'coords':(left, top - shift, right, bottom + shift),
                                           'car_number':list(middle_part + region_part)}

                    # add first image from two
                    img_name = item['secondOct']['photoProof']['link'].split('/')[-1]
                    left = item['secondOct']['photoProof']['bounds']['leftBorder']
                    top = item['secondOct']['photoProof']['bounds']['topBorder']
                    right = item['secondOct']['photoProof']['bounds']['rightBorder']
                    bottom = item['secondOct']['photoProof']['bounds']['bottomBorder']
                    number = item['secondOct']['correctedCarNumber']
                    middle_part = number['middleCarNumber']
                    region_part = number['regionCarNumber'].split(' ')[0]
                    all_images[img_name] = {'coords':(left, top - shift, right, bottom + shift),
                                           'car_number':list(middle_part + region_part)}

        with open('all_images.json', 'w') as fp:
            json.dump(all_images, fp)

    else:
        printing('`all_images` file already exists')
        with open('all_images.json', 'r') as fp:
            all_images = json.load(fp)

    return all_images
